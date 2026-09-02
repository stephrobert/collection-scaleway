"""Échoue si un artefact versionné n'est plus celui que le générateur produit.

Le principe : régénérer, puis exiger que git ne voie aucune différence. Un
fichier généré commité qui diffère de ce que le générateur produit est un
mensonge silencieux, et il se découvre au pire moment.

**`git diff --exit-code` ne suffit pas.** Il ne voit pas un fichier *non
suivi* : un module tout neuf, produit et jamais commité, laisserait la
commande verte. Ce script regarde les deux : ce qui a changé, et ce qui est
apparu.

    python scripts/check_generated.py tests/fixtures ansible_collections
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Chemins dont le contenu est produit par le générateur.
DEFAULT_PATHS: tuple[str, ...] = ("tests/fixtures", "ansible_collections")

#: Les fichiers volontairement ni suivis par git, ni ignorés.
#:
#: `CLAUDE.md` porte les instructions de travail de ce dépôt, `BRIEF.md` l'état
#: d'avancement tenu à la main. Le mainteneur a tranché : ils ne sont pas
#: versionnés, et ils ne sont pas non plus listés dans `.gitignore`. Cette
#: seconde moitié n'est pas un oubli, et elle a un effet
#: mesurable : un fichier ignoré disparaît de `git status`, donc personne ne
#: voit s'il change ou s'il manque, alors qu'un fichier simplement non suivi
#: reste sous les yeux à chaque commande.
#:
#: L'exemption est donc **étroite à dessein** : seule la forme « non suivi »
#: (`??`) est acceptée. Si l'un d'eux réapparaissait dans l'index, `A ` ou
#: `M `, ce script échouerait comme avant, ce qui est bien ce qu'on veut :
#: la décision est de ne pas les commiter, pas de ne plus les regarder.
UNTRACKED_BY_DESIGN: frozenset[str] = frozenset({"CLAUDE.md", "BRIEF.md"})


def exempted(line: str) -> bool:
    """Vrai pour la seule forme exemptée : un non-suivi nommé dans la table."""
    status, _, path = line.partition(" ")
    return status == "??" and path.strip() in UNTRACKED_BY_DESIGN


def modified(paths: tuple[str, ...]) -> str:
    """Ce que git voit de différent, fichiers non suivis compris."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    lignes = [
        ligne for ligne in result.stdout.splitlines() if ligne.strip() and not exempted(ligne)
    ]
    return "\n".join(lignes)


def main(argv: list[str]) -> int:
    paths = tuple(argv[1:]) or DEFAULT_PATHS
    drift = modified(paths)
    if not drift:
        print(f"artefacts générés à jour : {', '.join(paths)}")
        return 0

    print("ce que git enregistre diffère de ce qui est sur le disque :", file=sys.stderr)
    print(drift, file=sys.stderr)
    print(
        "\nUn fichier généré : relire le diff, puis commiter la régénération — "
        "un golden rafraîchi sans être lu annule tout le mécanisme.\n"
        "Un artefact de build : l'ajouter au .gitignore, il n'a rien à faire ici.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
