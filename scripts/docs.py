"""Juge et produit la documentation de la collection avec l'outil officiel.

`antsibull-docs` est ce qui construit les pages de docs.ansible.com. Deux
usages ici, et le premier compte plus que le second :

* **`lint-collection-docs`** juge la documentation, et il voit une classe de
  défauts qu'`ansible-test sanity` laisse passer. Mesuré : sur un module qui
  écrit `M(local.scaleway.module_inexistant)`, `validate-modules` sort en 0
  sans rien signaler, et `antsibull-docs` sort en 3 en nommant la référence,
  dans `DOCUMENTATION` comme dans `RETURN` ;
* **`collection`** produit les pages RST, une par module, depuis la même
  `DOCUMENTATION` que le module porte. Elles ne sont pas versionnées : ce sont
  des artefacts, et `build/` les reçoit.

**Le même piège que pour `ansible-test`.** Mesuré aussi : sur une collection
qui ne contient aucun plugin, `lint-collection-docs` sort en 0 sans rien dire.
Un vert qui n'a rien examiné est indiscernable d'une documentation
irréprochable, donc ce script exige de savoir ce qu'il a examiné, avant et
après.

    python scripts/docs.py            # juger, puis produire
    python scripts/docs.py --lint     # juger seulement
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from generator.ansible.collection import Collection, load_collection

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "build" / "docs"

#: Contrôles demandés au linter. `--plugin-docs` est celui qui lit les
#: références croisées ; sans lui le linter ne juge que les fichiers annexes.
LINT_FLAGS: tuple[str, ...] = (
    "--plugin-docs",
    "--validate-collection-refs",
    "all",
    "--disallow-unknown-collection-refs",
)


class DocsError(RuntimeError):
    """La documentation ne peut pas être jugée, ou n'a pas été produite."""


def executable(name: str) -> str:
    """Chemin d'un outil de l'environnement courant."""
    beside_python = Path(sys.executable).parent / name
    return str(beside_python) if beside_python.is_file() else name


def documented_modules(collection: Collection) -> tuple[str, ...]:
    """Les modules que la collection porte, triés.

    C'est la population du contrôle : sans elle, le linter passerait sur rien
    et le dirait avec un code de retour 0.
    """
    if not collection.modules_dir.is_dir():
        return ()
    return tuple(sorted(path.stem for path in collection.modules_dir.glob("*.py")))


def modules_to_document(collection: Collection) -> tuple[str, ...]:
    """Les modules à documenter, ou une erreur qui dit pourquoi il n'y en a pas.

    Sans cette garde, `lint-collection-docs` juge une collection vide et sort
    en 0 : mesuré. Le vert serait indiscernable d'une documentation
    irréprochable.
    """
    modules = documented_modules(collection)
    if not modules:
        raise DocsError(
            f"aucun module dans {os.path.relpath(collection.modules_dir, ROOT)} : le linter "
            "passerait sur une collection vide et sortirait en 0. "
            "Lancer `mise run generate` d'abord."
        )
    return modules


def page_for(module: str, collection: Collection) -> Path:
    """Chemin de la page attendue pour un module."""
    return (
        OUTPUT_DIR / "collections" / collection.namespace / collection.name / f"{module}_module.rst"
    )


def lint(tree: Path) -> int:
    """Juge la documentation, et rend le code de retour du linter."""
    command = [executable("antsibull-docs"), "lint-collection-docs", *LINT_FLAGS, "."]
    print(f"$ {' '.join(command)}\n  dans {tree}\n", flush=True)
    result = subprocess.run(command, cwd=tree, text=True, check=False)
    return result.returncode


def render(collection: Collection) -> None:
    """Produit les pages RST, et vérifie qu'elles existent."""
    if OUTPUT_DIR.exists():
        for existing in OUTPUT_DIR.rglob("*.rst"):
            existing.unlink()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # `antsibull-docs` refuse un répertoire de sortie ouvert en écriture au
    # groupe ou à tout le monde, et le dit sans ambiguïté.
    OUTPUT_DIR.chmod(0o755)

    command = [
        executable("antsibull-docs"),
        "collection",
        "--use-current",
        "--dest-dir",
        str(OUTPUT_DIR),
        collection.fqcn,
    ]
    print(f"\n$ {' '.join(command)}", flush=True)
    result = subprocess.run(
        command,
        env={**os.environ, "ANSIBLE_COLLECTIONS_PATH": str(collection.collections_root)},
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise DocsError("antsibull-docs n'a pas produit la documentation")


def main(argv: list[str]) -> int:
    collection = load_collection()
    modules = modules_to_document(collection)
    print(f"{len(modules)} module(s) à documenter : {', '.join(modules)}\n")

    code = lint(collection.path)
    if code != 0:
        print(f"\nla documentation est refusée par antsibull-docs (code {code})", file=sys.stderr)
        return 1

    if "--lint" in argv[1:]:
        print("documentation jugée conforme")
        return 0

    render(collection)

    manquantes = [module for module in modules if not page_for(module, collection).is_file()]
    if manquantes:
        raise DocsError(f"aucune page produite pour {manquantes}")

    print(f"\n{len(modules)} page(s) écrite(s) dans {os.path.relpath(OUTPUT_DIR, ROOT)}/")
    for module in modules:
        print(f"  {os.path.relpath(page_for(module, collection), ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except DocsError as error:
        print(f"erreur : {error}", file=sys.stderr)
        raise SystemExit(1) from error
