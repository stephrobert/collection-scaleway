"""Éprouver le rulebook livré : un événement entre, un diagnostic sort.

Un rulebook livré que rien ne joue pourrit comme le reste, et il pourrit plus
discrètement : personne ne lance un rulebook à la main pour voir s'il marche
encore (#212).

Ce lanceur mesure la chaîne entière, telle qu'un opérateur la monterait :

    émulateur          l'API que le diagnostic va lire
         v
    ansible-rulebook   démarré sur le rulebook **de la collection installée**
         v
    webhook            un événement d'alerte, posté comme Alertmanager le ferait
         v
    fleet_report       le diagnostic, joué par la règle

**Ce qui est mesuré n'est pas que la commande sort en 0.** Un rulebook qui
écouterait sans jamais déclencher sortirait en 0 lui aussi. Ce qui compte est
que le playbook ait tourné, et qu'il ait tourné **à cause de l'événement** :
l'événement sans `status` doit, lui, ne rien déclencher.

Codes de sortie : `0` la chaîne tient, `1` le lanceur n'a pas pu la jouer,
`2` il l'a jouée et le verdict est non.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTION = ROOT / "ansible_collections" / "stephrobert" / "scaleway"
RULEBOOK = "stephrobert.scaleway.diagnose_on_alert"

#: L'émulateur de **ce lanceur**, distinct de celui de l'intégration et de
#: celui de la plateforme d'exemple : trois cibles qui tourneraient sur le même
#: port se détruiraient mutuellement, et ce n'est pas une gêne, c'est une perte
#: de travail en cours.
ADRESSE = os.environ.get("FEINT_ADDR", "127.0.0.1:4878")
ENDPOINT = f"http://{ADRESSE}"

#: Où vit la collection qui fournit les sources d'événements. Hors de
#: l'arbre du dépôt : une collection tierce posée dedans serait lue par
#: tous les contrôles d'ici.
SOURCES = ROOT / "build" / "collections"

#: Le port du webhook. Sur la boucle locale : cette écoute accepte un événement
#: de qui l'atteint, et rien ici n'a besoin qu'elle sorte de la machine.
PORT = int(os.environ.get("RULEBOOK_PORT", "5099"))


class RulebookError(Exception):
    """Le lanceur n'a pas pu jouer la chaîne."""


class Verdict(Exception):
    """La chaîne a été jouée, et elle ne tient pas."""


def binaire(nom: str) -> str:
    chemin = shutil.which(nom)
    if not chemin:
        raise RulebookError(
            f"{nom} est introuvable. Cette cible échoue plutôt que de se sauter : "
            "un contrôle qui se saute tout seul finit par ne plus jamais tourner."
        )
    return chemin


def environnement() -> dict[str, str]:
    """Les identifiants que l'émulateur accepte, lus chez lui.

    Les inventer ici créerait une seconde source de ce qu'il accepte, et les
    deux divergeraient le jour où feint changerait d'avis.
    """
    resultat = subprocess.run(
        [binaire("feint"), "env", "scaleway", "--endpoint", ENDPOINT],
        capture_output=True,
        text=True,
        check=False,
    )
    if resultat.returncode != 0:
        raise RulebookError(f"`feint env scaleway` a échoué :\n{resultat.stderr}")

    variables = dict(os.environ)
    for ligne in resultat.stdout.splitlines():
        if ligne.startswith("export "):
            nom, _, valeur = ligne.removeprefix("export ").partition("=")
            variables[nom] = valeur.strip("'\"")
    # Les deux chemins : la collection de ce dépôt, et celle qui fournit les
    # sources d'événements. Cette dernière vit sous `build/` et non dans
    # l'arbre du dépôt, parce qu'une collection tierce posée là serait lue
    # par tous les contrôles d'ici : celui qui refuse le tiret cadratin a
    # rougi sur sa documentation avant qu'elle ne soit déplacée.
    variables["ANSIBLE_COLLECTIONS_PATH"] = f"{ROOT}:{SOURCES}"
    return variables


def sources_disponibles() -> None:
    """`ansible.eda` fournit les sources, et son absence se dit tôt.

    Mesuré : les sources vivent dans le paquet `ansible-rulebook`, et aucune
    n'est adressable sans cette collection. Sans elle, le rulebook démarre,
    écoute une seconde, puis s'arrête sur `SourcePluginNotFoundException`, un
    diagnostic qu'on met du temps à relier à une collection manquante.
    """
    if (SOURCES / "ansible_collections" / "ansible" / "eda").is_dir():
        return
    raise RulebookError(
        "la collection `ansible.eda` est absente, et c'est elle qui fournit "
        "`ansible.eda.webhook`. Sans elle le rulebook démarre puis s'arrête sur "
        "`SourcePluginNotFoundException`, ce qui ne dit pas ce qui manque.\n\n"
        f"  ansible-galaxy collection install ansible.eda -p {SOURCES}\n\n"
        "Cette collection ne la déclare pas en dépendance : qui installe des "
        "modules pour éteindre un parc la nuit n'a pas à tirer un cadre "
        "événementiel qu'il n'a pas demandé."
    )


