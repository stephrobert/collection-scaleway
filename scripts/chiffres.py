"""Aucun compteur vivant dans un document écrit à la main.

Le README dérive ses nombres et la CI refuse un README périmé. **Cette règle ne
valait que pour lui**, et un audit de la 0.3.0 a trouvé quatre documents qui
publiaient des chiffres faux :

| fichier | disait | la mesure disait |
|---|---|---|
| `docs/architecture/generator.md` | 41 Day-2, 40 AUTO, 97,6 %, 14 IGNORE | 40, 39, 97,5 %, 15 |
| `docs/architecture/runtime.md` | modules joués sur **46** | 50 |
| `docs/best-practices.md` | 575 tests, 149 mutations | 595, 158 |

Le projet dit « ne pas mentir, mesurer ». Une règle qui ne vaut que pour un
fichier ne vaut pas.

**Ce que ce contrôle cherche, et ce qu'il ne cherche pas.** Il ne juge pas si un
nombre est juste : il ne le saurait pas sans le recalculer, et ce serait alors
un second calcul à maintenir. Il cherche les **tournures** par lesquelles ce
dépôt publie une mesure — « N tests unitaires », « N modules », « N opérations
Day-2 », « couverture N % ». Toute occurrence hors d'un bloc dérivé est refusée,
avec le nom du bloc où la mettre.

Un nombre qui n'est pas une mesure passe donc sans encombre : « les trois
règles », « Python 3.12 », « RFC 2606 ». C'est voulu, et c'est la différence
entre un contrôle et une gêne.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Les fichiers suivis où un compteur périmé se lit comme une mesure.
#:
#: `CLAUDE.md` en est exclu : il n'est pas versionné dans ce dépôt. Les
#: changelogs non plus : un changelog décrit ce qu'une version passée portait,
#: et ses nombres doivent **rester** ceux d'alors.
SURVEILLES: tuple[Path, ...] = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "RELEASING.md",
    ROOT / "SECURITY.md",
    ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "README.md",
    *sorted((ROOT / "docs").rglob("*.md")),
)

#: Les tournures par lesquelles ce dépôt publie une mesure, et le bloc dérivé
#: qui doit la porter. Chacune vient d'une divergence réellement trouvée.
TOURNURES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b\d+\s+unit tests\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s+mutations\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s+modules? (written|played|called|generated)\b", re.I), "compteurs"),
    (re.compile(r"\bout of \d+\s+(modules|operations)\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s+Day-2\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s+(AUTO|MANUAL|IGNORE|LIFECYCLE|UNKNOWN)\b"), "compteurs"),
    (re.compile(r"\bcoverage\s+\d+[.,]\d+\s*%"), "compteurs"),
    (re.compile(r"\b\d+\s+published pages\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s*/\s*\d+\s+(options|returned keys|examples)\b", re.I), "compteurs"),
)

#: Un bloc dérivé, quel que soit son nom.
#:
#: Le tiret est dans la classe parce qu'un nom de bloc en porte :
#: `runtime-etat`, `ecart-cibles`. Sans lui, ces trois blocs existaient et le
#: contrôle les signalait quand même, ce qui aurait fait chercher un défaut là
#: où il n'y en avait pas.
DEBUT = re.compile(r"<!-- compteurs:(?:[a-z-]+:)?début")
FIN = re.compile(r"<!-- compteurs:(?:[a-z-]+:)?fin")


@dataclass(frozen=True)
class Ecart:
    """Un compteur publié hors d'un bloc dérivé."""

    fichier: Path
    ligne: int
    texte: str
    bloc: str


def _hors_des_blocs(texte: str) -> list[tuple[int, str]]:
    """Les lignes du fichier qui ne sont dans aucun bloc dérivé."""
    dedans = False
    dehors: list[tuple[int, str]] = []
    for rang, ligne in enumerate(texte.splitlines(), start=1):
        if DEBUT.search(ligne):
            dedans = True
            continue
        if FIN.search(ligne):
            dedans = False
            continue
        if not dedans:
            dehors.append((rang, ligne))
    return dehors


def examiner(chemin: Path) -> list[Ecart]:
    """Les compteurs publiés hors bloc dans ce fichier."""
    if not chemin.is_file():
        return []
    ecarts: list[Ecart] = []
    for rang, ligne in _hors_des_blocs(chemin.read_text(encoding="utf-8")):
        for motif, bloc in TOURNURES:
            trouve = motif.search(ligne)
            if trouve:
                ecarts.append(Ecart(chemin, rang, trouve.group(0), bloc))
    return ecarts


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--check", action="store_true", help="échouer sur un compteur hors bloc")
    parseur.parse_args(argv[1:])

    ecarts = [ecart for chemin in SURVEILLES for ecart in examiner(chemin)]
    if not ecarts:
        print(f"{len(SURVEILLES)} fichier(s) examiné(s) : aucun compteur hors d'un bloc dérivé.")
        return 0

    print(f"{len(ecarts)} compteur(s) publié(s) hors d'un bloc dérivé :\n", file=sys.stderr)
    for ecart in ecarts:
        chemin = ecart.fichier.relative_to(ROOT)
        print(f"  {chemin}:{ecart.ligne}  « {ecart.texte} »", file=sys.stderr)
    print(
        "\nUn nombre écrit à la main vieillit en silence et se lit exactement\n"
        "comme une mesure. Encadrer le passage par un bloc dérivé :\n"
        "    <!-- compteurs:<nom>:début, produits par scripts/readme_counters.py -->\n"
        "    ...\n"
        "    <!-- compteurs:<nom>:fin -->\n"
        "puis produire ce bloc dans `scripts/readme_counters.py`.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
