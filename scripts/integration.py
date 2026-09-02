"""Joue un playbook réel contre `feint`, un émulateur local des clouds européens.

C'est la seule preuve qui compte pour un changement de comportement : le module
tel qu'il a été généré, le vrai SDK, un vrai serveur HTTP. Ni compte Scaleway,
ni dépense, ni ressource créée nulle part.

`SCW_API_URL` est ce qui rend cette preuve possible, et c'est pour ça que la
règle 7 du projet le protège de bout en bout.

**L'émulateur est un backend de test, pas une dépendance.** Rien dans
`plugins/` ne le connaît, et `mise run check` tourne sans lui. Cette cible est
séparée, et elle **échoue** quand feint est absent plutôt que de se sauter en
silence : un test qui se saute tout seul finit par ne plus jamais tourner.

Trois choses viennent de l'émulateur plutôt que d'être écrites ici :

* **les identifiants**, lus par `feint env scaleway`. Les inventer dans ce
  dépôt créerait une seconde source de ce que l'émulateur accepte ;
* **le cycle de vie**, par les verbes `wait`, `start` et `stop`. `feint wait`
  est le verbe de CI, et il distingue « en écoute » de « rien ici » par son
  code de retour, là où `feint status` sort en 0 dans les deux cas ;
* **l'adoption** : quand un émulateur répond déjà, ce script s'en sert et ne
  l'arrête pas. C'est ce qui permet à la CI de le démarrer par
  `stephrobert/setup-feint`, sans que le script se marche dessus.

    python scripts/integration.py
    FEINT=/chemin/vers/feint python scripts/integration.py
    FEINT_VM=incus-ovn python scripts/integration.py

`FEINT_VM` choisit ce qui porte un serveur allumé : `off` par défaut, où
l'état est pure comptabilité, ou `incus`, `incus-vm`, `incus-ovn`, où une
machine démarre réellement. Le scénario est le même dans les deux cas, et c'est
le but : ce qui change est la difficulté du sujet, pas la mesure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from generator.ansible.collection import Collection, load_collection

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "tests" / "integration" / "feint" / "playbook.yml"
INVENTORY = ROOT / "tests" / "integration" / "feint" / "inventaire.scaleway.yml"
INVENTORY_PLAYBOOK = ROOT / "tests" / "integration" / "feint" / "playbook_inventaire.yml"

#: Surchargeable pour ne pas marcher sur un émulateur qui tourne déjà pour
#: quelqu'un d'autre, ce qui arrive sur une machine de développement.
ADDRESS = os.environ.get("FEINT_ADDR", "127.0.0.1:4599")
ENDPOINT = f"http://{ADDRESS}"
ZONE = "fr-par-1"

#: Le pack de l'émulateur dont on veut l'environnement client.
PROVIDER = "scaleway"

#: Au-delà d'une page de 100 : c'est ce qui distingue « la liste est complète »
#: de « la première page ressemblait à une liste complète ».
SEEDED_SERVERS = 104

#: Ce qui porte un serveur allumé. `off` par défaut : démarrer des machines est
#: un effet de bord que ce projet demande explicitement, jamais par défaut.
VM_MODE = os.environ.get("FEINT_VM", "off")

#: Combien de temps un serveur allumé a pour atteindre `running`. En `off`,
#: c'est immédiat ; sous `incus-ovn`, une machine démarre pour de bon.
BOOT_TIMEOUT_SECONDS = 120


class IntegrationError(RuntimeError):
    """Le scénario ne peut pas être joué, et il faut le dire au lieu de sauter."""


def feint_binary() -> str:
    """Chemin de l'émulateur, ou une erreur qui dit quoi installer."""
    candidate = os.environ.get("FEINT") or shutil.which("feint")
    if not candidate:
        raise IntegrationError(
            "feint est introuvable. C'est une cible d'intégration, pas un test unitaire : "
            "elle échoue plutôt que de se sauter. Installer feint "
            "(https://github.com/stephrobert/feint), ou passer FEINT=/chemin/vers/feint."
        )
    return candidate


def run(
    command: list[str],
    *,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        check=False,
        capture_output=capture,
        env=env,
    )


def playbooks(collection: Collection) -> list[Path]:
    """Le playbook de contrat, puis les playbooks livrés avec la collection.

    Ils sont joués, et pas seulement écrits : un exemple que personne n'exécute
    pourrit, et un exemple faux dans une documentation coûte plus cher qu'une
    documentation absente.
    """
    livres = sorted(collection.playbooks_dir.glob("*.yml"))
    if not livres:
        raise IntegrationError(
            f"aucun playbook dans {os.path.relpath(collection.playbooks_dir, ROOT)} : "
            "ce scénario en joue au moins un, sinon rien ne les tient à jour"
        )
    return [PLAYBOOK, *livres]


