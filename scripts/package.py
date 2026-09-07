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
    """Les fichiers que l'archive porte, triés. Les répertoires n'en sont pas."""
    with tarfile.open(archive, "r:gz") as tar:
        return tuple(sorted(member.name for member in tar.getmembers() if member.isfile()))


def entrees(archive: Path) -> tuple[str, ...]:
    """**Tout** ce que l'archive porte, répertoires compris.

    La distinction n'est pas théorique : l'archive emportait un répertoire
    `tests/` vide, et le contrôle des fuites ne le voyait pas parce qu'il ne
    regardait que les fichiers. Un lecteur du tarball y lit pourtant que la
    collection livre ses tests, et le jour où un fichier s'y glisse, c'est le
    `build_ignore` qui décide seul.
    """
    with tarfile.open(archive, "r:gz") as tar:
        return tuple(sorted(member.name for member in tar.getmembers()))


def check_contents(archive: Path) -> tuple[str, ...]:
    """Refuse une archive qui emporte le générateur, ou qui oublie un module.

    Les deux moitiés comptent : sans la seconde, une archive vide passerait
    tous les contrôles de la première.
    """
    contenu = members(archive)

    # Sur **toutes** les entrées, et pas seulement les fichiers : un répertoire
    # interdit, même vide, annonce au lecteur du tarball quelque chose qui n'a
    # pas sa place chez lui.
    fuites = sorted(
        {
            chemin.split("/", 1)[0]
            for chemin in entrees(archive)
            if chemin.split("/", 1)[0] in FORBIDDEN
        }
    )
    if fuites:
        raise PackageError(f"l'archive emporte ce qui doit rester au dépôt : {fuites}")

    manquants = [attendu for attendu in REQUIRED if attendu not in contenu]
    if manquants:
        raise PackageError(f"l'archive n'emporte pas {manquants}")

    return contenu


