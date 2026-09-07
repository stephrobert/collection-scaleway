"""Une seule source pour les nombres que ce dépôt publie.

**Le README dérive ses compteurs, et le reste du dépôt ne le faisait pas.** Un
audit de la 0.3.0 a trouvé quatre divergences, toutes dans des documents écrits
à la main :

Le relevé de ces écarts, avec ses nombres et sa date, vit dans ADR-007. Il
était recopié ici et dans `scripts/chiffres.py`, et les deux copies ne disaient
déjà plus la même chose.

Le projet dit « ne pas mentir, mesurer ». La règle doit valoir partout, ou elle
ne vaut nulle part.

Ce script produit `build/evidence.json`, que `readme_counters.py` consomme pour
écrire chaque bloc dérivé. Un nombre publié vient d'ici, ou il n'est pas publié.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import docs_quality

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

RAPPORTS = ROOT / "build" / "reports"
MUTATIONS = ROOT / "tests" / "falsify" / "specs.json"
SORTIE = ROOT / "build" / "evidence.json"


class EvidenceError(RuntimeError):
    """Une source manque, et un nombre faux serait pire qu'une erreur."""


def _rapport(produit: str) -> dict[str, Any]:
    chemin = RAPPORTS / f"{produit}.json"
    if not chemin.is_file():
        raise EvidenceError(
            f"{chemin.relative_to(ROOT)} manque : lancer `mise run report` avant. "
            "Un compteur sans sa source n'est pas un compteur."
        )
    contenu: dict[str, Any] = json.loads(chemin.read_text(encoding="utf-8"))
    return contenu


def _tests() -> int:
    """Le nombre de tests que pytest collecte, demandé à pytest."""
    resultat = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", str(ROOT / "tests")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # `N tests collected`, la ligne que pytest écrit lui-même. La forme courte
    # `-q` rend un compte par fichier qu'il faudrait sommer, et une somme est
    # une occasion de se tromper là où pytest a déjà fait le calcul. Écrit ici
    # après l'avoir essayée : `-q` ne porte pas cette ligne.
    for ligne in reversed(resultat.stdout.splitlines()):
        mots = ligne.split()
        if len(mots) >= 3 and mots[1] in {"test", "tests"} and mots[2] == "collected":
            return int(mots[0])
    raise EvidenceError(
        "pytest n'a pas dit combien de tests il collecte. Un compte deviné "
        "serait pire que pas de compte."
    )


def _mutations() -> int:
    return len(json.loads(MUTATIONS.read_text(encoding="utf-8"))["mutations"])


def rassembler() -> dict[str, Any]:
    """Tout ce que ce dépôt publie comme nombre, mesuré à l'instant."""
    instance = _rapport("instance.v1")
    totaux = instance["totals"]
    qualite, _ = docs_quality.mesurer()

    return {
        "_comment": (
            "Produit par scripts/evidence.py. Un nombre publié vient d'ici, "
            "ou il n'est pas publié. Ne pas éditer à la main."
        ),
        "instance": {
            "operations": totaux["operations"],
            "day2": totaux["day2_candidates"],
            "auto": totaux["by_mode"]["auto"],
            "override": totaux["by_mode"]["override"],
            "manual": totaux["by_mode"]["manual"],
            "kinds": totaux["by_kind"],
            "coverage": instance["day2_automation_coverage"],
        },
        "tests": _tests(),
        "mutations": _mutations(),
        "documentation": {
            "pages": qualite.modules,
            "options": [qualite.options_decrites, qualite.options],
            "retours": [qualite.retours_decrits, qualite.retours],
            "champs": [qualite.champs_decrits, qualite.champs],
            "exemples": [qualite.exemples_copiables, qualite.exemples],
        },
    }


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--write", action="store_true", help="écrire build/evidence.json")
    arguments = parseur.parse_args(argv[1:])

    try:
        donnees = rassembler()
    except (EvidenceError, docs_quality.QualiteError) as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return 1

    rendu = json.dumps(donnees, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if arguments.write:
        SORTIE.parent.mkdir(parents=True, exist_ok=True)
        SORTIE.write_text(rendu, encoding="utf-8")
        print(f"écrit dans {SORTIE.relative_to(ROOT)}")
    else:
        print(rendu, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
