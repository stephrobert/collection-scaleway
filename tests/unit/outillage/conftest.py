"""Rend les scripts du dépôt importables par les tests.

`scripts/` n'est pas un paquet installé : les scripts s'appellent par leur nom
de fichier, et c'est délibéré. Les tester demande donc de leur ouvrir le chemin
d'import, ici et pas ailleurs.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = str(REPO_ROOT / "scripts")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
