"""Prouve qu'un test échoue quand la garde qu'il mesure disparaît.

Un test qui passe ne prouve rien à lui seul : il peut affirmer quelque chose
qui était déjà vrai. Ce harnais neutralise une garde dans une **copie du dépôt
hors de l'arbre de travail**, lance le seul test censé la mesurer, et exige
qu'il rougisse.

Les mutations sont déclarées dans `tests/falsify/specs.json`, à côté de la
garde qu'elles neutralisent, plutôt qu'écrites à la main à chaque fois : une
falsification jouée une fois puis oubliée est une phrase sur le passé.

    python scripts/falsify.py              # rejoue toutes les mutations
    python scripts/falsify.py no_log       # une seule, par son nom
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "tests" / "falsify" / "specs.json"

#: Ce qui n'a pas à être copié pour lancer les tests.
IGNORED = shutil.ignore_patterns(
    ".git",
    ".venv",
    "build",
    "__pycache__",
    "*.egg-info",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
)


@dataclass(frozen=True)
class Mutation:
    """Une garde, la façon de la neutraliser, et le test qui doit le voir."""

    name: str
    file: str
    find: str
    replace: str
    test: str
    why: str


@dataclass(frozen=True)
class Verdict:
    """Ce que la mutation a produit. Une seule valeur est une preuve."""

    mutation: Mutation
    outcome: str
    detail: str = ""

    @property
    def proves(self) -> bool:
        return self.outcome == "le test a mordu"


def load_mutations() -> list[Mutation]:
    document = json.loads(SPECS.read_text(encoding="utf-8"))
    return [Mutation(**entry) for entry in document["mutations"]]


def run_pytest(cwd: Path, target: str) -> subprocess.CompletedProcess[str]:
    # PYTHONDONTWRITEBYTECODE : voir `falsify()`, le harnais a déjà menti une
    # fois à cause du cache de bytecode.
    return subprocess.run(
        [sys.executable, "-m", "pytest", target, "-x", "-q", "--no-header"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def falsify(mutation: Mutation, source: Path, parent: Path) -> Verdict:
    """Joue une mutation dans une copie neuve du dépôt.

    Une copie par mutation, et pas une copie mutée puis restaurée : le harnais
    a rapporté deux gardes « non prouvées » qui l'étaient, parce que deux
    mutations d'un même fichier ajoutaient exactement dix caractères chacune.
    Après restauration, le source retrouvait la taille et la seconde de mtime
    inscrites dans le `.pyc` de la mutation précédente, que Python réutilisait
    alors : le test mesurait le fichier d'avant.

    La sortie fausse était parfaitement plausible, c'est ce qui la rend
    dangereuse : elle disait « le test est resté vert », exactement ce
    qu'afficherait une garde réellement non mesurée.
    """
    workdir = parent / f"repo-{mutation.name}"
    shutil.copytree(source, workdir, ignore=IGNORED)

    target = workdir / mutation.file
    original = target.read_text(encoding="utf-8")

    occurrences = original.count(mutation.find)
    if occurrences == 0:
        # Le fragment n'est plus dans le fichier : rien n'a été mesuré. Ce
        # verdict est un échec, pas une absence de résultat.
        return Verdict(mutation, "la mutation ne s'applique pas", mutation.find[:60])

    if occurrences > 1:
        # **Un motif ambigu mute le premier endroit, pas celui qu'on visait.**
        # Le cas est arrivé : `if module.check_mode:` existait dans le module
        # d'action, puis un module de gestion a été écrit avant lui dans le même
        # fichier. La mutation a muté le second, le test du premier est resté
        # vert, et le harnais a rapporté « garde non prouvée » sur une garde qui
        # l'était. Une mutation qui ne sait pas où elle frappe ne prouve rien.
        return Verdict(
            mutation,
            f"motif ambigu, {occurrences} occurrences",
            mutation.find[:60],
        )

    target.write_text(original.replace(mutation.find, mutation.replace, 1), encoding="utf-8")
    result = run_pytest(workdir, mutation.test)

    if "ImportError" in result.stdout or "SyntaxError" in result.stdout:
        return Verdict(mutation, "le module ne s'importe plus", "mutation destructive")
    if result.returncode == 0:
        return Verdict(mutation, "le test est resté vert", "garde non prouvée")
    return Verdict(mutation, "le test a mordu")


def main(argv: list[str]) -> int:
    wanted = set(argv[1:])
    mutations = [m for m in load_mutations() if not wanted or m.name in wanted]
    if not mutations:
        print("aucune mutation à jouer", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="falsify-") as temporary:
        parent = Path(temporary)
        reference = parent / "repo-baseline"
        shutil.copytree(ROOT, reference, ignore=IGNORED)

        # Exiger le vert d'abord : une copie déjà rouge rendrait tous les
        # verdicts suivants ininterprétables.
        baseline = run_pytest(reference, "tests/unit")
        if baseline.returncode != 0:
            print("la copie est rouge avant toute mutation, rien n'est mesurable")
            print(baseline.stdout[-2000:])
            return 1

        verdicts = [falsify(mutation, ROOT, parent) for mutation in mutations]

    largeur = max(len(verdict.mutation.name) for verdict in verdicts)
    print()
    for verdict in verdicts:
        marque = "ok  " if verdict.proves else "ECHEC"
        detail = f"  ({verdict.detail})" if verdict.detail else ""
        print(f"{marque} {verdict.mutation.name:<{largeur}}  {verdict.outcome}{detail}")

    prouvees = sum(1 for verdict in verdicts if verdict.proves)
    print(f"\n{prouvees}/{len(verdicts)} garde(s) prouvée(s)")
    return 0 if prouvees == len(verdicts) else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