def start_command(binary: str, state: Path) -> list[str]:
    """La commande qui démarre l'émulateur, isolée pour être vérifiable.

    `--cleanup` en fait partie, et ce n'est pas du confort : sans lui, une
    exécution sous `incus-ovn` laisse derrière elle le conteneur qu'elle a
    démarré. Mesuré une fois, tenu par un test depuis.
    """
    return [
        binary,
        "start",
        "--addr",
        ADDRESS,
        "--state",
        str(state),
        "--vm",
        VM_MODE,
        "--cleanup",
        "--timeout",
        "120s",
    ]


def answers(binary: str, *, timeout: str = "2s") -> bool:
    """Vrai quand un émulateur répond déjà à cette adresse.

    `feint wait` est le verbe prévu pour ça : 0 quand l'émulateur répond, 1
    quand rien ne répond. `feint status` ne convient pas, il sort en 0 dans les
    deux cas, mesuré après avoir failli l'utiliser : le scénario n'aurait
    jamais démarré d'émulateur en local.
    """
    probe = run([binary, "wait", "--addr", ADDRESS, "--timeout", timeout], capture=True)
    return probe.returncode == 0


def machine_mode(binary: str) -> str:
    """Ce qui porte les machines de l'émulateur en écoute, dit par lui.

    `feint status --format json` porte le champ `machines`, et il vaut `none`
    quand l'émulateur tourne sans backend de machines.
    """
    result = run([binary, "status", "--addr", ADDRESS, "--format", "json"], capture=True)
    if result.returncode != 0:
        raise IntegrationError(f"`feint status` a échoué :\n{result.stderr}")
    try:
        payload = json.loads(result.stdout or "{}")
    except ValueError as erreur:
        raise IntegrationError(f"`feint status` n'a pas rendu du JSON : {erreur}") from erreur
    return str(payload.get("machines", ""))


def check_adopted_mode(binary: str) -> None:
    """Refuse d'adopter un émulateur qui ne porte pas le mode demandé.

    Sans cette garde, `mise run integration FEINT_VM=incus-ovn` lancé pendant qu'un
    émulateur en `off` écoute déjà passe au vert **sans avoir démarré une seule
    machine**. C'est arrivé : la sortie était identique à celle d'un run qui
    aurait fait le travail, à une durée de démarrage près que personne ne lit.
    """
    attendu = "none" if VM_MODE == "off" else VM_MODE
    trouve = machine_mode(binary)
    if trouve != attendu:
        raise IntegrationError(
            f"l'émulateur en écoute sur {ADDRESS} porte les machines en '{trouve}', "
            f"et ce scénario demande '{attendu}'. Il n'est pas adopté : le run "
            f"mesurerait autre chose que ce qui est demandé.\n"
            f"Arrêter cet émulateur, ou choisir une autre adresse avec FEINT_ADDR."
        )


def parse_exports(output: str) -> dict[str, str]:
    """Lit les lignes `export NOM='valeur'` produites par `feint env`."""
    environment: dict[str, str] = {}
    for line in output.splitlines():
        if not line.startswith("export "):
            continue
        name, _, value = line.removeprefix("export ").partition("=")
        environment[name.strip()] = value.strip().strip("'\"")
    return environment


def client_environment(binary: str) -> dict[str, str]:
    """L'environnement qu'un client Scaleway doit recevoir, dit par l'émulateur.

    `feint env` écrit les exports sur la sortie standard et ses remarques sur la
    sortie d'erreur, ce qui rend cette lecture sûre.

    La garde qui suit n'est pas décorative : un environnement mal lu laisserait
    le playbook partir avec ce qui traîne dans le shell, c'est-à-dire
    éventuellement vers l'API Scaleway réelle, avec de vrais identifiants et de
    vraies ressources.
    """
    result = run([binary, "env", PROVIDER, "--endpoint", ENDPOINT], capture=True)
    if result.returncode != 0:
        raise IntegrationError(f"`feint env {PROVIDER}` a échoué :\n{result.stderr}")

    environment = parse_exports(result.stdout)
    if environment.get("SCW_API_URL") != ENDPOINT:
        raise IntegrationError(
            f"`feint env {PROVIDER}` n'a pas donné SCW_API_URL={ENDPOINT}. "
            "Le scénario s'arrête : sans cette variable, le playbook parlerait "
            "à l'API Scaleway réelle."
        )
    return environment


