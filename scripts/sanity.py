"""Lance `ansible-test sanity`, et refuse un vert qui n'a rien mesuré.

La collection vit dans `ansible_collections/<namespace>/<nom>/`, l'emplacement
qu'`ansible-test` exige. Il tourne donc **en place**, sans copie assemblée
ailleurs. La première version de ce script en fabriquait une, et c'est ce
détour qui a produit le faux vert décrit plus bas.

**`ansible-test` interroge git pour énumérer les fichiers.** Lancé sur une
arborescence que git ne suit pas, il ne trouve aucune cible et affiche :

    WARNING: All targets skipped.

...puis il sort en 0. Un vert parfait, et pas un seul fichier examiné. La
sortie ressemble exactement à celle d'une collection irréprochable. Ce script
tient donc la garde des deux côtés : la collection doit être suivie par git
**avant**, et cette phrase ne doit pas apparaître **après**.

    python scripts/sanity.py               # tous les tests
    python scripts/sanity.py --test import # un seul
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from generator.ansible.collection import Collection, load_collection

ROOT = Path(__file__).resolve().parents[1]

#: Phrase par laquelle `ansible-test` annonce qu'il n'a rien testé. Elle sort
#: sur la sortie standard, avec un code de retour 0.
NOTHING_TESTED = "All targets skipped"


def executable() -> str:
    """Chemin de `ansible-test`, celui de l'environnement courant d'abord."""
    from_env = os.environ.get("ANSIBLE_TEST")
    if from_env:
        return from_env
    beside_python = Path(sys.executable).parent / "ansible-test"
    return str(beside_python) if beside_python.is_file() else "ansible-test"


def measured_something(output: str) -> bool:
    """Faux quand `ansible-test` annonce n'avoir examiné aucune cible.

    C'est la seule chose qui distingue « la collection est saine » de « rien
    n'a été regardé », et les deux sortent en 0.
    """
    return NOTHING_TESTED not in output


def in_git_repository() -> bool:
    """Vrai quand le dépôt est un dépôt git.

    La distinction compte : **dans** un dépôt, `ansible-test` demande la liste
    des fichiers à git ; **hors** d'un dépôt, il parcourt le disque. Le faux
    vert n'existe que dans le premier cas.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def tracked_files(directory: Path) -> tuple[str, ...]:
    """Les fichiers que git suit sous ce répertoire."""
    result = subprocess.run(
        ["git", "ls-files", "--", str(directory)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return tuple(ligne for ligne in result.stdout.splitlines() if ligne)


def refusal(under_git: bool, tracked: int, where: str) -> str | None:
    """Le message de refus, ou `None` quand la mesure peut avoir lieu.

    Fonction pure, pour que la décision se teste sans dépôt ni ansible-test.
    """
    if under_git and tracked == 0:
        return (
            f"git ne suit aucun fichier sous {where} ; ansible-test n'y verrait "
            "aucune cible et sortirait en 0 sans rien examiner."
        )
    return None


def check_visible(collection: Collection) -> None:
    """Refuse de lancer une mesure qui ne porterait sur rien."""
    under_git = in_git_repository()
    suivis = tracked_files(collection.path) if under_git else ()
    message = refusal(under_git, len(suivis), os.path.relpath(collection.path, ROOT))
    if message:
        raise SystemExit(f"erreur : {message}")
    if under_git:
        print(f"{len(suivis)} fichier(s) suivi(s) par git dans {collection.fqcn}")
    else:
        print(f"hors dépôt git : ansible-test parcourra {collection.fqcn} sur disque")


def main(argv: list[str]) -> int:
    collection = load_collection()
    check_visible(collection)

    command = [executable(), "sanity", "--python", "3.12", *argv[1:]]
    print(f"$ {' '.join(command)}\n  dans {os.path.relpath(collection.path, ROOT)}\n", flush=True)

    result = subprocess.run(
        command,
        cwd=collection.path,
        text=True,
        capture_output=True,
        check=False,
    )
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)

    if not measured_something(result.stdout) or not measured_something(result.stderr):
        print(
            "\nerreur : ansible-test n'a examiné aucun fichier. "
            "Un vert qui ne mesure rien vaut moins qu'un rouge.",
            file=sys.stderr,
        )
        return 1

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
