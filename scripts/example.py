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
import re
import secrets
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deblocage
import verrou_plateforme

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "examples" / "stack"
PLAYBOOKS = ROOT / "examples" / "playbooks"
RAPPELS = ROOT / "examples" / "callback_plugins"
TRAVAIL = ROOT / "build" / "example"
CLE = TRAVAIL / "cle"

#: Préfixe des modules de la collection, pour les distinguer d'`ansible.builtin`.
PREFIXE_COLLECTION = "stephrobert.scaleway."

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

#: L'adresse du proxy d'enregistrement, distincte de celle de l'émulateur.
#:
#: Les deux ne servent pas la même chose et ne doivent jamais se confondre :
#: l'émulateur **répond** à la place du cloud, le proxy **transmet** au cloud
#: et note ce qui passe. Un run qui les mélangerait croirait mesurer le réel
#: en interrogeant une imitation.
PROXY = os.environ.get("FEINT_PROXY_ADDR", "127.0.0.1:4878")

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


#: Ce que `feint status` rend pour chaque mode de démarrage. **Mesuré le
#: 2026-09-11**, en démarrant un émulateur dans chaque mode et en lisant sa
#: sortie : `--vm off` se déclare `none`, les autres se déclarent sous leur
#: propre nom. Supposer la table ferait refuser une cible parfaitement valide,
#: ce qui est pire que l'absence de garde.
MODES_DECLARES: dict[str, str] = {"off": "none"}


def mode_servi(adresse: str) -> str | None:
    """Le mode de machines de l'émulateur qui écoute, tel qu'il le déclare.

    `None` quand la question n'a pas de réponse : l'émulateur ne répond pas à
    `status`, ou répond quelque chose qui n'est pas du JSON. L'appelant refuse
    alors, plutôt que de supposer.
    """
    resultat = lancer(
        [binaire("feint"), "status", "--addr", adresse, "--format", "json"], capture=True
    )
    if resultat.returncode != 0:
        return None
    try:
        declare = json.loads(resultat.stdout or "{}").get("machines")
    except ValueError:
        return None
    return None if declare is None else str(declare)