def call(path: str, body: dict[str, object] | None = None) -> dict[str, object]:
    """Appel HTTP direct à l'émulateur, sans passer par la collection.

    L'amorçage n'utilise pas les modules : un scénario qui se sert de ce qu'il
    teste pour préparer ce qu'il teste ne mesure plus rien.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        f"{ENDPOINT}{path}",
        data=data,
        method="POST" if data else "GET",
    )
    request.add_header("accept", "application/json")
    if data:
        request.add_header("content-type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read() or b"{}")
    if not isinstance(payload, dict):
        raise IntegrationError(f"{path} : réponse inattendue de l'émulateur")
    return payload


def total_servers() -> int:
    """Ce que l'émulateur compte, dit par lui et non déduit."""
    listed = call(f"/instance/v1/zones/{ZONE}/servers?per_page=1&page=1")
    total = listed.get("total_count")
    if not isinstance(total, (int, str)):
        raise IntegrationError("l'émulateur ne rend pas de total_count sur ListServers")
    return int(total)


def seed(count: int) -> tuple[int, str]:
    """Crée les serveurs, et rend le total et l'identifiant du premier.

    Le total est relu plutôt que supposé : un émulateur adopté peut déjà
    contenir des serveurs, et le playbook doit comparer au vrai nombre.
    """
    before = total_servers()
    premier = ""
    for index in range(1, count + 1):
        cree = call(
            f"/instance/v1/zones/{ZONE}/servers",
            {
                "name": f"ansible-integration-{index:03d}",
                "commercial_type": "DEV1-S",
                "image": "ubuntu_jammy",
            },
        )
        if not premier:
            serveur = cree.get("server")
            if not isinstance(serveur, dict) or not serveur.get("id"):
                raise IntegrationError("CreateServer n'a pas rendu d'identifiant de serveur")
            premier = str(serveur["id"])

    after = total_servers()
    if after != before + count:
        raise IntegrationError(
            f"amorçage incomplet : {after - before} serveur(s) créé(s) pour {count} demandé(s)"
        )
    return after, premier


def power_on(server_id: str) -> None:
    """Allume un serveur et attend qu'il soit réellement `running`.

    L'amorçage passe par l'API et non par un module : ce qui est testé ne doit
    pas préparer ce qui le teste. Sous `FEINT_VM=off` l'état bascule tout de
    suite ; sous `incus-ovn` une machine démarre pour de bon, et l'attente est
    la même parce que la seule chose qui compte est l'état que l'API annonce.
    """
    call(f"/instance/v1/zones/{ZONE}/servers/{server_id}/action", {"action": "poweron"})

    limite = time.monotonic() + BOOT_TIMEOUT_SECONDS
    etat = "inconnu"
    while time.monotonic() < limite:
        serveur = call(f"/instance/v1/zones/{ZONE}/servers/{server_id}").get("server")
        etat = serveur.get("state", "inconnu") if isinstance(serveur, dict) else "inconnu"
        if etat == "running":
            return
        time.sleep(1)

    raise IntegrationError(
        f"le serveur {server_id} est resté en '{etat}' après {BOOT_TIMEOUT_SECONDS} s "
        f"(machines : {VM_MODE})"
    )


def inventory_graph(environment: dict[str, str]) -> dict[str, object]:
    """Ce que le plugin d'inventaire rend, lu par `ansible-inventory`.

    C'est la seule façon honnête de mesurer un plugin d'inventaire : appeler
    ses fonctions dans un test unitaire prouve qu'elles calculent, pas
    qu'Ansible sait les charger, résoudre le nom du plugin, appliquer le cache
    et rendre un graphe.
    """
    binaire = str(Path(sys.executable).parent / "ansible-inventory")
    lu = run([binaire, "-i", str(INVENTORY), "--list"], capture=True, env=environment)
    if lu.returncode != 0:
        raise IntegrationError(f"`ansible-inventory --list` a échoué :\n{lu.stderr}")
    try:
        graphe = json.loads(lu.stdout or "{}")
    except ValueError as erreur:
        raise IntegrationError(f"`ansible-inventory` n'a pas rendu du JSON : {erreur}") from erreur
    if not isinstance(graphe, dict):
        raise IntegrationError("`ansible-inventory` a rendu autre chose qu'un objet")
    return graphe