def emulateur_demarre() -> bool:
    """Démarre l'émulateur, sauf s'il en tourne déjà un ici.

    Adopter plutôt qu'écraser : le cycle de vie appartient à qui l'a démarré,
    et c'est ce qui permet à la CI de le lancer autrement.
    """
    sonde = subprocess.run(
        [binaire("feint"), "wait", "--addr", ADRESSE, "--timeout", "2s"],
        capture_output=True,
        check=False,
    )
    if sonde.returncode == 0:
        return False

    subprocess.run(
        [binaire("feint"), "start", "--addr", ADRESSE, "--detach", "--timeout", "30s"],
        capture_output=True,
        check=False,
    )
    attente = subprocess.run(
        [binaire("feint"), "wait", "--addr", ADRESSE, "--timeout", "30s"],
        capture_output=True,
        check=False,
    )
    if attente.returncode != 0:
        raise RulebookError(f"l'émulateur n'écoute pas sur {ADRESSE}")
    return True


def poster(charge: dict[str, object]) -> None:
    """Un événement, posté comme une supervision le posterait."""
    requete = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/endpoint",
        data=json.dumps(charge).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(requete, timeout=10).read()
    except urllib.error.URLError as erreur:
        raise RulebookError(f"le webhook n'a pas accepté l'événement : {erreur}") from erreur


def attendre_lecoute(processus: subprocess.Popen[str], limite: float = 60.0) -> None:
    """L'écoute est prête, ou le lanceur dit pourquoi il n'a pas pu la joindre."""
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        if processus.poll() is not None:
            raise RulebookError(
                "`ansible-rulebook` s'est arrêté avant d'écouter :\n"
                f"{(processus.stdout.read() if processus.stdout else '')[-2000:]}"
            )
        try:
            urllib.request.urlopen(
                urllib.request.Request(
                    f"http://127.0.0.1:{PORT}/endpoint",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                ),
                timeout=2,
            ).read()
            return
        except urllib.error.URLError:
            time.sleep(1)
    raise RulebookError(f"le webhook n'écoute pas sur le port {PORT} au bout de {limite:.0f} s")


def jouer() -> str:
    """Monte la chaîne, envoie un événement, et rend ce que le rulebook a dit."""
    # `-e` prend un **fichier** de variables, et `-E` les noms des variables
    # d'environnement à faire traverser. Les confondre fait écouter le rulebook
    # sur son port par défaut pendant que le lanceur frappe ailleurs, et le
    # diagnostic est alors « le webhook n'écoute pas », ce qui est vrai et
    # trompeur.
    variables = ROOT / "build" / "rulebook-vars.yml"
    variables.parent.mkdir(parents=True, exist_ok=True)
    variables.write_text(f"listen_host: 127.0.0.1\nlisten_port: {PORT}\n", encoding="utf-8")

    processus = subprocess.Popen(
        [
            binaire("ansible-rulebook"),
            "--rulebook",
            RULEBOOK,
            "--inventory",
            str(ROOT / "tests" / "integration" / "feint" / "inventaire.scaleway.yml"),
            "--vars",
            str(variables),
            "--print-events",
            "-E",
            "SCW_API_URL,SCW_ACCESS_KEY,SCW_SECRET_KEY,SCW_DEFAULT_PROJECT_ID",
        ],
        env=environnement(),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        attendre_lecoute(processus)
        # Le premier événement ne porte pas de `status` : il ne doit rien
        # déclencher, et c'est ce qui distingue « la règle a tiré » de « le
        # rulebook tire sur tout ».
        # **La source imbrique le corps posté sous `payload`.** Mesuré : poster
        # `{"payload": {...}}` donnait `event.payload.payload.status`, et la
        # règle ne tirait pas. Ce qui part ici est donc le corps qu'une
        # supervision enverrait, sans enveloppe ajoutée par nous.
        poster({"message": "rien à signaler"})
        time.sleep(3)
        poster({"status": "firing", "alertname": "InstanceDown"})
        time.sleep(25)
    finally:
        processus.terminate()
        try:
            sortie, _ = processus.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            processus.kill()
            sortie, _ = processus.communicate()
    return sortie or ""


def juger(sortie: str) -> None:
    """Ce que la chaîne doit avoir fait, et ce qu'elle ne doit pas avoir fait."""
    if "Report on a Scaleway fleet" not in sortie:
        raise Verdict(
            "l'alerte n'a pas déclenché le diagnostic. Un rulebook qui écoute "
            "sans jamais déclencher sort en 0 lui aussi, et c'est pourquoi le "
            f"verdict porte sur ce qui a tourné.\n{sortie[-3000:]}"
        )
    if "nothing was read" not in sortie:
        raise Verdict(
            "l'événement sans `status` n'a pas été nommé. Une règle qui "
            "matcherait en silence une charge utile que personne n'a vérifiée "
            f"est la façon dont un rulebook se met à tirer sur autre chose.\n{sortie[-3000:]}"
        )
    print("  une alerte entre, un diagnostic sort ; un événement muet ne déclenche rien")


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description="Éprouver le rulebook livré.")
    parseur.add_argument(
        "--garder", action="store_true", help="laisser l'émulateur en écoute à la fin"
    )
    arguments = parseur.parse_args(argv)

    a_demarre = False
    try:
        sources_disponibles()
        a_demarre = emulateur_demarre()
        print(f"rulebook {RULEBOOK}, webhook sur 127.0.0.1:{PORT}")
        juger(jouer())
    except Verdict as erreur:
        print(f"\nla chaîne ne tient pas : {erreur}", file=sys.stderr)
        return 2
    except RulebookError as erreur:
        print(f"\nla chaîne n'a pas pu être jouée : {erreur}", file=sys.stderr)
        return 1
    finally:
        if a_demarre and not arguments.garder:
            subprocess.run(
                [binaire("feint"), "stop", "--addr", ADRESSE], capture_output=True, check=False
            )

    print("\ndétecter puis diagnostiquer : la chaîne tient.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
