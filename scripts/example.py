"""Déploie la plateforme d'exemple, l'exploite avec la collection, puis la détruit.

Trois cibles, une seule stack et un seul jeu de playbooks :

    emulateur     feint en `--vm off`. Le plan de contrôle seul : rien ne
                  démarre, donc aucun playbook SSH. Rapide, gratuit, hors ligne.
    machines      feint en `--vm incus-ovn`. De vraies machines démarrent, avec
                  un vrai réseau : l'application se déploie pour de bon.
    reel          le compte Scaleway réel. Même stack, mêmes playbooks, et un
                  contrôle de résidu qui encadre l'exécution.

**La destruction est dans un `finally`.** Elle a lieu quand l'application
échoue, quand un playbook échoue, et quand l'utilisateur interrompt. C'est la
seule forme qui tienne la promesse « aucune ressource ne subsiste » : une
destruction qu'on n'atteint qu'en cas de succès ne protège que des succès.

    python scripts/example.py emulateur
    python scripts/example.py machines
    python scripts/example.py reel

`--garder` laisse la plateforme debout pour l'inspecter. Contre le cloud réel,
l'option demande une confirmation explicite : ce qui reste debout est facturé.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "examples" / "stack"
PLAYBOOKS = ROOT / "examples" / "playbooks"
TRAVAIL = ROOT / "build" / "example"
CLE = TRAVAIL / "cle"

#: L'adresse de l'émulateur de **cet exercice**, et surtout pas 4599.
#:
#: 4599 est le port par défaut de feint, donc celui qu'un poste où feint est
#: développé occupe déjà. Un exercice qui s'y installe adopte l'émulateur du
#: mainteneur, y crée trente-sept ressources, puis les détruit : ce n'est pas
#: une gêne, c'est une destruction de travail en cours.
#:
#: `FEINT_ADDR` reste honoré pour viser un émulateur précis.
ADRESSE = os.environ.get("FEINT_ADDR", "127.0.0.1:4877")
ENDPOINT = f"http://{ADRESSE}"

#: Ce que chaque cible implique. `vm` est le mode de l'émulateur, `ssh` dit si
#: les playbooks qui se connectent aux machines ont un sens.
CIBLES: dict[str, dict[str, Any]] = {
    "emulateur": {"emulateur": True, "vm": "off", "ssh": False},
    "machines": {"emulateur": True, "vm": "incus-ovn", "ssh": True},
    "reel": {"emulateur": False, "vm": None, "ssh": True},
}


class ExempleError(RuntimeError):
    """L'exercice ne peut pas être joué, et il faut le dire au lieu de sauter."""


