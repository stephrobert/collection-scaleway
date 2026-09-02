"""Rend le moteur d'inventaire importable comme Ansible l'importe.

Les couches de décision ne connaissent ni Ansible ni le SDK : elles se testent
donc sans réseau, sans identifiants et sans émulateur. C'est ce qui permet de
prouver Elastic Metal et Apple Silicon, que l'émulateur ne sert pas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from generator.ansible.collection import load_collection


@pytest.fixture(scope="session", autouse=True)
def collection_importable() -> Path:
    racine = load_collection().collections_root
    if str(racine) not in sys.path:
        sys.path.insert(0, str(racine))
    return racine
