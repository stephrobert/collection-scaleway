"""Ce que le plugin sérialise, et ce qu'il rend après un aller-retour de cache.

Toute exécution passe par cette sérialisation, avec ou sans cache : ce qui n'y
survit pas n'existe pas pour l'utilisateur, même si le provider l'a produit.
"""

from __future__ import annotations

from types import SimpleNamespace

from ansible_collections.stephrobert.scaleway.plugins.inventory.compute import (
    InventoryModule,
    _plain,
)
from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.models import (
    InventoryHost,
    NetworkAttachment,
)


def test_la_reponse_brute_survit_a_laller_retour() -> None:
    """`include_raw` était entièrement inerte.

    L'option était documentée, comptée dans la clé de cache, testée côté
    provider, et sans le moindre effet observable : `_serialise` ne portait pas
    `raw`, et tout run passe par là.
    """
    host = InventoryHost(
        id="i-1",
        product="instance",
        raw=SimpleNamespace(id="i-1", commercial_type="DEV1-S"),
    )

    rendu = InventoryModule._deserialise(InventoryModule._serialise(host))

    assert rendu.raw is not None
    assert rendu.raw["commercial_type"] == "DEV1-S"


def test_sans_reponse_brute_rien_nest_invente() -> None:
    """Le contre-exemple : `include_raw` désactivé ne doit pas poser un objet."""
    host = InventoryHost(id="i-1", product="instance")
    assert InventoryModule._deserialise(InventoryModule._serialise(host)).raw is None


def test_ce_quun_cache_ne_sait_pas_ecrire_devient_du_texte() -> None:
    """Un cache jsonfile ne sait écrire ni une date ni un enum. Le champ est un
    confort de diagnostic : il n'a pas à casser un inventaire."""

    class Opaque:
        __slots__ = ()

        def __str__(self) -> str:
            return "objet-opaque"

    reduit = _plain({"date": Opaque(), "liste": [Opaque()], "nombre": 3})

    assert reduit == {"date": "objet-opaque", "liste": ["objet-opaque"], "nombre": 3}


def test_le_reste_du_modele_traverse_sans_perte() -> None:
    """Le contre-exemple qui borne le précédent : si tout devenait du texte,
    les tests ci-dessus passeraient aussi."""
    host = InventoryHost(
        id="i-1",
        product="instance",
        name="web01",
        zone="fr-par-1",
        tags=("env=prod",),
        public_ipv4=("51.15.1.1",),
        private_networks=(NetworkAttachment("pn-1", "backend", "vpc-1", "socle", ("10.0.0.5",)),),
    )

    rendu = InventoryModule._deserialise(InventoryModule._serialise(host))

    assert rendu.name == "web01"
    assert rendu.tags == ("env=prod",)
    assert rendu.public_ipv4 == ("51.15.1.1",)
    assert rendu.private_networks[0].vpc_name == "socle"
    assert rendu.private_networks[0].ipv4 == ("10.0.0.5",)
