"""Le rapport de **chaque** produit suivi, en mode strict.

`python -m generator report` prend un produit, et c'est juste : il décrit un
contrat. Mais le dépôt en suit désormais plusieurs, et une tâche qui n'en
rapporte qu'un laisse le site refuser de se construire faute d'une page de
mesure, trois étapes plus loin et pour une raison qui ne se lit pas.

**La liste des produits n'est pas recopiée ici.** Elle vient de
`specs/scaleway/products.txt`, qui est l'index tenu à la main et la seule
source qui fasse foi. Ajouter un troisième produit ne demandera donc pas de
retoucher ce script, et surtout ne pourra pas l'oublier.

Le code de sortie est le plus sévère rencontré, pas celui du dernier produit :
un contrat non trié doit rougir même si celui d'après est propre.

    python scripts/report_all.py            # tous les produits, mode strict
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generator.cli import main as report_main
from generator.source.base import VendoredSpecSource

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "specs" / "scaleway"


def main() -> int:
    produits = list(VendoredSpecSource(root=SPEC_ROOT).available())
    if not produits:
        print(
            f"aucun produit dans {SPEC_ROOT.relative_to(ROOT)}/products.txt : "
            "un rapport qui ne mesure rien passerait pour un rapport vert.",
            file=sys.stderr,
        )
        return 1

    pire = 0
    for produit, version in produits:
        code = report_main(["report", produit, "--api-version", version, "--strict"])
        pire = max(pire, code)
    return pire


if __name__ == "__main__":
    raise SystemExit(main())
