"""La taxonomie des échecs.

Le plugin officiel écrit `except ScalewayException: pass` : un jeton révoqué,
un droit manquant et un produit absent d'une zone y produisent le même
inventaire incomplet avec un code de retour 0. Ces tests fixent la frontière
entre les trois.
"""

from __future__ import annotations

import pytest

from ansible_collections.local.scaleway.plugins.module_utils.inventory.errors import (
    AuthenticationFailed,
    DiscoveryFailed,
    InventoryError,
    PermissionDenied,
    ProductUnavailable,
    classify,
)


@pytest.mark.parametrize(
    ("statut", "attendu"),
    [
        (401, AuthenticationFailed),
        (403, PermissionDenied),
        (404, ProductUnavailable),
        (501, ProductUnavailable),
        (500, DiscoveryFailed),
        (429, DiscoveryFailed),
        (None, DiscoveryFailed),
    ],
)
def test_chaque_statut_va_dans_sa_categorie(statut, attendu) -> None:
    assert classify(statut) is attendu


def test_un_401_qui_parle_de_droit_refuse_reste_tolerable() -> None:
    """Scaleway rend parfois 401 pour un droit manquant : ce n'est pas fatal."""
    assert classify(401, "permission denied on this resource") is PermissionDenied


def test_toutes_les_categories_descendent_de_la_meme_racine() -> None:
    """Un appelant peut donc attraper `InventoryError` sans les énumérer."""
    for categorie in (AuthenticationFailed, PermissionDenied, ProductUnavailable, DiscoveryFailed):
        assert issubclass(categorie, InventoryError)


def test_authentification_et_droit_ne_se_confondent_pas() -> None:
    """La distinction qui décide entre « on continue » et « on s'arrête »."""
    assert classify(401) is not classify(403)
