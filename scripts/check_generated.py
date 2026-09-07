"""Échoue si un artefact versionné n'est plus celui que le générateur produit.

Le principe : régénérer, puis exiger que git ne voie aucune différence. Un
fichier généré commité qui diffère de ce que le générateur produit est un
mensonge silencieux, et il se découvre au pire moment.

**`git diff --exit-code` ne suffit pas.** Il ne voit pas un fichier *non
suivi* : un module tout neuf, produit et jamais commité, laisserait la
commande verte. Ce script regarde les deux : ce qui a changé, et ce qui est
apparu.

**Ce qui est déjà indexé n'est pas une dérive.** Un fichier régénéré puis
`git add`é a exactement le contenu que le générateur produit : c'est la
situation que ce contrôle demande d'atteindre, pas celle qu'il doit refuser.
Confondre les deux rendait le crochet de pré-commit auto-contradictoire, en
refusant le commit qui porte la régénération qu'il réclamait. On regarde donc
la **deuxième** colonne de `git status --porcelain`, celle de la copie de
travail, plus les fichiers non suivis.

    python scripts/check_generated.py tests/fixtures ansible_collections
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Chemins dont le contenu est produit par le générateur.
DEFAULT_PATHS: tuple[str, ...] = ("tests/fixtures", "ansible_collections")


def derives(lignes: str) -> list[str]:
    """Les lignes de `git status --porcelain` qui disent une vraie dérive.

    Le format donne deux colonnes : l'index, puis la copie de travail. Seule la
    seconde décide. Un fichier indexé et identique au disque porte `M ` ; il a
    le contenu que le générateur produit, et le retenir ferait échouer le commit
    qui le porte. Un fichier non suivi porte `??`, donc `?` en seconde colonne,
    et reste une dérive : un module produit et jamais commité est exactement le
    cas que `git diff --exit-code` ne voit pas.
    """
    return [ligne for ligne in lignes.splitlines() if ligne and ligne[1] != " "]


def modified(paths: tuple[str, ...]) -> str:
    """Ce que git voit de différent, fichiers non suivis compris."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return "\n".join(derives(result.stdout))


def main(argv: list[str]) -> int:
    paths = tuple(argv[1:]) or DEFAULT_PATHS
    drift = modified(paths)
    if not drift:
        print(f"artefacts générés à jour : {', '.join(paths)}")
        return 0

    print("ce que git enregistre diffère de ce qui est sur le disque :", file=sys.stderr)
    print(drift, file=sys.stderr)
    print(
        "\nUn fichier généré : relire le diff, puis commiter la régénération, "
        "un golden rafraîchi sans être lu annule tout le mécanisme.\n"
        "Un artefact de build : l'ajouter au .gitignore, il n'a rien à faire ici.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