def section(source: dict[str, object], cle: str) -> dict[str, object]:
    """Une sous-partie du graphe, typée, ou un dictionnaire vide.

    Le JSON d'`ansible-inventory` est du `dict[str, object]` : le traverser
    sans vérifier chaque étage revient à supposer sa forme, et c'est ce que
    mypy refuse à juste titre.
    """
    valeur = source.get(cle)
    return valeur if isinstance(valeur, dict) else {}


def unwrap(valeur: object) -> object:
    """Déballe ce qu'`ansible-inventory` marque comme non sûr.

    Une chaîne rendue par un plugin d'inventaire ressort du `--list` sous la
    forme `{"__ansible_unsafe": "..."}`. C'est normal, c'est le marquage
    d'Ansible, et un contrôle qui l'ignore compare une chaîne à un
    dictionnaire et se trompe de diagnostic.
    """
    if isinstance(valeur, dict) and set(valeur) == {"__ansible_unsafe"}:
        return valeur["__ansible_unsafe"]
    return valeur


def check_strict_mode_is_visible(environment: dict[str, str]) -> None:
    """Mesure ce qu'Ansible fait vraiment d'un plugin d'inventaire qui refuse.

    Le plugin lève, avec un message qui nomme le produit, la région et la
    cause. Mais **`ansible-inventory` déclasse cet échec en avertissement et
    sort en 0** : par défaut, une source d'inventaire qui ne se lit pas n'est
    pas une erreur pour Ansible. Un utilisateur qui compte sur `strict: true`
    pour arrêter sa CI ne serait donc pas arrêté.

    Ce contrôle mesure les deux moitiés du fait, parce que la documentation
    les affirme toutes les deux : sans `any_unparsed_is_failed`, la sortie est
    0 et l'inventaire est vide ; avec, la sortie est non nulle.
    """
    binaire = str(Path(sys.executable).parent / "ansible-inventory")
    injoignable = {**environment, "SCW_API_URL": "http://127.0.0.1:1"}
    commande = [binaire, "-i", str(INVENTORY), "--list"]

    sans_garde = run(commande, capture=True, env=injoignable)
    if sans_garde.returncode != 0:
        raise IntegrationError(
            "`ansible-inventory` a échoué sur un point de terminaison injoignable. "
            "C'est ce qu'on voudrait, mais ce n'est pas ce qu'Ansible faisait quand "
            "cette documentation a été écrite : la relire avant de l'annoncer."
        )
    vide = json.loads(sans_garde.stdout or "{}")
    if section(section(vide, "_meta"), "hostvars"):
        raise IntegrationError("l'inventaire a rendu des machines sans API joignable")

    avec_garde = run(
        commande,
        capture=True,
        env={**injoignable, "ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED": "True"},
    )
    if avec_garde.returncode == 0:
        raise IntegrationError(
            "avec ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED, un inventaire qui ne se "
            "lit pas doit faire échouer la commande, et il ne le fait pas"
        )
    if "DiscoveryFailed" not in (avec_garde.stdout + avec_garde.stderr):
        raise IntegrationError(
            "l'échec ne nomme pas sa cause : le message du plugin n'est pas remonté"
        )
    print(
        "mode strict : refus visible seulement avec "
        "ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED, mesuré dans les deux sens"
    )


def check_inventory(environment: dict[str, str], expected: int, running_id: str) -> None:
    """Vérifie le graphe sur ses nombres, pas sur sa mise en forme.

    Trois choses se prouvent ici, et aucune ne se prouve hors ligne :

    * le **compte** correspond à ce que l'émulateur dit contenir. Un plugin
      qui pagine mal en rendrait cent, ce qui ressemble beaucoup à un parc ;
    * l'**identité** est présente sur chaque machine, parce que c'est elle qui
      permet aux modules Day-2 d'agir dessus ;
    * l'état **mesuré** apparaît : le serveur allumé plus haut est dans
      `scw_state_running`, ce qui prouve que le groupe suit l'API et non une
      valeur recopiée.
    """
    graphe = inventory_graph(environment)
    if "_meta" not in graphe:
        raise IntegrationError("le graphe rendu ne porte pas de `_meta`")
    hostvars = section(section(graphe, "_meta"), "hostvars")

    if len(hostvars) != expected:
        raise IntegrationError(
            f"l'inventaire rend {len(hostvars)} machine(s), l'émulateur en compte "
            f"{expected}. Un écart ici veut dire pagination incomplète, filtre "
            f"involontaire, ou collision de noms d'hôtes."
        )

    sans_identite = sorted(
        nom
        for nom in hostvars
        if not unwrap(section(hostvars, nom).get("scaleway_id"))
        or not unwrap(section(hostvars, nom).get("scaleway_product"))
    )
    if sans_identite:
        raise IntegrationError(
            f"{len(sans_identite)} machine(s) sans identité Scaleway, "
            f"dont {sans_identite[:3]} : les modules Day-2 ne pourraient pas agir dessus"
        )

    allumes = section(graphe, "scw_state_running").get("hosts") or []
    if not isinstance(allumes, list):
        raise IntegrationError("`scw_state_running` ne porte pas une liste de machines")
    identifiants = {
        unwrap(section(hostvars, str(nom)).get("scaleway_id"))
        for nom in allumes
        if str(nom) in hostvars
    }
    if running_id not in identifiants:
        raise IntegrationError(
            f"le serveur {running_id}, allumé et vu `running` par l'API, n'est pas "
            f"dans `scw_state_running` ({len(allumes)} machine(s) dedans)"
        )

    groupes = sorted(cle for cle in graphe if cle.startswith("scw_"))
    print(
        f"inventaire : {len(hostvars)} machines, {len(groupes)} groupes natifs, "
        f"{len(allumes)} allumée(s)"
    )


