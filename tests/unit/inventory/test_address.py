"""Le choix de `ansible_host`, la décision la plus lourde du plugin.

La fonction est pure : aucun appel, aucune configuration globale. Ces tests
couvrent les cas qu'un parc réel produit, et chacun vérifie **aussi** la
raison rendue, parce qu'une adresse sans explication ne se diagnostique pas.
"""

from __future__ import annotations

import pytest

from ansible_collections.local.scaleway.plugins.module_utils.inventory.address import (
    AddressPolicy,
    select_ansible_host,
)
from ansible_collections.local.scaleway.plugins.module_utils.inventory.models import (
    InventoryHost,
    NetworkAttachment,
)


def _host(**champs) -> InventoryHost:
    return InventoryHost(id="i-1", product="instance", name="web01", **champs)


def test_seulement_une_adresse_publique_ipv4() -> None:
    selection = select_ansible_host(_host(public_ipv4=("51.15.1.1",)), AddressPolicy())
    assert selection.address == "51.15.1.1"
    assert selection.source == "public_ipv4"


def test_seulement_ipv6_ne_suppose_pas_ipv4() -> None:
    """IPv6 est de premier rang : ne jamais supposer qu'une machine a de l'IPv4."""
    selection = select_ansible_host(_host(public_ipv6=("2001:db8::1",)), AddressPolicy())
    assert selection.address == "2001:db8::1"
    assert selection.source == "public_ipv6"


def test_le_prive_passe_avant_le_public_par_defaut() -> None:
    host = _host(public_ipv4=("51.15.1.1",), private_ipv4=("10.0.0.5",))
    assert select_ansible_host(host, AddressPolicy()).address == "10.0.0.5"


def test_une_priorite_publique_inverse_le_choix() -> None:
    """Le cas du poste de travail hors VPC."""
    host = _host(public_ipv4=("51.15.1.1",), private_ipv4=("10.0.0.5",))
    politique = AddressPolicy(priority=("public_ipv4", "public_ipv6"))
    assert select_ansible_host(host, politique).address == "51.15.1.1"


def test_plusieurs_reseaux_prives_le_choix_reste_deterministe() -> None:
    """Sans réseau nommé, c'est l'ordre des rattachements qui tranche."""
    host = _host(
        private_ipv4=("10.10.0.5", "10.20.0.7"),
        private_networks=(
            NetworkAttachment("pn1", "backend", ipv4=("10.10.0.5",)),
            NetworkAttachment("pn2", "monitoring", ipv4=("10.20.0.7",)),
        ),
    )
    selection = select_ansible_host(host, AddressPolicy())
    assert selection.address == "10.10.0.5"
    assert selection.private_network == "backend"


def test_un_reseau_nomme_impose_son_adresse() -> None:
    """La fonctionnalité qui distingue ce plugin : joindre par un réseau précis."""
    host = _host(
        private_ipv4=("10.10.0.5", "10.20.0.7"),
        private_networks=(
            NetworkAttachment("pn1", "backend", ipv4=("10.10.0.5",)),
            NetworkAttachment("pn2", "monitoring", ipv4=("10.20.0.7",)),
        ),
    )
    selection = select_ansible_host(host, AddressPolicy(private_network="monitoring"))
    assert selection.address == "10.20.0.7"
    assert selection.private_network == "monitoring"


def test_un_reseau_nomme_par_identifiant_marche_aussi() -> None:
    host = _host(private_networks=(NetworkAttachment("pn2", "monitoring", ipv4=("10.20.0.7",)),))
    assert select_ansible_host(host, AddressPolicy(private_network="pn2")).address == "10.20.0.7"


def test_une_machine_absente_du_reseau_demande_est_dite_absente() -> None:
    host = _host(private_networks=(NetworkAttachment("pn1", "backend", ipv4=("10.10.0.5",)),))
    selection = select_ansible_host(host, AddressPolicy(private_network="monitoring"))
    assert not selection.found
    assert "monitoring" in selection.source
    assert selection.considered == ("backend",)


def test_un_reseau_sans_adresse_le_dit_autrement_quun_reseau_absent() -> None:
    """Deux échecs distincts : pas sur le réseau, ou dessus sans adresse."""
    host = _host(private_networks=(NetworkAttachment("pn1", "backend"),))
    selection = select_ansible_host(host, AddressPolicy(private_network="backend"))
    assert not selection.found
    assert "aucune adresse" in selection.source
    assert selection.private_network == "backend"


def test_aucune_adresse_est_un_resultat_pas_une_erreur() -> None:
    selection = select_ansible_host(_host(), AddressPolicy())
    assert not selection.found
    assert selection.considered == AddressPolicy().priority


def test_une_famille_inconnue_est_ignoree_pas_devinee() -> None:
    politique = AddressPolicy(priority=("carrier_pigeon", "public_ipv4"))
    assert politique.families() == ("public_ipv4",)


def test_la_selection_sait_sexpliquer() -> None:
    """Le mode debug doit pouvoir répondre à « pourquoi cette IP »."""
    host = _host(
        private_ipv4=("10.10.0.5",),
        private_networks=(NetworkAttachment("pn1", "backend", ipv4=("10.10.0.5",)),),
    )
    texte = select_ansible_host(host, AddressPolicy()).explain("web01")
    assert "10.10.0.5" in texte and "private_ipv4" in texte and "backend" in texte


@pytest.mark.parametrize("famille", ["private_ipv4", "public_ipv4", "private_ipv6", "public_ipv6"])
def test_chaque_famille_est_atteignable(famille: str) -> None:
    host = _host(**{famille: ("adresse",)})
    assert select_ansible_host(host, AddressPolicy(priority=(famille,))).source == famille
