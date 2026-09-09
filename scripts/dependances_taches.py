"""Une tâche qui lit les modules générés déclare qu'elle attend la génération.

`mise` lance les tâches d'une porte en parallèle. Une tâche qui lit
`plugins/modules/*.py` sans déclarer `generate` peut donc lire pendant que
`generate` réécrit ces fichiers, et tomber sur un fichier à moitié écrit.

Ce n'est pas une hypothèse. `admission` appelait `docs_quality.mesurer()` sans
la dépendance, et `main` est sorti rouge sur deux défauts documentaires que le
dépôt ne porte pas, après une pull request verte : la signature d'une course.
C'était déjà l'omission de #138, où `readme` n'avait pas la dépendance que
`readme:check` avait. Deux fois suffisent.

## Ce qu'il voit

Un script lit les modules générés s'il construit le chemin lui-même, ou s'il
importe un script qui le fait. La chaîne s'arrête là : un import à deux niveaux
lui échapperait.

## Ce qu'il ne voit pas, et qui reste à la relecture

Une lecture par un chemin calculé ailleurs, ou par un sous-processus. Le dire
ici vaut mieux que de laisser croire à une couverture complète, et c'est la
même honnêteté que `outillage_ci` s'impose sur sa liste d'outils.

    python scripts/dependances_taches.py

Codes de sortie : `0` conforme, `1` erreur, `2` une tâche lit sans attendre.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISE = ROOT / "mise.toml"
SCRIPTS = ROOT / "scripts"

#: Ce que `generate` écrit, et que personne ne doit lire pendant qu'il écrit.
PRODUCTEUR = "generate"

#: La construction du chemin des modules générés, telle que les scripts
#: l'écrivent. Un chemin bâti autrement échapperait au contrôle, et la
#: docstring le dit plutôt que de le taire.
_LIT_LES_MODULES = re.compile(r'/\s*"modules"')

_TACHE = re.compile(r"^\[tasks\.", re.MULTILINE)
_LANCE = re.compile(r'run = "python (scripts/[\w.]+)')


class DependancesError(RuntimeError):
    """Le fichier de tâches n'a pas pu être lu."""


def taches(texte: str) -> dict[str, tuple[str | None, list[str]]]:
    """Nom de tâche -> (script lancé, dépendances déclarées)."""
    trouvees: dict[str, tuple[str | None, list[str]]] = {}
    for bloc in _TACHE.split(texte)[1:]:
        nom = bloc.split("]", 1)[0].strip('"')
        corps = bloc.split("]", 1)[1]
        avant = corps.split("run =", 1)[0]
        lance = _LANCE.search(corps)
        depends = (
            re.findall(r'"([\w:.-]+)"', avant.split("depends", 1)[1]) if "depends" in avant else []
        )
        trouvees[nom] = (lance.group(1) if lance else None, depends)
    return trouvees


def lit_les_modules(script: Path, vus: frozenset[str] = frozenset()) -> bool:
    """Vrai quand ce script lit les modules générés, directement ou par un import.

    La chaîne d'imports s'arrête à un niveau : au-delà, le contrôle mentirait
    sur ce qu'il sait, et la docstring du module dit cette limite.
    """
    if not script.is_file() or script.name in vus:
        return False
    texte = script.read_text(encoding="utf-8")
    if _LIT_LES_MODULES.search(texte):
        return True
    if vus:
        return False
    importes = set(re.findall(r"^\s*(?:import|from) (\w+)", texte, re.MULTILINE))
    return any(
        lit_les_modules(SCRIPTS / f"{nom}.py", frozenset({script.name}))
        for nom in importes
        if (SCRIPTS / f"{nom}.py").is_file()
    )


def attend_la_generation(nom: str, table: dict[str, tuple[str | None, list[str]]]) -> bool:
    """La tâche déclare-t-elle `generate`, directement ou par une dépendance ?"""
    vus: set[str] = set()
    a_voir = [nom]
    while a_voir:
        courant = a_voir.pop()
        if courant in vus:
            continue
        vus.add(courant)
        if courant == PRODUCTEUR:
            return True
        a_voir.extend(table.get(courant, (None, []))[1])
    return False


def refus(texte: str) -> list[str]:
    """Les tâches de `check` qui lisent sans attendre."""
    table = taches(texte)
    if PRODUCTEUR not in table:
        raise DependancesError(
            f"`{PRODUCTEUR}` n'est pas une tâche de mise.toml : le contrôle ne saurait "
            "pas ce qu'il surveille."
        )
    portes = table.get("check", (None, []))[1]
    if not portes:
        raise DependancesError(
            "`check` ne déclare aucune dépendance : un contrôle qui ne lit rien rend "
            "vert sur n'importe quoi."
        )

    manques = []
    for nom in portes:
        script, _ = table.get(nom, (None, []))
        if script is None or not lit_les_modules(ROOT / script):
            continue
        if not attend_la_generation(nom, table):
            manques.append(
                f"`{nom}` lance {script}, qui lit les modules générés, et ne déclare "
                f"pas `{PRODUCTEUR}` : `mise` peut le lancer pendant que la génération "
                "réécrit ces fichiers"
            )
    return manques


def main() -> int:
    try:
        manques = refus(MISE.read_text(encoding="utf-8"))
    except (OSError, DependancesError) as erreur:
        print(str(erreur), file=sys.stderr)
        return 1

    if manques:
        print(
            f"{len(manques)} tâche(s) qui lisent les modules générés sans attendre :\n"
            + "\n".join(f"  {ligne}" for ligne in manques)
            + f'\n\nAjouter `depends = ["{PRODUCTEUR}"]`. Une lecture concurrente tombe '
            "sur\nun fichier à moitié écrit, et le verdict invente des défauts que le\n"
            "dépôt ne porte pas.",
            file=sys.stderr,
        )
        return 2

    print("toute tâche de `check` qui lit les modules générés attend la génération.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
