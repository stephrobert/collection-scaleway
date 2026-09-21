"""Écrire les modules de chaque produit généré, sans nommer aucun produit ici.

La tâche `generate` nommait les produits à la main, l'un après l'autre. Elle
recopiait donc `specs/scaleway/products.txt`, qui est déjà l'index, et un
troisième produit ajouté à l'index n'aurait rien produit tant que personne
n'aurait pensé à ajouter une ligne ici. C'est exactement l'écart que le dépôt
existe pour ne pas laisser vivre : on ne suit pas la surface à la main, on la
mesure.

`VendoredSpecSource.available()` ne rend que les produits **générés** : ce que
l'index range sous `suivis/` n'y figure pas, et c'est voulu. Élargir la
génération à un produit que la collection ne sert pas ajouterait des UNKNOWN
permanents.

`MODULES` restreint le périmètre quand on veut régénérer un module précis. Vide,
il ne restreint rien : une liste vide passée en `--module` déguiserait un refus
du modèle en décision humaine, et c'est un défaut déjà payé une fois.

    python scripts/generate_all.py
    MODULES="instance_server_info" python scripts/generate_all.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator.cli import main as generator_main
from generator.source.base import VendoredSpecSource

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "specs" / "scaleway"


def main() -> int:
    produits = list(VendoredSpecSource(root=SPEC_ROOT).available())
    if not produits:
        print(
            f"aucun produit généré dans {SPEC_ROOT.relative_to(ROOT)}/products.txt : "
            "une génération qui n'écrit rien passerait pour une génération verte.",
            file=sys.stderr,
        )
        return 1

    restriction = [
        drapeau
        for module in os.environ.get("MODULES", "").split()
        for drapeau in ("--module", module)
    ]

    # **La version se passe, elle ne se redevine pas.** Elle était lue puis
    # jetée, et `generate` retombait sur son défaut `v1` : tant que tous les
    # produits générés étaient en v1, les deux valeurs coïncidaient et rien ne
    # le disait. `vpc v2` est le premier à les séparer, et la génération
    # s'arrêtait sur `contrat absent : specs/scaleway/vpc.v1.yml` - un produit
    # connu de l'index et inconnu de la génération.
    pire = 0
    for produit, version in produits:
        pire = max(
            pire,
            generator_main(["generate", produit, "--api-version", version, *restriction]),
        )

    # La table de résolution est fondue entre tous les contrats générés, donc
    # elle s'écrit une fois, après eux. Un identifiant revendiqué par deux
    # produits ne se voit pas depuis un seul.
    return max(pire, generator_main(["resolve"]))


if __name__ == "__main__":
    raise SystemExit(main())