def refuser_un_mode_incompatible(cible: dict[str, Any], adresse: str) -> None:
    """Refuse d'adopter un émulateur qui ne sert pas le mode que la cible exige.

    **La garde voisine contrôle une propriété et laissait passer celle-ci.**
    `refuser_emulateur_habite` demande si l'émulateur contient quelque chose ;
    un émulateur vide en `--vm off` lui convient donc, et `machines` l'aurait
    adopté avant de jouer des playbooks SSH contre des machines qui ne démarrent
    jamais. L'échec serait arrivé après plusieurs minutes d'attente, et il
    aurait accusé les playbooks : `wait_for_connection` sur un hôte injoignable
    ne dit rien du mode de l'émulateur (#187).

    **Refuser n'est pas bloquer.** L'exercice reste lançable pendant qu'un autre
    émulateur tourne, sur une autre adresse, et le message le dit plutôt que
    d'arrêter le processus de quelqu'un d'autre : c'est exactement ce que la
    garde voisine existe pour empêcher.
    """
    attendu = MODES_DECLARES.get(cible["vm"], cible["vm"])
    servi = mode_servi(adresse)

    if servi is None:
        raise ExempleError(
            f"un émulateur écoute sur {adresse} et ne dit pas dans quel mode. "
            "L'exercice refuse de l'adopter : il ne sait pas si les machines "
            "qu'il va demander démarreront.\n"
            f"Choisir une autre adresse avec FEINT_ADDR, ou arrêter cet émulateur."
        )

    if servi != attendu:
        raise ExempleError(
            f"un émulateur écoute sur {adresse} et sert les machines en "
            f"« {servi} », quand cette cible demande « {attendu} ». L'exercice "
            "refuse de l'adopter : les playbooks qui se connectent aux machines "
            "attendraient des hôtes que personne ne démarre, et l'échec "
            "accuserait les playbooks.\n"
            "Choisir une autre adresse avec FEINT_ADDR, et l'exercice démarrera "
            "le sien dans le bon mode."
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


def demarrer_proxy(chemin: str) -> subprocess.Popen[str]:
    """Lance `feint proxy` devant l'API réelle, et attend qu'il réponde.

    **Il transmet, il ne répond pas à la place.** C'est ce qui le distingue de
    l'émulateur, et ce qui fait de sa transcription une mesure du cloud plutôt
    qu'une mesure d'une imitation.

    Deux propriétés viennent de feint et ne se redéclarent pas ici : les
    identifiants n'atteignent jamais le fichier, la rédaction étant une
    propriété du type enregistré, et le proxy n'écoute que sur la boucle locale.
    """
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    processus = subprocess.Popen(
        [
            binaire("feint"),
            "proxy",
            "--provider",
            "scaleway",
            "--upstream",
            "https://api.scaleway.com",
            "--addr",
            PROXY,
            "--record",
            chemin,
        ],
        text=True,
    )
    for _ in range(50):
        try:
            import socket

            hote, port = PROXY.split(":")
            with socket.create_connection((hote, int(port)), timeout=0.2):
                return processus
        except OSError:
            time.sleep(0.2)
    processus.terminate()
    raise ExempleError(
        f"`feint proxy` n'écoute pas sur {PROXY}. L'exercice s'arrête plutôt que "
        "de parler au cloud sans enregistrer : un run facturé qui ne mesure rien "
        "est le pire des deux."
    )


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


#: Un identifiant que le provider Terraform a préfixé par sa portée,
#: `fr-par-1/<uuid>` ou `fr-par/<uuid>`. Le module qui le reçoit tel quel
#: compose `/frontends/fr-par-1/<uuid>`, et ce que rend l'API n'est pas une
#: erreur d'API : c'est le 404 du serveur web devant elle, que le runtime ne
#: sait pas interpréter.
PORTEE_COLLEE = re.compile(r"^[a-z]{2}-[a-z]+(?:-\d+)?/[0-9a-f]{8}-[0-9a-f-]{27}$")


def refuser_une_sortie_portee(sorties: dict[str, Any]) -> None:
    """Refuse une sortie Terraform qui a gardé sa portée.

    `CLAUDE.md` pose la règle : « toute sortie Terraform qui traverse vers un
    module se dépouille de sa portée, et c'est la sortie qui s'en charge, pas
    le playbook ». Elle était écrite et rien ne l'exécutait.

    Mesuré sur le compte réel le 2026-09-10 : quatre sorties sur cinq la
    violaient, `GetFrontend` rendait 400 sur l'une d'elles, et le bloc de
    mesure #119 n'a jamais tourné jusqu'au bout là où il est le seul à pouvoir
    tourner. Deux d'entre elles ne traversaient encore vers aucun module : la
    garde ne distingue pas, parce que le jour où elles traverseront, personne
    ne relira ce commentaire.
    """
    fautives = []
    for nom, contenu in sorties.items():
        valeur = contenu.get("value") if isinstance(contenu, dict) else contenu
        for element in valeur if isinstance(valeur, list) else [valeur]:
            if isinstance(element, str) and PORTEE_COLLEE.match(element):
                fautives.append(f"{nom} = {element}")
    if fautives:
        raise ExempleError(
            "sortie(s) Terraform portant encore leur portée :\n  "
            + "\n  ".join(sorted(fautives))
            + "\nUn module qui les reçoit compose une URL que l'API refuse. "
            'Les dépouiller dans `outputs.tf` : reverse(split("/", ...))[0].'
        )


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
    # **Deux backends, et le second n'est pas décoratif.** Il porte la route que
    # `lb_route` réécrit : sans lui, ce module était livré sans qu'aucun exemple
    # ne l'exerce. Un backend ne coûte rien, c'est de la configuration dans un
    # load balancer déjà facturé.
    cibles = api(env, f"/lb/v1/zones/{zone}/lbs/{lbs[0]['id']}/backends")["backends"]
    exige(len(cibles) == 2, f"deux backends déclarés ({len(cibles)} trouvé(s))")
    # **Chaque** backend, et pas le premier venu : ils sont deux depuis que
    # `lb_route` a eu besoin d'une cible, et l'ordre d'une liste d'API n'est
    # promis nulle part. Contrôler `cibles[0]` reviendrait à mesurer celui que
    # l'API a rendu en premier ce jour-là.
    for cible_lb in cibles:
        exige(
            len(cible_lb["pool"]) == attendu["web"],
            f"le backend {cible_lb['name']} pointe les {attendu['web']} machines web "
            f"({len(cible_lb['pool'])} cibles)",
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
        # Écarté, et dit. `createImage` accepte un instantané Block comme volume
        # racine sur le cloud réel, et le refusait sur l'émulateur (feint#651),
        # donc la stack ne déclare pas l'image hors cible réelle. Le contrôle ne
        # se tait pas pour autant : il affirme l'absence, sans quoi une image
        # oubliée un jour sur le compte passerait inaperçue ici.
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

    Sans cette sonde, l'absence de sortie se manifeste bien plus loin par
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


def artefact(journal: dict[str, Any], cible: str, run_id: str, residu: str) -> dict[str, Any]:
    """Ce que cette exécution a couvert, dérivé de ce qui s'est réellement joué.

    **Joué n'est pas appelé.** Analyser le playbook dirait quels modules il
    nomme ; une tâche gardée par un `when` non satisfait ne touche pourtant
    jamais l'API. Le journal vient du plugin de rappel, donc d'Ansible, qui est
    le seul à connaître la différence.

    Un module joué une fois et sauté ailleurs compte comme joué : ce qui est
    demandé est « a-t-il tourné contre cette API », pas « toutes ses tâches
    ont-elles tourné ».

    **Quatre sorts, et les mélanger envoie un rapport chez le mauvais projet.**
    Un champ unique les confondait, et la comparaison publiait « chacun a été
    appelé des deux côtés » sur un ensemble qui contenait des tâches sautées.
    Mesuré le 2026-09-11 : l'émulateur n'avait décliné que
    `GetServerTypesAvailability` et `ListVolumesTypes`, et la liste publiée y
    ajoutait `instance_image` et `lb_certificate`, que le playbook saute faute
    de ressource à viser, plus `instance_server_action`, qu'aucune tâche n'y
    nommait. Une issue déposée sur cette base part chez le mauvais projet
    (#189).

        joué      l'API a répondu, et c'est une preuve de couverture
        décliné   l'API a été appelée et a dit qu'elle ne sert pas cette route
        en échec  l'API a été appelée et a refusé
        sauté     `when` l'a écartée : personne n'a rien appelé
    """
    joues: set[str] = set()
    declines: set[str] = set()
    echoues: set[str] = set()
    sautes: set[str] = set()
    for tache in journal.get("taches", []):
        module = str(tache.get("module", ""))
        if not module.startswith(PREFIXE_COLLECTION):
            continue
        court = module[len(PREFIXE_COLLECTION) :]
        if tache.get("verdict") == "skipped":
            sautes.add(court)
        elif tache.get("api_type") == "not_emulated":
            # Une route non émulée a bien été appelée, mais l'API n'a rien fait :
            # la compter comme jouée ferait passer une limite de l'émulateur pour
            # une preuve de couverture.
            declines.add(court)
        elif tache.get("verdict") in ("ok", "changed"):
            joues.add(court)
        else:
            echoues.add(court)

    # Un appel l'emporte sur une absence d'appel, et une réponse sur un refus :
    # un module joué quelque part a tourné, quoi qu'il soit devenu ailleurs.
    declines -= joues
    echoues -= joues | declines
    sautes -= joues | declines | echoues

    faits = journal.get("faits", {})
    return {
        "cible": cible,
        "run_id": run_id,
        "horodatage": datetime.now(UTC).isoformat(timespec="seconds"),
        "modules_joues": sorted(joues),
        "modules_declines": sorted(declines),
        "modules_en_echec": sorted(echoues),
        "modules_sautes": sorted(sautes),
        "taches_jouees": len(journal.get("taches", [])),
        "routes_non_emulees": sorted(faits.get("non_emules", [])),
        "idempotence_prouvee": sorted(faits.get("idempotences_prouvees", [])),
        "reecritures_non_mesurees": sorted(faits.get("reecritures_non_mesurees", [])),
        "residu": residu,
    }


def ecrire_artefact(chemin_journal: Path, cible: str, run_id: str, residu: str) -> Path | None:
    """Écrit l'artefact à côté du journal, et rend son chemin.

    Rend `None` quand rien n'a été journalisé : un artefact vide se lirait
    comme une exécution qui n'a rien couvert, alors qu'elle n'a pas eu lieu.
    """
    if not chemin_journal.is_file():
        return None
    journal = json.loads(chemin_journal.read_text(encoding="utf-8"))
    destination = TRAVAIL / f"{cible}-{run_id}.json"
    contenu = artefact(journal, cible, run_id, residu)
    destination.write_text(
        json.dumps(contenu, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    # Un nom stable par cible, pour que la mesure suivante n'ait pas à deviner
    # quel `run_id` était le dernier.
    (TRAVAIL / f"dernier-{cible}.json").write_text(
        destination.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return destination


def jouer(playbook: str, env: dict[str, str], variables: dict[str, Any]) -> int:
    """Joue un playbook, en lui passant les variables **sans les aplatir**.

    **`-e nom=valeur` transforme toute valeur en chaîne.** Une liste Python y
    devient `"['a', 'b']"`, dont la longueur est celle du texte : une assertion
    `| length == 2` la lit à 22 et tombe. Mesuré sur un run réel, où la mesure
    d'ordre de #119 a été sautée pour cette seule raison, après quarante-cinq
    ressources créées et détruites.

    C'est exactement le défaut que l'override `csv` documente un étage plus bas,
    sur `tags` de `ListServers` : Ansible n'échoue pas, il compose une chaîne
    que personne n'attendait.

    `-e` avec un document JSON préserve les types. Une chaîne reste une chaîne,
    une liste reste une liste, et le playbook n'a plus à deviner.
    """
    binaire_ansible = str(Path(sys.executable).parent / "ansible-playbook")
    inventaire_fichier = str(PLAYBOOKS / "inventaire.scaleway.yml")
    commande = [binaire_ansible, "-i", inventaire_fichier, str(PLAYBOOKS / playbook)]
    if variables:
        commande += ["-e", json.dumps(variables)]
    print(f"\n--- {playbook} ---", flush=True)
    code: int = lancer(commande, env=env).returncode
    return code


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("cible", choices=sorted(CIBLES))
    parseur.add_argument("--garder", action="store_true", help="ne pas détruire à la fin")
    parseur.add_argument(
        "--enregistrer",
        metavar="FICHIER",
        help=(
            "faire passer les modules par `feint proxy` et écrire la transcription "
            "ici. Ce que l'API répond devient une mesure relisible, là où une "
            "assertion ne rend qu'un booléen. Cible `reel` seulement."
        ),
    )
    arguments = parseur.parse_args(argv[1:])
    cible = CIBLES[arguments.cible]

    if arguments.garder and not cible["emulateur"]:
        raise ExempleError(
            "`--garder` contre le cloud réel laisse des ressources facturées debout. "
            "Relancer sans l'option, ou détruire à la main avec `terraform -chdir="
            "examples/stack destroy` puis `python scripts/residue.py verify`."
        )

    run_id = f"{int(time.time()) % 100000}{secrets.token_hex(2)}"
    # Sur l'émulateur il n'y a rien à vérifier, et le dire vaut mieux que
    # d'écrire « aucun » sur un contrôle qui n'a pas eu lieu.
    verdict_residu = (
        "sans objet (émulateur)" if CIBLES[arguments.cible]["emulateur"] else "non vérifié"
    )
    # Déclaré avant tout branchement : le `finally` y touche, et un `finally`
    # qui lève sur un nom inconnu masque l'erreur qu'il devait laisser passer.
    proxy: subprocess.Popen[str] | None = None
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
            # Deux questions, et la première ne répond pas à la seconde : un
            # émulateur vide peut très bien ne pas servir le mode demandé.
            refuser_un_mode_incompatible(cible, ADRESSE)
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
        # **Enregistrer ce que l'API répond, et pas seulement si l'assertion
        # passe.** Une assertion rend un booléen ; quand elle échoue, elle dit
        # ce qu'elle attendait, jamais ce que l'API a répondu, et un play qui
        # meurt sur une assertion emporte tout ce qui la suit. Un run réel a
        # ainsi coûté quarante-cinq ressources pour rendre zéro donnée sur la
        # question posée (#119).
        #
        # `feint proxy` s'intercale entre les modules et le cloud, et écrit
        # chaque échange : identifiants expurgés par construction, boucle locale
        # seulement. La collection honore `SCW_API_URL` de bout en bout, ce qui
        # est la règle 7 du projet et exactement ce pour quoi elle existe.
        #
        # **Terraform y passe aussi, et c'est mesuré plutôt que supposé.** Le
        # bloc `provider` de la stack laisse `api_url` à `null` sur la cible
        # réelle, donc le fournisseur lit `SCW_API_URL` comme les modules. La
        # transcription d'un run porte trente-deux opérations de création et de
        # suppression, qu'aucun module de cette collection n'émet.
        #
        # C'est un gain, pas un effet de bord : la transcription montre alors ce
        # que l'API a répondu **à la création** autant qu'à la relecture, et
        # c'est justement la comparaison qui manquait. Le premier commentaire
        # écrit ici affirmait l'inverse ; la transcription l'a démenti.
        if arguments.enregistrer:
            proxy = demarrer_proxy(arguments.enregistrer)
            env["SCW_API_URL"] = f"http://{PROXY}"
            print(
                f"les modules passent par le proxy {PROXY}, transcription : {arguments.enregistrer}"
            )
        print("cible : le compte Scaleway réel. Prise de la référence de résidu.")
        residu = [sys.executable, str(ROOT / "scripts" / "residue.py"), "capture"]
        if lancer(residu).returncode != 0:
            raise ExempleError("la référence de résidu n'a pas pu être prise")

    # Le journal d'exécution. Il s'accumule sur tous les playbooks, donc il
    # part d'une page blanche : un journal de la veille ferait passer un module
    # non joué pour un module éprouvé, et c'est précisément le mensonge que
    # l'artefact existe pour empêcher.
    journal = TRAVAIL / f"journal-{run_id}.json"
    journal.unlink(missing_ok=True)
    env["ANSIBLE_CALLBACK_PLUGINS"] = str(RAPPELS)
    env["ANSIBLE_CALLBACKS_ENABLED"] = "journal"
    env["EXEMPLE_JOURNAL"] = str(journal)

    env["ANSIBLE_COLLECTIONS_PATH"] = str(ROOT)
    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    env["ANSIBLE_PRIVATE_KEY_FILE"] = str(CLE)
    env["ANSIBLE_LOCALHOST_WARNING"] = "False"

    # **Le verrou avant le `try`, et son retrait dans le `finally`.**
    # Il refuse un second run tant qu'une plateforme est debout : deux
    # exercices concurrents se détruiraient mutuellement par leurs `finally`.
    verrou_plateforme.poser(run_id, arguments.cible)
    code = 0
    # **Le sort de la destruction, séparé du sort du run.** Les confondre a
    # laissé un verrou debout sur une plateforme entièrement détruite : un
    # playbook rouge suffisait, et le run suivant était refusé pour une
    # plateforme qui n'existait plus. Un verrou qui refuse ce qu'il devrait
    # laisser passer finit par se retirer à la main sans le lire, ce qui le
    # ramène à zéro.
    detruit = False
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

        refuser_une_sortie_portee(sorties)
        controler_plan_de_controle(env, sorties)
        controler_inventaire(inventaire(env), attendu)

        extra = {
            "bastion_ip": bastion_ip,
            "application_url": application_url,
            "ssh_key": str(CLE),
            # Les playbooks doivent savoir contre quoi ils tournent : une route
            # non émulée est une limite déclarée chez feint et un défaut sur le
            # cloud réel. Sans cette variable, il faudrait un `ignore_errors`,
            # qui tairait les deux.
            "cible": arguments.cible,
            # L'image d'or n'existe que sur le cloud réel : la stack la met à
            # zéro ailleurs, et le playbook saute la tâche plutôt que d'échouer.
            "image_doree": sorties.get("image_doree", {}).get("value", ""),
            # La mesure d'ordre de #119. Les trois sorties existent toujours et
            # sont vides hors du cloud réel : feint décline `CreateCertificate`,
            # avec sa raison, et le playbook saute la mesure sur une liste vide
            # plutôt que de diverger selon la cible.
            "frontend_tls": sorties.get("frontend_tls", {}).get("value", ""),
            "certificats_mesure": sorties.get("certificats_mesure", {}).get("value", []),
            "certificat_backend": sorties.get("certificat_backend", {}).get("value", ""),
        }

        # Les modules recensés parlent à l'API et n'ont besoin d'aucune
        # machine démarrée : ils tournent donc sur **toutes les cibles**, avec la même
        # stack et les mêmes assertions. C'est ce qui fait de l'exercice un test
        # différentiel de l'émulateur, et ce qui a produit feint#648, feint#650
        # et feint#651. Un écart entre les deux exécutions est un défaut de
        # l'émulateur, pas une fatalité.
        code = jouer("modules.yml", env, extra)

        if cible["ssh"]:
            controler_sortie_internet(bastion_ip)
            code = code or jouer("site.yml", env, extra) or jouer("verifier.yml", env, extra)
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
            # **Avant Terraform, pas après.** Une destruction lancée depuis
            # une définition qui n'est plus celle du déploiement échoue sur
            # un fournisseur absent, et laisse tout debout. Le dire ici est
            # bon marché ; le découvrir après a coûté un compte à nettoyer à la
            # main (ADR-015).
            dit = verrou_plateforme.derive()
            if dit:
                print(f"\n{dit}\n", file=sys.stderr, flush=True)
            echec = terraform("destroy", env, variables).returncode != 0
            if echec and not cible["emulateur"]:
                # **Une seule reprise, et seulement après un échec.** Terraform
                # détruit `scaleway_instance_private_nic` avant le serveur,
                # parce que la carte porte le `server_id`, et l'API refuse une
                # carte attachée : des ressources facturées restent debout.
                # Retirer les cartes par l'API puis relancer est la séquence qui
                # aboutit (ADR-017).
                #
                # Une boucle sans borne serait pire que l'échec qu'elle
                # rattrape : elle masquerait un blocage d'une autre nature en
                # tournant jusqu'au bout du temps.
                try:
                    retirees = deblocage.deverrouiller(f"acs-{run_id}")
                except deblocage.DeblocageError as erreur:
                    print(f"déblocage impossible : {erreur}", file=sys.stderr)
                    retirees = []
                if retirees:
                    print(
                        f"\n{len(retirees)} carte(s) réseau retirée(s) pour débloquer "
                        "la destruction :",
                        file=sys.stderr,
                    )
                    for carte in retirees:
                        print(f"  {carte.serveur_nom}  {carte.identifiant}", file=sys.stderr)
                    echec = terraform("destroy", env, variables).returncode != 0
            if echec:
                print(
                    "LA DESTRUCTION A ÉCHOUÉ. Ne pas en rester là : relancer "
                    "`terraform -chdir=examples/stack destroy`, puis vérifier.",
                    file=sys.stderr,
                )
                code = 1
            else:
                detruit = True
            if not cible["emulateur"]:
                verifier = [sys.executable, str(ROOT / "scripts" / "residue.py"), "verify"]
                if lancer(verifier).returncode != 0:
                    code = 1
                    verdict_residu = "non vérifié"
                else:
                    verdict_residu = "aucun"
        # Dans le `finally`, et après le contrôle de résidu : une exécution qui
        # a échoué au milieu a quand même couvert quelque chose, et c'est cette
        # trace-là qui manquait. Un artefact écrit seulement en cas de succès
        # aurait exactement le biais d'un test qui se saute quand il échoue.
        ecrit = ecrire_artefact(journal, arguments.cible, run_id, verdict_residu)
        if ecrit is not None:
            print(f"\ncouverture de cette exécution : {ecrit.relative_to(ROOT)}")
        # **Après la destruction, et pas avant.** Elle passe par Terraform,
        # qui parle au cloud directement, mais un playbook interrompu peut
        # encore avoir un appel en vol. Couper le proxy trop tôt perdrait la
        # fin de la transcription, c'est-à-dire précisément ce qui a échoué.
        # La décision est dans `verrou_plateforme`, avec sa raison et son test :
        # elle a déjà été prise de travers ici, en liant le verrou au sort du
        # run plutôt qu'à celui de la destruction.
        if verrou_plateforme.a_retirer(detruit, arguments.garder):
            verrou_plateforme.retirer()
        if proxy is not None:
            proxy.terminate()
            proxy.wait(timeout=10)
            print(f"transcription écrite : {arguments.enregistrer}")
        if cible["emulateur"] and not adopte and not arguments.garder:
            lancer([binaire("feint"), "stop", "--addr", ADRESSE], capture=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except ExempleError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
