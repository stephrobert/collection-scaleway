"""Construit l'archive de la collection, l'installe, et vérifie qu'elle sert.

Une archive qui existe ne prouve rien. Ce script fait les trois choses, dans
cet ordre, et la troisième est celle qui compte :

1. **construire** avec `ansible-galaxy collection build`, depuis la collection
   telle qu'elle est rangée dans `ansible_collections/<namespace>/<nom>/` :
   ce qui part est ce que le répertoire contient, et le `build_ignore` de
   `galaxy.yml` n'a plus à écarter le générateur, qui n'y est pas ;
2. **contrôler le contenu** de l'archive. Le générateur, les contrats et les
   tests n'ont rien à faire chez un utilisateur, et une archive qui les
   emporte est une fuite, pas un détail de taille ;
3. **installer et interroger**. La preuve est qu'`ansible-doc` charge le module
   depuis la collection installée et rend sa documentation. Un fichier présent
   dans une archive n'est pas un module qu'Ansible sait charger.

    python scripts/package.py
    python scripts/package.py --keep    # garder l'installation temporaire
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from generator.ansible.collection import Collection, load_collection

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "build" / "dist"

#: Ce qu'une archive livrée ne doit jamais contenir. La liste est celle des
#: répertoires du dépôt qui n'ont aucun sens chez un utilisateur.
FORBIDDEN: tuple[str, ...] = ("generator", "specs", "scripts", "tests", ".venv")

#: Ce qu'elle doit contenir pour être autre chose qu'une coquille.
REQUIRED: tuple[str, ...] = (
    "MANIFEST.json",
    "LICENSE",
    "CHANGELOG.rst",
    "changelogs/changelog.yaml",
    "meta/runtime.yml",
    "meta/execution-environment.yml",
    "meta/ee-requirements.txt",
    "playbooks/inventaire_serveurs.yml",
    "plugins/modules/instance_server_info.py",
    "plugins/module_utils/scaleway.py",
    "plugins/doc_fragments/scaleway.py",
)


class PackageError(RuntimeError):
    """L'archive n'a pas été produite, ou elle ne tient pas ses promesses."""


def executable(name: str) -> str:
    beside_python = Path(sys.executable).parent / name
    return str(beside_python) if beside_python.is_file() else name


def archive_name(collection: Collection) -> str:
    """`local-scaleway-0.1.0.tar.gz`, le nom que Galaxy impose."""
    return f"{collection.namespace}-{collection.name}-{collection.version}.tar.gz"


def members(archive: Path) -> tuple[str, ...]:
    """Les chemins que l'archive porte, triés."""
    with tarfile.open(archive, "r:gz") as tar:
        return tuple(sorted(member.name for member in tar.getmembers() if member.isfile()))


def check_contents(archive: Path) -> tuple[str, ...]:
    """Refuse une archive qui emporte le générateur, ou qui oublie un module.

    Les deux moitiés comptent : sans la seconde, une archive vide passerait
    tous les contrôles de la première.
    """
    contenu = members(archive)

    fuites = sorted(
        {chemin.split("/", 1)[0] for chemin in contenu if chemin.split("/", 1)[0] in FORBIDDEN}
    )
    if fuites:
        raise PackageError(f"l'archive emporte ce qui doit rester au dépôt : {fuites}")

    manquants = [attendu for attendu in REQUIRED if attendu not in contenu]
    if manquants:
        raise PackageError(f"l'archive n'emporte pas {manquants}")

    return contenu