def lancer(
    commande: list[str],
    *,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(commande, env=env, text=True, check=False, capture_output=capture)


def binaire(nom: str) -> str:
    chemin = shutil.which(nom)
    if not chemin:
        raise ExempleError(
            f"{nom} est introuvable. Cet exercice échoue plutôt que de se sauter : "
            "un exemple qui se saute tout seul finit par ne plus jamais tourner."
        )
    return chemin


def cle_ssh() -> str:
    """La clé de l'exercice, créée une fois et gardée sous `build/`.

    Elle ne vit pas dans le dépôt : c'est une clé de poste, pas un artefact du
    produit, et elle n'a d'intérêt que pour la plateforme éphémère.
    """
    TRAVAIL.mkdir(parents=True, exist_ok=True)
    if not CLE.exists():
        lancer(
            [
                binaire("ssh-keygen"),
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "exemple-collection-scaleway",
                "-f",
                str(CLE),
            ]
        )
    return (CLE.with_suffix(".pub")).read_text(encoding="utf-8").strip()


def refuser_emulateur_habite(_env: dict[str, str]) -> None:
    """Refuse d'adopter un émulateur qui contient déjà quelque chose.

    Cet exercice crée trente-sept ressources puis les **détruit**. Adopter
    l'émulateur de quelqu'un d'autre reviendrait donc à détruire son travail en
    cours, et feint est développé sur la même machine que ce dépôt.

    Le port par défaut de l'exercice n'est déjà pas celui de feint. Cette garde
    est la seconde barrière, celle qui tient même quand `FEINT_ADDR` désigne
    autre chose que prévu.
    """
    import requests

    try:
        reponse = requests.get(
            f"{ENDPOINT}/instance/v1/zones/fr-par-1/servers?per_page=1", timeout=10
        )
        reponse.raise_for_status()
        total = int(reponse.json().get("total_count") or 0)
    except Exception as erreur:
        raise ExempleError(
            f"un émulateur écoute sur {ADRESSE} mais ne répond pas à une lecture "
            f"simple ({erreur}). L'exercice refuse de l'adopter : il détruit ce "
            "qu'il a créé, et il ne sait pas ce qu'il détruirait."
        ) from erreur

    if total:
        raise ExempleError(
            f"un émulateur écoute sur {ADRESSE} et contient déjà {total} "
            "serveur(s). L'exercice refuse de l'adopter : il termine par une "
            "destruction, et celle-ci emporterait ce qui s'y trouve.\n"
            "Choisir une autre adresse avec FEINT_ADDR, ou arrêter cet émulateur."
        )


def environnement_emulateur() -> dict[str, str]:
    """Les identifiants que l'émulateur accepte, dits par lui et non inventés."""
    resultat = lancer([binaire("feint"), "env", "scaleway", "--endpoint", ENDPOINT], capture=True)
    if resultat.returncode != 0:
        raise ExempleError(f"`feint env scaleway` a échoué :\n{resultat.stderr}")
    valeurs: dict[str, str] = {}
    for ligne in resultat.stdout.splitlines():
        if ligne.startswith("export "):
            nom, _, valeur = ligne.removeprefix("export ").partition("=")
            valeurs[nom.strip()] = valeur.strip().strip("'\"")
    if valeurs.get("SCW_API_URL") != ENDPOINT:
        raise ExempleError(
            f"`feint env` n'a pas donné SCW_API_URL={ENDPOINT}. L'exercice s'arrête : "
            "sans cette variable, Terraform et les playbooks parleraient à l'API réelle."
        )
    return valeurs


def terraform(
    action: str,
    env: dict[str, str],
    variables: dict[str, str],
    *,
    json_sortie: bool = False,
) -> subprocess.CompletedProcess[str]:
    commande = [binaire("terraform"), f"-chdir={STACK}", action, "-no-color", "-input=false"]
    if action in ("apply", "destroy"):
        commande.append("-auto-approve")
    if action == "output":
        commande = [binaire("terraform"), f"-chdir={STACK}", "output", "-json"]
    else:
        for nom, valeur in variables.items():
            commande += ["-var", f"{nom}={valeur}"]
    return lancer(commande, env=env, capture=json_sortie)


def inventaire(env: dict[str, str]) -> dict[str, Any]:
    """Le graphe que le plugin construit sur la plateforme déployée."""
    binaire_ansible = str(Path(sys.executable).parent / "ansible-inventory")
    resultat = lancer(
        [binaire_ansible, "-i", str(PLAYBOOKS / "inventaire.scaleway.yml"), "--list"],
        env=env,
        capture=True,
    )
    if resultat.returncode != 0:
        raise ExempleError(f"`ansible-inventory` a échoué :\n{resultat.stderr}")
    graphe = json.loads(resultat.stdout or "{}")
    if not isinstance(graphe, dict):
        raise ExempleError("`ansible-inventory` a rendu autre chose qu'un objet")
    return graphe


def controler_inventaire(graphe: dict[str, Any], attendu: dict[str, int]) -> None:
    """Ce que l'inventaire doit avoir trouvé, comparé à ce que la stack a créé.

    C'est le contrôle qui refuse un vert obtenu sur rien : un plugin qui ne
    trouve aucune machine construit un inventaire parfaitement valide.
    """
    hostvars = graphe.get("_meta", {}).get("hostvars", {})
    if len(hostvars) != attendu["total"]:
        raise ExempleError(
            f"l'inventaire rend {len(hostvars)} machine(s), la stack en a créé {attendu['total']}"
        )

    roles = (("bastion", attendu["bastion"]), ("web", attendu["web"]), ("app", attendu["app"]))
    for role, compte in roles:
        groupe = graphe.get(f"scw_tag_role_{role}", {}).get("hosts", [])
        if len(groupe) != compte:
            raise ExempleError(
                f"le groupe scw_tag_role_{role} porte {len(groupe)} machine(s), "
                f"la stack en a créé {compte}"
            )

    # Le point qui distingue ce plugin : quatre machines sur cinq n'ont aucune
    # adresse publique, et doivent quand même être joignables.
    sans_prive = sorted(
        nom
        for nom, variables in hostvars.items()
        if not _valeur(variables.get("scaleway_private_ipv4"))
    )
    if sans_prive:
        raise ExempleError(
            f"{len(sans_prive)} machine(s) sans adresse privée découverte, dont "
            f"{sans_prive[:3]} : la jointure IPAM n'a pas eu lieu"
        )
    print(
        f"inventaire : {len(hostvars)} machines, "
        f"{len([c for c in graphe if c.startswith('scw_')])} groupes natifs, "
        "toutes jointes par une adresse privée"
    )


def api(env: dict[str, str], chemin: str) -> Any:
    """Interroge l'API directement, sans passer par ce qu'on veut vérifier.

    Un contrôle qui se sert de la collection pour juger la collection ne
    mesure plus rien : ces lectures passent par le client officiel.
    """
    import requests
    from scaleway_core.profile import Profile

    # Les identifiants viennent du profil, pas seulement de l'environnement.
    # Contre l'émulateur, `feint env` les exporte ; contre le cloud réel ils
    # vivent dans `~/.config/scw/config.yaml`, et l'environnement est vide.
    # Ne lire que l'environnement produisait un 401 **après** un `apply`
    # réussi : la stack tenait, c'est le contrôle qui ne savait pas
    # s'authentifier, ce qui est la pire façon d'échouer.
    profil = Profile.from_config_file_and_env(None, env.get("SCW_PROFILE") or "default")
    base = env.get("SCW_API_URL") or profil.api_url or "https://api.scaleway.com"
    jeton = env.get("SCW_SECRET_KEY") or profil.secret_key

    entetes = {"accept": "application/json"}
    if jeton:
        entetes["x-auth-token"] = jeton
    reponse = requests.get(f"{base}{chemin}", headers=entetes, timeout=30)
    reponse.raise_for_status()
    return reponse.json()


def controler_plan_de_controle(env: dict[str, str], sorties: dict[str, Any]) -> None:
    """Tout ce que la plateforme déclare, vérifié auprès de l'API.

    Ces contrôles valent dans **les trois cibles**, machines démarrées ou non :
    ils portent sur le plan de contrôle, pas sur ce qui tourne dedans. C'est ce
    qui donne sa valeur à la cible rapide, et c'est aussi le test différentiel
    de l'émulateur : un écart ici entre l'émulateur et le cloud réel est un
    défaut de l'émulateur.
    """
    zone = env.get("SCW_DEFAULT_ZONE", "fr-par-1")
    region = env.get("SCW_DEFAULT_REGION", "fr-par")
    attendu = sorties["attendu"]["value"]
    prefixe = f"acs-{sorties['run_id']['value']}"
    constats: list[str] = []

    def exige(condition: bool, message: str) -> None:
        constats.append(("ok  " if condition else "ÉCHEC ") + message)
        if not condition:
            raise ExempleError(f"plan de contrôle : {message}")

    vpcs = [
        v
        for v in api(env, f"/vpc/v2/regions/{region}/vpcs")["vpcs"]
        if v["name"].startswith(prefixe)
    ]
    exige(len(vpcs) == 1, f"le VPC de la plateforme ({len(vpcs)} trouvé)")

    reseaux = [
        r
        for r in api(env, f"/vpc/v2/regions/{region}/private-networks")["private_networks"]
        if r["name"].startswith(prefixe)
    ]
    exige(len(reseaux) == 3, f"trois réseaux privés ({len(reseaux)} trouvés)")

    groupes = [
        g
        for g in api(env, f"/instance/v1/zones/{zone}/security_groups")["security_groups"]
        if g["name"].startswith(prefixe)
    ]
    exige(len(groupes) == 3, f"un groupe de sécurité par étage ({len(groupes)} trouvés)")

    lbs = [
        item
        for item in api(env, f"/lb/v1/zones/{zone}/lbs")["lbs"]
        if item["name"].startswith(prefixe)
    ]
    exige(len(lbs) == 1, f"un load balancer ({len(lbs)} trouvé)")
    cibles = api(env, f"/lb/v1/zones/{zone}/lbs/{lbs[0]['id']}/backends")["backends"]
    exige(len(cibles) == 1, "un backend déclaré")
    exige(
        len(cibles[0]["pool"]) == attendu["web"],
        f"le backend pointe les {attendu['web']} machines web ({len(cibles[0]['pool'])} cibles)",
    )

    passerelles = [
        g
        for g in api(env, f"/vpc-gw/v2/zones/{zone}/gateways")["gateways"]
        if g["name"].startswith(prefixe)
    ]
    exige(len(passerelles) == 1, f"une passerelle publique ({len(passerelles)} trouvée)")

    attaches = api(env, f"/vpc-gw/v2/zones/{zone}/gateway-networks")["gateway_networks"]
    exige(
        len([a for a in attaches if a["gateway_id"] == passerelles[0]["id"]]) == 2,
        "la passerelle porte la sortie des tiers web et applicatif",
    )

    placement = [
        p
        for p in api(env, f"/instance/v1/zones/{zone}/placement_groups")["placement_groups"]
        if p["name"].startswith(prefixe)
    ]
    exige(len(placement) == 1, "un groupe de placement pour le tier applicatif")

    instantanes = [
        s
        for s in api(env, f"/block/v1alpha1/zones/{zone}/snapshots")["snapshots"]
        if s["name"].startswith(prefixe)
    ]
    exige(len(instantanes) == 1, "un instantané Block du disque système du bastion")

    images = [
        i
        for i in api(env, f"/instance/v1/zones/{zone}/images")["images"]
        if i["name"].startswith(prefixe)
    ]
    if sorties["image_doree"]["value"]:
        exige(len(images) == 1, "une image d'or taillée dedans")
    else:
        # Écarté, et dit. L'émulateur crée l'instantané par l'API Block puis rend
        # 404 sur le même identifiant côté Instance (feint#651), donc la stack ne
        # déclare pas l'image hors cible réelle. Le contrôle ne se tait pas pour
        # autant : il affirme l'absence, sans quoi une image oubliée un jour sur
        # le compte passerait inaperçue ici.
        exige(
            len(images) == 0,
            "image d'or écartée hors cible réelle, et absente comme prévu (feint#651)",
        )

    charge = api(env, f"/block/v1alpha1/zones/{zone}/volumes")["volumes"]
    volumes = [v for v in charge if v["name"].startswith(prefixe)]
    exige(
        len(volumes) >= attendu["app"],
        f"un volume Block Storage par machine applicative ({len(volumes)} trouvés)",
    )

    print("plan de contrôle vérifié :")
    for constat in constats:
        print(f"  {constat}")


def _valeur(brut: Any) -> Any:
    if isinstance(brut, dict) and set(brut) == {"__ansible_unsafe"}:
        return brut["__ansible_unsafe"]
    if isinstance(brut, list):
        return [_valeur(item) for item in brut]
    return brut


def controler_sortie_internet(bastion_ip: str) -> None:
    """Les machines peuvent-elles joindre l'internet, avant de leur demander d'installer.

    Sans cette sonde, l'absence de sortie se manifeste dix tâches plus loin par
    « Failed to update apt cache after 5 retries », qui désigne le dépôt de
    paquets, le miroir, ou le DNS. Trois choses innocentes. La cause se mesure
    en six secondes depuis le bastion, et une cause nommée vaut mieux qu'un
    symptôme.
    """
    sonde = [
        "ssh",
        "-F",
        "/dev/null",
        "-i",
        str(CLE),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "BatchMode=yes",
        f"root@{bastion_ip}",
        'timeout 6 bash -c "</dev/tcp/1.1.1.1/443"',
    ]
    if lancer(sonde, capture=True).returncode == 0:
        print("sortie internet : joignable depuis le bastion")
        return
    raise ExempleError(
        "les machines n'ont aucune sortie vers l'internet, donc aucun paquet ne "
        "s'installera.\n"
        "  Sous `incus-ovn`, c'est feint#647 : le bastion porte bien une route par "
        "défaut et le trafic\n"
        "  ne sort pas, et `push_default_route` n'installe aucune route. Mesuré, "
        "et la même stack\n"
        "  converge sur le cloud réel. Ce n'est pas un défaut de la plateforme "
        "d'exemple :\n"
        "  `mise run example:reel` la joue entièrement."
    )


def jouer(playbook: str, env: dict[str, str], variables: dict[str, str]) -> int:
    binaire_ansible = str(Path(sys.executable).parent / "ansible-playbook")
    inventaire_fichier = str(PLAYBOOKS / "inventaire.scaleway.yml")
    commande = [binaire_ansible, "-i", inventaire_fichier, str(PLAYBOOKS / playbook)]
    for nom, valeur in variables.items():
        commande += ["-e", f"{nom}={valeur}"]
    print(f"\n--- {playbook} ---", flush=True)
    code: int = lancer(commande, env=env).returncode
    return code


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("cible", choices=sorted(CIBLES))
    parseur.add_argument("--garder", action="store_true", help="ne pas détruire à la fin")
    arguments = parseur.parse_args(argv[1:])
    cible = CIBLES[arguments.cible]

    if arguments.garder and not cible["emulateur"]:
        raise ExempleError(
            "`--garder` contre le cloud réel laisse des ressources facturées debout. "
            "Relancer sans l'option, ou détruire à la main avec `terraform -chdir="
            "examples/stack destroy` puis `python scripts/residue.py verify`."
        )

    run_id = f"{int(time.time()) % 100000}{secrets.token_hex(2)}"
    variables = {"run_id": run_id, "ssh_public_key": cle_ssh()}
    env = dict(os.environ)
    adopte = False

    if cible["emulateur"]:
        variables["endpoint"] = ENDPOINT
        sonde = lancer(
            [binaire("feint"), "wait", "--addr", ADRESSE, "--timeout", "2s"], capture=True
        )
        adopte = sonde.returncode == 0
        if adopte:
            refuser_emulateur_habite(env_probe := dict(os.environ))
            del env_probe
        if not adopte:
            demarrage = lancer(
                [
                    binaire("feint"),
                    "start",
                    "--addr",
                    ADRESSE,
                    "--vm",
                    cible["vm"],
                    "--cleanup",
                    "--timeout",
                    "180s",
                ],
                capture=True,
            )
            if demarrage.returncode != 0:
                raise ExempleError(f"feint n'a pas démarré :\n{demarrage.stderr}")
            print(demarrage.stdout.strip())
        env.update(environnement_emulateur())
        env["SCW_CONFIG_PATH"] = str(TRAVAIL / "absent.yaml")
    else:
        variables["endpoint"] = ""
        print("cible : le compte Scaleway réel. Prise de la référence de résidu.")
        residu = [sys.executable, str(ROOT / "scripts" / "residue.py"), "capture"]
        if lancer(residu).returncode != 0:
            raise ExempleError("la référence de résidu n'a pas pu être prise")

    env["ANSIBLE_COLLECTIONS_PATH"] = str(ROOT)
    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    env["ANSIBLE_PRIVATE_KEY_FILE"] = str(CLE)
    env["ANSIBLE_LOCALHOST_WARNING"] = "False"

    code = 0
    try:
        if terraform("init", env, {}).returncode != 0:
            raise ExempleError("`terraform init` a échoué")
        if terraform("apply", env, variables).returncode != 0:
            raise ExempleError("`terraform apply` a échoué")

        sorties = json.loads(terraform("output", env, {}, json_sortie=True).stdout or "{}")
        attendu = sorties["attendu"]["value"]
        bastion_ip = sorties["bastion_ip"]["value"]
        application_url = sorties["application_url"]["value"]
        print(f"plateforme déployée : {attendu['total']} machines, bastion {bastion_ip}")

        controler_plan_de_controle(env, sorties)
        controler_inventaire(inventaire(env), attendu)

        if cible["ssh"]:
            controler_sortie_internet(bastion_ip)
            extra = {
                "bastion_ip": bastion_ip,
                "application_url": application_url,
                "ssh_key": str(CLE),
            }
            code = jouer("site.yml", env, extra) or jouer("verifier.yml", env, extra)
        else:
            print(
                "cible sans machines : les playbooks SSH ne sont pas joués, et c'est "
                "dit plutôt que sauté en silence. Utiliser `machines` ou `reel` pour eux."
            )
        return code
    finally:
        if arguments.garder:
            print("\nplateforme conservée. La détruire avec :")
            print(f"  terraform -chdir=examples/stack destroy -auto-approve -var run_id={run_id}")
        else:
            print("\n--- destruction ---", flush=True)
            if terraform("destroy", env, variables).returncode != 0:
                print(
                    "LA DESTRUCTION A ÉCHOUÉ. Ne pas en rester là : relancer "
                    "`terraform -chdir=examples/stack destroy`, puis vérifier.",
                    file=sys.stderr,
                )
                code = 1
            if not cible["emulateur"]:
                verifier = [sys.executable, str(ROOT / "scripts" / "residue.py"), "verify"]
                if lancer(verifier).returncode != 0:
                    code = 1
        if cible["emulateur"] and not adopte and not arguments.garder:
            lancer([binaire("feint"), "stop", "--addr", ADRESSE], capture=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except ExempleError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
