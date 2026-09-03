"""Identité et emplacement de la collection.

La collection vit dans `ansible_collections/<namespace>/<nom>/`, à
l'emplacement qu'Ansible impose. Ce n'est pas une préférence de rangement :
c'est ce qui permet à `ansible-test`, `antsibull-docs` et `ansible-playbook`
de travailler **en place**, sans qu'on assemble une copie ailleurs.

Deux sources décrivent alors la même identité, et Ansible les lit toutes les
deux : le **chemin** (`ansible_collections/stephrobert/scaleway`) et **galaxy.yml**.
On ne peut pas en supprimer une, l'outil impose les deux. Ce qu'on peut faire,
et que fait `load_collection`, c'est **exiger qu'elles concordent** : une
collection dont le chemin et le manifeste divergent se charge sous un nom et
se déclare sous un autre, et rien d'autre ne le dirait avant l'exécution.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]

#: Racine des collections du dépôt. Ansible cherche ses collections sous un
#: répertoire portant exactement ce nom.
DEFAULT_COLLECTIONS_ROOT = ROOT / "ansible_collections"

#: Champs sans lesquels aucun module ne peut être rendu.
_REQUIRED_FIELDS: tuple[str, ...] = ("namespace", "name", "version")


class CollectionError(ValueError):
    """La collection est introuvable, ou elle ne se décrit pas de façon cohérente."""


@dataclass(frozen=True)
class Collection:
    """Ce qu'un module généré doit savoir de la collection qui l'héberge."""

    namespace: str
    name: str
    version: str
    path: Path
    authors: tuple[str, ...] = ()

    @property
    def fqcn(self) -> str:
        """`stephrobert.scaleway`, le préfixe du nom complet d'un module."""
        return f"{self.namespace}.{self.name}"

    @property
    def module_utils_import(self) -> str:
        """Chemin d'import du runtime, tel qu'Ansible le résout à l'exécution."""
        return f"ansible_collections.{self.fqcn}.plugins.module_utils.scaleway"

    @property
    def doc_fragment(self) -> str:
        """Nom complet du fragment de documentation des paramètres communs."""
        return f"{self.fqcn}.scaleway"

    @property
    def collections_root(self) -> Path:
        """Le répertoire à mettre dans `ANSIBLE_COLLECTIONS_PATH`.

        Ansible veut le répertoire qui *contient* `ansible_collections/`, pas
        la collection elle-même.
        """
        return self.path.parents[2]

    @property
    def modules_dir(self) -> Path:
        return self.path / "plugins" / "modules"

    @property
    def playbooks_dir(self) -> Path:
        return self.path / "playbooks"

    def module_fqcn(self, module: str) -> str:
        return f"{self.fqcn}.{module}"


def find_collection(collections_root: Path = DEFAULT_COLLECTIONS_ROOT) -> Path:
    """Trouve l'unique collection du dépôt, par son `galaxy.yml`.

    Une seule, et le dire : deux collections dans un même dépôt demanderaient
    de choisir, et un choix implicite est un choix que personne ne relit.
    """
    if not collections_root.is_dir():
        raise CollectionError(f"répertoire de collections absent : {collections_root}")

    manifestes = sorted(collections_root.glob("*/*/galaxy.yml"))
    if not manifestes:
        raise CollectionError(
            f"aucun galaxy.yml sous {collections_root}/<namespace>/<nom>/ : "
            "la collection n'est pas à l'emplacement qu'Ansible attend"
        )
    if len(manifestes) > 1:
        trouvees = [str(m.parent.relative_to(collections_root)) for m in manifestes]
        raise CollectionError(f"plusieurs collections dans le dépôt : {trouvees}")
    return manifestes[0].parent


def load_collection(path: Path | None = None) -> Collection:
    """Charge l'identité de la collection, et exige qu'elle soit cohérente."""
    directory = path or find_collection()
    manifeste = directory / "galaxy.yml"
    if not manifeste.is_file():
        raise CollectionError(f"galaxy.yml absent : {manifeste}")

    with manifeste.open(encoding="utf-8") as handle:
        document: Any = yaml.safe_load(handle)
    if not isinstance(document, dict):
        raise CollectionError(f"{manifeste} ne contient pas un mapping")

    missing = [field for field in _REQUIRED_FIELDS if not document.get(field)]
    if missing:
        raise CollectionError(f"{manifeste} : champs obligatoires absents {missing}")

    namespace = str(document["namespace"])
    name = str(document["name"])

    # Ansible charge la collection par son chemin et la décrit par son
    # manifeste. Les deux qui divergent, c'est une collection qui répond à un
    # nom et s'annonce sous un autre.
    attendu = (namespace, name)
    trouve = (directory.parent.name, directory.name)
    if trouve != attendu:
        raise CollectionError(
            f"{manifeste} déclare {namespace}.{name}, "
            f"et le chemin dit {trouve[0]}.{trouve[1]} : "
            "Ansible chargerait la collection sous le nom du chemin"
        )

    authors = document.get("authors") or []
    return Collection(
        namespace=namespace,
        name=name,
        version=str(document["version"]),
        path=directory,
        authors=tuple(str(author) for author in authors),
    )
