"""Les nombres publiés dans le README, dérivés plutôt que recopiés.

Le README annonçait 366 tests unitaires et 46 mutations. Mesuré au même
instant : 420 tests et 73 mutations. Le message d'un commit annonçait 373 pour
376. Trois occurrences du même défaut, et il n'a rien d'anecdotique dans un
dépôt dont la thèse est qu'on mesure au lieu de supposer : **un nombre recopié
à la main vieillit en silence, et se lit exactement comme une mesure.**

Ce script produit le bloc entre les deux marqueurs du README depuis les
sources qui font foi. Deux modes, et la CI se sert du second :

    python scripts/readme_counters.py --write    réécrit le bloc
    python scripts/readme_counters.py --check    échoue si le bloc a vieilli

Ce qui n'est pas mesurable hors ligne n'entre pas dans le bloc. Le compte de
`ansible-test sanity` et celui des serveurs listés contre l'émulateur
demandent chacun de lancer autre chose ; les recopier ici les remettrait
exactement dans l'état qu'on corrige. Ils sont dits sans nombre, et le lecteur
qui veut le nombre lance la commande nommée.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
RAPPORTS = ROOT / "build" / "reports"
MUTATIONS = ROOT / "tests" / "falsify" / "specs.json"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

DEBUT = "<!-- compteurs:début, produits par scripts/readme_counters.py -->"
FIN = "<!-- compteurs:fin -->"


class CompteursError(RuntimeError):
    """Une source manque, et il vaut mieux le dire que publier un nombre faux."""


def _rapport(produit: str, version: str) -> dict[str, Any]:
    chemin = RAPPORTS / f"{produit}.{version}.json"
    if not chemin.is_file():
        raise CompteursError(
            f"{chemin.relative_to(ROOT)} manque : lancer `mise run report` avant. "
            "Un compteur sans sa source n'est pas un compteur."
        )
    donnees: dict[str, Any] = json.loads(chemin.read_text(encoding="utf-8"))
    return donnees


def _modules_ecrits() -> tuple[int, int]:
    """Modules écrits et modules du plan, lus dans le compte rendu de génération."""
    chemin = RAPPORTS / "instance.v1.generation.md"
    if not chemin.is_file():
        raise CompteursError(
            f"{chemin.relative_to(ROOT)} manque : lancer `mise run generate` avant."
        )
    texte = chemin.read_text(encoding="utf-8")
    for ligne in texte.splitlines():
        if ligne.startswith("Modules écrits :"):
            ecrits = int(ligne.split("**")[1])
            ecartes = int(ligne.split("**")[3])
            return ecrits, ecrits + ecartes
    raise CompteursError("le compte rendu de génération ne porte pas sa ligne de modules")


def _tests() -> int:
    """Le nombre de tests que pytest collecte, demandé à pytest."""
    resultat = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", str(ROOT / "tests")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    # `N tests collected`, la ligne que pytest écrit lui-même. La forme courte
    # `-q` rend un compte par fichier qu'il faudrait sommer, et une somme est
    # une occasion de se tromper là où pytest a déjà fait le calcul.
    for ligne in reversed(resultat.stdout.splitlines()):
        mots = ligne.split()
        if len(mots) >= 3 and mots[1] in {"test", "tests"} and mots[2] == "collected":
            return int(mots[0])
    raise CompteursError(
        f"pytest n'a pas dit combien de tests il collecte :\n{resultat.stdout[-500:]}"
    )


def _mutations() -> int:
    donnees = json.loads(MUTATIONS.read_text(encoding="utf-8"))
    return len(donnees["mutations"])


def _jobs() -> tuple[int, tuple[str, ...]]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    noms = tuple(str(details.get("name", cle)).split(" (")[0] for cle, details in jobs.items())
    return len(jobs), noms


def _pourcent(valeur: float) -> str:
    """Avec la virgule décimale, le dépôt écrivant en français."""
    return f"{valeur * 100:.1f} %".replace(".", ",", 1)


def _en_lettres(nombre: int) -> str:
    lettres = {1: "un", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq", 6: "six", 7: "sept"}
    return lettres.get(nombre, str(nombre))


def bloc() -> str:
    """Le bloc, tel qu'il doit être aujourd'hui."""
    rapport = _rapport("instance", "v1")
    totaux = rapport["totals"]
    genres = totaux["by_kind"]
    modes = totaux["by_mode"]
    couverture = rapport["day2_automation_coverage"]
    ecrits, plan = _modules_ecrits()
    nb_jobs, noms_jobs = _jobs()

    return "\n".join(
        [
            "```text",
            f"instance v1 : {totaux['operations']} opérations découvertes",
            f"  INFO {genres['info']} · ACTION {genres['action']} · "
            f"MANAGE {genres['manage']} · WORKFLOW {genres['workflow']} · "
            f"LIFECYCLE {genres['lifecycle']} · IGNORE {genres['ignore']} · "
            f"UNKNOWN {genres['unknown']}",
            f"  Day-2 {totaux['day2_candidates']} · AUTO {modes['auto']} · "
            f"MANUAL {modes['manual']} · classées pour génération automatique "
            f"{_pourcent(couverture)} ({modes['auto'] + modes['override']}"
            f"/{totaux['day2_candidates']})",
            "",
            f"collection local.scaleway : {ecrits} modules produits sur {plan} au plan",
            "  instance_server_info    lire une Instance, ou lister une zone entière",
            "  instance_server_action  allumer, arrêter, redémarrer, figer",
            "  scaleway (inventaire)   instance, elastic_metal, apple_silicon",
            f"  {_tests()} tests unitaires · {_mutations()} mutations prouvées par /falsify",
            f"  CI : {_en_lettres(nb_jobs)} jobs, {' · '.join(noms_jobs)}",
            "  ansible-test sanity, playbooks et inventaire contre l'émulateur :",
            "  comptes rendus par `mise run sanity` et `mise run integration`",
            "```",
        ]
    )


def _remplace(texte: str, nouveau: str) -> str:
    if DEBUT not in texte or FIN not in texte:
        raise CompteursError(
            f"les marqueurs manquent dans {README.name}. Encadrer le bloc par :\n"
            f"{DEBUT}\n...\n{FIN}"
        )
    avant = texte[: texte.index(DEBUT) + len(DEBUT)]
    apres = texte[texte.index(FIN) :]
    return f"{avant}\n{nouveau}\n{apres}"


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    groupe = parseur.add_mutually_exclusive_group(required=True)
    groupe.add_argument("--write", action="store_true", help="réécrire le bloc")
    groupe.add_argument("--check", action="store_true", help="échouer s'il a vieilli")
    arguments = parseur.parse_args(argv[1:])

    texte = README.read_text(encoding="utf-8")
    attendu = _remplace(texte, bloc())

    if arguments.write:
        if attendu == texte:
            print("compteurs du README : déjà à jour")
            return 0
        README.write_text(attendu, encoding="utf-8")
        print("compteurs du README : réécrits")
        return 0

    if attendu != texte:
        print(
            "les compteurs du README ne correspondent plus à ce qui est mesuré.\n"
            "Lancer `mise run readme` puis relire le diff : un nombre recopié à la\n"
            "main vieillit en silence, et se lit exactement comme une mesure.",
            file=sys.stderr,
        )
        return 1
    print("compteurs du README : conformes à la mesure")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except CompteursError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