def check_installed(collections_path: Path, collection: Collection) -> None:
    """Interroge **tous** les modules depuis la collection installée.

    `ansible-doc` charge la collection comme Ansible le fera. C'est la seule
    preuve que l'archive sert, et elle ne vaut que pour ce qu'on interroge :
    ce contrôle portait sur un « module représentatif », donc sur un cinquantième
    du paquet. Un module cassé parmi les quarante-neuf autres passait.

    Les noms partent en **un seul appel** : `ansible-doc` en accepte plusieurs,
    et cinquante processus coûteraient une minute là où un en coûte deux
    secondes.
    """
    noms = sorted(
        chemin.stem
        for chemin in (collection.path / "plugins" / "modules").glob("*.py")
        if not chemin.stem.startswith("_")
    )
    if not noms:
        raise PackageError(
            "aucun module à interroger : un contrôle qui n'examine rien rend "
            "vert sur n'importe quoi."
        )
    fqcns = [collection.module_fqcn(nom) for nom in noms]
    result = subprocess.run(
        [executable("ansible-doc"), "--json", *fqcns],
        env={**os.environ, "ANSIBLE_COLLECTIONS_PATH": str(collections_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PackageError(
            f"`ansible-doc` a échoué sur les {len(fqcns)} modules de l'archive "
            f"installée :\n{result.stderr}"
        )

    payload = json.loads(result.stdout or "{}")
    muets: list[str] = []
    sans_options: list[str] = []
    for fqcn in fqcns:
        documentation = payload.get(fqcn, {}).get("doc", {})
        if not documentation.get("short_description"):
            muets.append(fqcn)
        elif not documentation.get("options"):
            sans_options.append(fqcn)
    if muets:
        raise PackageError(
            f"{len(muets)} module(s) que l'archive installée ne documente pas : {muets[:5]}"
        )
    if sans_options:
        raise PackageError(
            f"{len(sans_options)} module(s) installé(s) sans aucune option : "
            f"{sans_options[:5]}. Tous en portent au moins une, `zone` ou `region`."
        )
    print(f"  {len(fqcns)} module(s) interrogé(s) depuis l'archive installée, tous documentés")


#: Les répertoires de `plugins/` qu'`ansible-doc` sait interroger, et le type
#: qu'il attend pour chacun.
#:
#: La table est **exhaustive par décision** : un répertoire absent d'ici et de
#: `PLUGINS_NON_INTERROGEABLES` fait échouer le contrôle. Une découverte qui
#: ignorerait ce qu'elle ne connaît pas laisserait un plugin entier hors de la
#: preuve, et personne ne s'en apercevrait.
TYPES_DE_PLUGINS: dict[str, str] = {
    "inventory": "inventory",
    "lookup": "lookup",
    "filter": "filter",
    "test": "test",
    "connection": "connection",
    "callback": "callback",
    "become": "become",
    "cache": "cache",
    "shell": "shell",
    "strategy": "strategy",
    "vars": "vars",
}

#: Les répertoires de `plugins/` qu'`ansible-doc` ne sait pas interroger, et
#: qui ne sont donc pas une omission.
#:
#: `modules` a son propre contrôle, qui les interroge tous. `module_utils` est
#: du code partagé sans documentation propre ; `doc_fragments` est de la
#: documentation que les modules incorporent, et `ansible-doc` la rend déjà
#: fondue dans la leur — c'est là qu'elle se vérifie.
PLUGINS_NON_INTERROGEABLES = frozenset({"modules", "module_utils", "doc_fragments", "action"})

#: Ce qu'un utilisateur écrit dans son fichier de configuration, par type de
#: plugin. Si l'archive n'expose pas ces options, le plugin est présent et
#: inutilisable.
OPTIONS_ATTENDUES: dict[str, tuple[str, ...]] = {
    "inventory": ("plugin", "products", "hostnames", "address_priority", "group_by"),
}


def check_types_de_plugins(collection: Collection) -> None:
    """Refuse un répertoire de `plugins/` que ce contrôle ne sait pas traiter.

    C'est ce qui empêche la découverte d'être une passoire : le jour où un
    `lookup/` apparaît, il est interrogé ; le jour où un répertoire inconnu
    apparaît, le contrôle le dit au lieu de l'ignorer.
    """
    racine = collection.path / "plugins"
    presents = {d.name for d in racine.iterdir() if d.is_dir() and not d.name.startswith("_")}
    inconnus = sorted(presents - set(TYPES_DE_PLUGINS) - PLUGINS_NON_INTERROGEABLES)
    if inconnus:
        raise PackageError(
            f"répertoire(s) de plugins que ce contrôle ne sait pas traiter : {inconnus}. "
            "Les ajouter à `TYPES_DE_PLUGINS` s'ils s'interrogent, à "
            "`PLUGINS_NON_INTERROGEABLES` sinon. Un répertoire ignoré est un "
            "plugin hors de la preuve."
        )


def check_inventory_plugin(collections_path: Path, collection: Collection) -> None:
    """Interroge le plugin d'inventaire depuis la collection installée.

    Un plugin d'inventaire est plus fragile qu'un module dans une archive : il
    dépend d'un paquet entier sous `module_utils/`, et un répertoire oublié au
    build ne se voit pas dans la liste des fichiers. `ansible-doc -t inventory`
    charge le plugin comme Ansible le fera, et une option manquante dit que
    l'archive porte le fichier sans porter le plugin.
    """
    # **Le nom du plugin se lit sur le disque, et sa cardinalité ne se suppose
    # pas.** Le nom était écrit `scaleway` en dur, et le renommer en `compute` a
    # fait interroger un plugin qui n'existe plus. Le contrôle a ensuite refusé
    # d'en voir deux, ce qui marchait tant qu'il n'y en avait qu'un : c'est la
    # même hypothèse, déplacée du nom vers le nombre.
    for type_ansible, repertoire in sorted(TYPES_DE_PLUGINS.items()):
        dossier = collection.path / "plugins" / repertoire
        if not dossier.is_dir():
            continue
        plugins = sorted(f.stem for f in dossier.glob("*.py") if not f.stem.startswith("_"))
        # **Un répertoire présent et vide est un plugin qui a disparu.** Le
        # contrôle précédent refusait « 0 plugin » parce qu'il en interrogeait
        # exactement un ; celui-ci en interroge autant qu'il en trouve, et
        # trouverait zéro sans rien dire. L'intention se garde, sa forme change.
        if not plugins:
            raise PackageError(
                f"{dossier.relative_to(collection.path)} existe et ne porte aucun plugin : "
                "un plugin qui disparaît ne doit pas passer pour un paquet correct."
            )
        for nom in plugins:
            fqcn = f"{collection.fqcn}.{nom}"
            result = subprocess.run(
                [executable("ansible-doc"), "-t", type_ansible, "--json", fqcn],
                env={**os.environ, "ANSIBLE_COLLECTIONS_PATH": str(collections_path)},
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise PackageError(
                    f"`ansible-doc -t {type_ansible} {fqcn}` a échoué depuis l'archive "
                    f"installée :\n{result.stderr}"
                )
            payload = json.loads(result.stdout or "{}")
            options = payload.get(fqcn, {}).get("doc", {}).get("options", {})
            attendues = OPTIONS_ATTENDUES.get(type_ansible, ())
            manquantes = [attendue for attendue in attendues if attendue not in options]
            if manquantes:
                raise PackageError(
                    f"{fqcn} installé ne documente pas {manquantes} : le plugin est dans "
                    f"l'archive, mais Ansible n'en voit pas la configuration"
                )
            print(f"  {fqcn} : plugin {type_ansible} chargé, {len(options)} option(s)")


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
    check_types_de_plugins(collection)
    check_installed(installation, collection)
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
