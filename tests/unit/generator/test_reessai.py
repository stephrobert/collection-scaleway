"""Ce que le générateur décide de rejouer, et sur quoi il le décide.

Un `Retry(total=5)` global rejouerait le POST qui redémarre une machine. La
politique appartient donc à l'opération, et elle se déduit de deux faits que le
contrat **dit** : la méthode HTTP, dont RFC 9110 fixe la sûreté, et la classe
que le classifieur a établie (ADR-018). Rien d'autre : aucun document Scaleway
ne déclare l'idempotence d'une opération.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.retry import RetryPolicy, depuis_le_nom, politique_par_defaut
from generator.ir.enums import HTTPMethod, OperationKind

SPECS = Path("specs/scaleway")


def test_une_lecture_se_rejoue() -> None:
    """RFC 9110 fixe `GET` comme sûre : c'est le contrat le plus fort ici."""
    assert politique_par_defaut(HTTPMethod.GET, OperationKind.INFO) is RetryPolicy.SAFE


def test_une_ecriture_se_rejoue_sous_condition() -> None:
    for methode in (HTTPMethod.PATCH, HTTPMethod.PUT):
        assert politique_par_defaut(methode, OperationKind.MANAGE) is RetryPolicy.LIMITED


def test_une_action_ne_se_rejoue_jamais() -> None:
    """La propriété que l'issue demande, prise à sa source."""
    assert politique_par_defaut(HTTPMethod.POST, OperationKind.ACTION) is RetryPolicy.NEVER


def test_la_classe_prime_sur_la_methode() -> None:
    """`ServerAction` est un `POST` comme le serait une création.

    Tester la méthode d'abord rendrait `LIMITED` pour une action, donc
    rejouable sur un `429`, ce qui est exactement ce qu'on refuse. Ce test
    existe parce que l'ordre des deux conditions **est** la décision.
    """
    assert politique_par_defaut(HTTPMethod.GET, OperationKind.ACTION) is RetryPolicy.NEVER


def test_une_politique_inventee_est_refusee() -> None:
    """Une faute de frappe qui passerait ferait un override inerte : l'opération
    garderait la politique déduite en laissant croire qu'elle en a une autre."""
    with pytest.raises(ValueError, match="politique de réessai inconnue"):
        depuis_le_nom("agressif")
