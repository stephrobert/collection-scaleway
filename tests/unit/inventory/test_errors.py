"""La taxonomie des échecs.

Le plugin officiel écrit `except ScalewayException: pass` : un jeton révoqué,
un droit manquant et un produit absent d'une zone y produisent le même
inventaire incomplet avec un code de retour 0. Ces tests fixent la frontière
entre les trois.
"""

from __future__ import annotations

import pytest

from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.errors import (
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


def test_toutes_les_categories_descendent_de_la_meme_racine() -> None:
    """Un appelant peut donc attraper `InventoryError` sans les énumérer."""
    for categorie in (AuthenticationFailed, PermissionDenied, ProductUnavailable, DiscoveryFailed):
        assert issubclass(categorie, InventoryError)


def test_authentification_et_droit_ne_se_confondent_pas() -> None:
    """La distinction qui décide entre « on continue » et « on s'arrête »."""
    assert classify(401) is not classify(403)


def test_le_corps_401_reel_de_scaleway_est_bien_fatal() -> None:
    """Le défaut le plus coûteux de cette taxonomie, et le plus discret.

    Scaleway rend `{"message": "denied authentication", ...}` sur un refus
    d'authentification, et la règle cherchait `denied`. Aucun jeton révoqué ne
    levait donc `AuthenticationFailed` : la moitié fatale ne servait à rien, et
    un inventaire vide sortait avec un code de retour 0.
    """
    corps = '{"message": "denied authentication", "type": "denied_authentication"}'
    assert classify(401, corps) is AuthenticationFailed


def test_un_401_qui_parle_de_permission_reste_tolerable() -> None:
    """Scaleway rend parfois 401 pour un droit manquant : la nuance survit."""
    assert classify(401, "permission denied on this resource") is PermissionDenied
