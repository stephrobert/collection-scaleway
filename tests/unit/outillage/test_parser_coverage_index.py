"""`parser_coverage` mesure les contrats générés, et rien d'autre.

Le script relisait `products.txt` à la main. Une ligne `ipam v1 suivi` s'y
lisait comme `<slug> <produit> <version>` : il cherchait `v1.suivi.yml`, le
disait absent sur la sortie d'erreur, et sortait en 0. Une ligne de bruit par
contrat suivi à chaque passage, et un vrai contrat manquant qui se serait perdu
dedans.
"""

from __future__ import annotations

import parser_coverage
import pytest


def test_les_contrats_suivis_ne_sont_ni_mesures_ni_dits_absents(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert parser_coverage.main(["parser_coverage.py"]) == 0

    sortie = capsys.readouterr()
    assert "absent" not in sortie.err
    assert "suivi" not in sortie.err
    assert "=== instance v1" in sortie.out
    assert "=== lb v1" in sortie.out
    assert "ipam" not in sortie.out
