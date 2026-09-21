"""`parser_coverage` mesure les contrats générés, et rien d'autre.

Le script relisait `products.txt` à la main. Une ligne `ipam v1 suivi` s'y
lisait comme `<slug> <produit> <version>` : il cherchait `v1.suivi.yml`, le
disait absent sur la sortie d'erreur, et sortait en 0. Une ligne de bruit par
contrat suivi à chaque passage, et un vrai contrat manquant qui se serait perdu
dedans.

**La liste ne se recopie pas, elle se dérive.** Ce contrôle nommait `ipam`
comme représentant des contrats suivis, et la promotion d'ipam et de vpc (#258)
l'a rendu faux : il exigeait l'absence d'un produit désormais mesuré. Un nom de
produit écrit ici se périme à chaque promotion, et il se périme en rougissant
pour une raison qui n'est pas celle qu'il surveille.
"""

from __future__ import annotations

import parser_coverage
import pytest
from sync_specs import read_products


def test_les_contrats_suivis_ne_sont_ni_mesures_ni_dits_absents(
    capsys: pytest.CaptureFixture[str],
) -> None:
    produits = read_products()
    generes = [produit for produit in produits if not produit.tracked_only]
    suivis = [produit for produit in produits if produit.tracked_only]
    assert generes, "l'index ne déclare aucun contrat généré"
    assert suivis, "l'index ne déclare aucun contrat suivi : le contrôle ne mesure plus rien"

    assert parser_coverage.main(["parser_coverage.py"]) == 0

    sortie = capsys.readouterr()
    assert "absent" not in sortie.err
    assert "suivi" not in sortie.err

    for produit in generes:
        assert f"=== {produit.product} {produit.version}" in sortie.out, (
            f"`{produit.product}` est généré et n'est pas mesuré"
        )
    for produit in suivis:
        assert produit.product not in sortie.out, (
            f"`{produit.product}` est suivi sans être généré : il n'a ni module ni rapport, "
            "et le mesurer produirait le bruit que ce contrôle existe pour empêcher"
        )