def check_installed(collections_path: Path, collection: Collection, module: str) -> None:
    """Interroge le module depuis la collection installée.

    `ansible-doc` charge la collection comme Ansible le fera, et rend la
    documentation du module. C'est la seule preuve que l'archive sert.
    """
    fqcn = collection.module_fqcn(module)
    result = subprocess.run(
        [executable("ansible-doc"), "--json", fqcn],
        env={**os.environ, "ANSIBLE_COLLECTIONS_PATH": str(collections_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PackageError(
            f"`ansible-doc {fqcn}` a échoué depuis l'archive installée :\n{result.stderr}"
        )

    payload = json.loads(result.stdout or "{}")
    documentation = payload.get(fqcn, {}).get("doc", {})
    options = documentation.get("options", {})
    if "zone" not in options:
        raise PackageError(f"{fqcn} installé ne documente pas ses options : {sorted(options)}")
    courte = documentation.get("short_description")
    print(f"  {fqcn} : {len(options)} option(s), short_description « {courte} »")


#: Ce qu'un utilisateur écrit dans son fichier d'inventaire. Si l'archive
#: n'expose pas ces options, le plugin est présent et inutilisable.
INVENTORY_OPTIONS = ("plugin", "products", "hostnames", "address_priority", "group_by")


def check_inventory_plugin(collections_path: Path, collection: Collection) -> None:
    """Interroge le plugin d'inventaire depuis la collection installée.

    Un plugin d'inventaire est plus fragile qu'un module dans une archive : il
    dépend d'un paquet entier sous `module_utils/`, et un répertoire oublié au
    build ne se voit pas dans la liste des fichiers. `ansible-doc -t inventory`
    charge le plugin comme Ansible le fera, et une option manquante dit que
    l'archive porte le fichier sans porter le plugin.
    """
    fqcn = f"{collection.fqcn}.scaleway"
    result = subprocess.run(
        [executable("ansible-doc"), "-t", "inventory", "--json", fqcn],
        env={**os.environ, "ANSIBLE_COLLECTIONS_PATH": str(collections_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PackageError(
            f"`ansible-doc -t inventory {fqcn}` a échoué depuis l'archive installée :"
            f"\n{result.stderr}"
        )

    payload = json.loads(result.stdout or "{}")
    options = payload.get(fqcn, {}).get("doc", {}).get("options", {})
    manquantes = [nom for nom in INVENTORY_OPTIONS if nom not in options]
    if manquantes:
        raise PackageError(
            f"{fqcn} installé ne documente pas {manquantes} : le plugin est dans "
            f"l'archive, mais Ansible n'en voit pas la configuration"
        )
    print(f"  {fqcn} : plugin d'inventaire chargé, {len(options)} option(s)")


def check_playbooks(collections_path: Path, collection: Collection) -> None:
    """Vérifie que les playbooks livrés s'appellent par leur nom complet.

    C'est tout l'intérêt de `playbooks/` plutôt que d'un répertoire d'exemples :
    une fois la collection installée, `ansible-playbook
    stephrobert.scaleway.inventaire_serveurs` résout sans chemin. Le contrôle
    n'exécute rien, il exige que la résolution aboutisse.
    """
    racine = collections_path / "ansible_collections" / collection.namespace / collection.name
    noms = sorted(chemin.stem for chemin in (racine / "playbooks").glob("*.yml"))
    if not noms:
        raise PackageError("l'archive n'emporte aucun playbook")

    for nom in noms:
        fqcn = f"{collection.fqcn}.{nom}"
        result = subprocess.run(
            [executable("ansible-playbook"), "--list-tasks", fqcn],
            env={**os.environ, "ANSIBLE_COLLECTIONS_PATH": str(collections_path)},
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise PackageError(f"`ansible-playbook {fqcn}` ne résout pas :\n{result.stderr}")
        print(f"  {fqcn} : résolu depuis la collection installée")


def main(argv: list[str]) -> int:
    collection = load_collection()
    workdir = Path(tempfile.mkdtemp(prefix="scaleway-package-"))

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    built = subprocess.run(
        [
            executable("ansible-galaxy"),
            "collection",
            "build",
            "--force",
            "--output-path",
            str(DIST_DIR),
            str(collection.path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if built.returncode != 0:
        print(built.stdout + built.stderr, file=sys.stderr)
        raise PackageError("ansible-galaxy n'a pas construit l'archive")

    archive = DIST_DIR / archive_name(collection)
    if not archive.is_file():
        raise PackageError(f"archive attendue et absente : {archive}")

    contenu = check_contents(archive)
    taille = archive.stat().st_size
    print(f"{os.path.relpath(archive, ROOT)} : {len(contenu)} fichier(s), {taille // 1024} Kio")

    installation = workdir / "installed"
    installed = subprocess.run(
        [
            executable("ansible-galaxy"),
            "collection",
            "install",
            str(archive),
            "--force",
            "-p",
            str(installation),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if installed.returncode != 0:
        print(installed.stdout + installed.stderr, file=sys.stderr)
        raise PackageError("l'archive ne s'installe pas")

    print(f"installée dans {installation}")
    check_installed(installation, collection, "instance_server_info")
    check_inventory_plugin(installation, collection)
    check_playbooks(installation, collection)

    print(
        "\npour l'installer chez soi :\n"
        f"  ansible-galaxy collection install {os.path.relpath(archive, ROOT)}"
    )

    if "--keep" not in argv[1:]:
        subprocess.run(["rm", "-rf", str(workdir)], check=False)
    else:
        print(f"\ninstallation conservée : {installation}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except PackageError as error:
        print(f"erreur : {error}", file=sys.stderr)
        raise SystemExit(1) from error
