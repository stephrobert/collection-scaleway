"""Rend la collection importable comme Ansible l'importe à l'exécution.

Un module généré fait `from ansible_collections.local.scaleway.plugins...`.
Ce chemin existe tel quel dans le dépôt, parce que la collection est rangée à
l'emplacement qu'Ansible attend : il suffit d'ouvrir la racine du dépôt à
l'import.

Importer le fichier par son emplacement sur disque serait plus court, et ne
prouverait pas la même chose : c'est le chemin d'import qui casse en premier
quand le namespace change.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from generator.ansible.collection import Collection, load_collection

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def collection() -> Collection:
    return load_collection()


@pytest.fixture(scope="session")
def collection_root(collection: Collection) -> Path:
    """Ouvre l'import de `ansible_collections.<namespace>.<nom>` pour la session."""
    racine = str(collection.collections_root)
    if racine not in sys.path:
        sys.path.insert(0, racine)
    return collection.collections_root