def main() -> int:
    binary = feint_binary()
    collection = load_collection()
    workdir = Path(tempfile.mkdtemp(prefix="scaleway-integration-"))
    adopted = answers(binary)

    if adopted:
        check_adopted_mode(binary)
        print(
            f"émulateur déjà en écoute sur {ADDRESS} (machines : {machine_mode(binary)}) : "
            "adopté, il ne sera pas arrêté"
        )
    else:
        started = run(start_command(binary, workdir / "state.json"), capture=True)
        if started.returncode != 0:
            print(started.stdout + started.stderr, file=sys.stderr)
            raise IntegrationError(f"feint n'a pas démarré sur {ADDRESS}")
        print(started.stdout.strip() + f"  (machines : {VM_MODE})")

    try:
        expected, premier = seed(SEEDED_SERVERS)
        print(f"{SEEDED_SERVERS} serveurs amorcés dans {ZONE}, {expected} au total")

        depart = time.monotonic()
        power_on(premier)
        print(f"serveur {premier} allumé et running en {time.monotonic() - depart:.1f} s")

        environment = {
            **os.environ,
            **client_environment(binary),
            "ANSIBLE_COLLECTIONS_PATH": str(collection.collections_root),
            # Le scénario est hermétique : aucune configuration locale ne doit
            # pouvoir s'y inviter.
            "SCW_CONFIG_PATH": str(workdir / "absent.yaml"),
            "FEINT_SEEDED_SERVERS": str(expected),
            "FEINT_RUNNING_SERVER": premier,
            "ANSIBLE_LOCALHOST_WARNING": "False",
            "ANSIBLE_INVENTORY_UNPARSED_WARNING": "False",
        }
        ansible_playbook = str(Path(sys.executable).parent / "ansible-playbook")
        # Les mêmes variables qu'un utilisateur passerait en ligne de commande.
        # Un playbook qui ne s'en sert pas les ignore.
        variables = ["-e", f"zone={ZONE}", "-e", f"server_id={premier}"]
        # L'inventaire d'abord, et ce n'est pas un détail d'ordonnancement :
        # un des playbooks livrés **arrête** le serveur allumé plus haut. Le
        # mesurer après ferait chercher dans `scw_state_running` une machine
        # qu'un playbook vient d'éteindre, et le scénario accuserait
        # l'inventaire d'un état que lui-même a changé.
        print(f"\n--- {os.path.relpath(INVENTORY, ROOT)} ---", flush=True)
        check_inventory(environment, expected, premier)
        check_strict_mode_is_visible(environment)

        print(f"\n--- {os.path.relpath(INVENTORY_PLAYBOOK, ROOT)} ---", flush=True)
        code = run(
            [ansible_playbook, "-i", str(INVENTORY), str(INVENTORY_PLAYBOOK)],
            env=environment,
        ).returncode

        for chemin in playbooks(collection):
            print(f"\n--- {os.path.relpath(chemin, ROOT)} ---", flush=True)
            joue = run([ansible_playbook, *variables, str(chemin)], env=environment)
            code = code or joue.returncode
        return code
    finally:
        # On n'arrête que ce qu'on a démarré : en CI, l'émulateur appartient à
        # l'action qui l'a lancé, et d'autres étapes peuvent en avoir besoin.
        if not adopted:
            run([binary, "stop", "--addr", ADDRESS], capture=True)
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IntegrationError as error:
        print(f"erreur : {error}", file=sys.stderr)
        raise SystemExit(1) from error
