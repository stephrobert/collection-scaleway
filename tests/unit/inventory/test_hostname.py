"""Le nom d'hôte, et surtout ce qui se passe quand deux machines le partagent.

La collision est le défaut le plus coûteux du plugin officiel : la seconde
machine écrase la première dans l'inventaire, sans message. Ces tests exigent
que la collision soit résolue **et** dite.
"""

from __future__ import annotations

from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.hostname import (
    assign_hostnames,
    pick_hostname,
    resolve_source,
)
from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.models import (
    InventoryHost,
)


def _host(id_: str, **champs) -> InventoryHost:
    return InventoryHost(id=id_, product="instance", **champs)


def test_la_premiere_source_disponible_gagne() -> None:
    host = _host("i-1", name="web01")
    assert pick_hostname(host, ("name", "id")) == ("web01", "name")


def test_une_source_vide_est_sautee_pas_retenue() -> None:
    """Un nom vide n'est pas un nom : sinon l'inventaire contient une clé ''."""
    host = _host("i-1", name="")
    assert pick_hostname(host, ("name", "id")) == ("i-1", "id")


def test_les_noms_du_plugin_officiel_restent_compris() -> None:
    """Une configuration existante ne doit pas casser à la migration."""
    host = _host("i-1", name="web01", private_ipv4=("10.0.0.5",))
    assert resolve_source(host, "hostname") == "web01"
    assert resolve_source(host, "vpc_ipv4") == "10.0.0.5"


def test_un_tag_peut_nommer_la_machine() -> None:
    host = _host("i-1", tags=("env=prod", "role=web"))
    assert resolve_source(host, "tag:role") == "web"


def test_un_tag_absent_ne_donne_pas_de_nom() -> None:
    assert resolve_source(_host("i-1", tags=("env=prod",)), "tag:role") is None


def test_un_tag_sans_valeur_ne_donne_pas_de_nom() -> None:
    """`role=` ne nomme rien : mieux vaut passer à la source suivante."""
    assert resolve_source(_host("i-1", tags=("role=",)), "tag:role") is None


def test_deux_machines_du_meme_nom_ne_secrasent_pas() -> None:
    hosts = (
        _host("i-1", name="web01", zone="fr-par-1"),
        _host("i-2", name="web01", zone="fr-par-2"),
    )
    attribues, avertissements = assign_hostnames(hosts, ("name",))

    noms = [nom for _, nom in attribues]
    assert noms == ["web01", "web01_fr-par-2"]
    assert len(set(noms)) == 2
    assert any("i-2" in texte for texte in avertissements)


def test_une_collision_dans_la_meme_zone_descend_jusqua_lidentifiant() -> None:
    hosts = (
        _host("i-1", name="web01", zone="fr-par-1"),
        _host("i-2", name="web01", zone="fr-par-1"),
        _host("i-3", name="web01", zone="fr-par-1"),
    )
    attribues, _ = assign_hostnames(hosts, ("name",))
    noms = [nom for _, nom in attribues]
    assert noms == ["web01", "web01_fr-par-1", "web01_i-3"]
    assert len(set(noms)) == 3


def test_la_desambiguisation_est_stable_dune_execution_a_lautre() -> None:
    hosts = tuple(_host(f"i-{i}", name="web01", zone="fr-par-1") for i in range(5))
    premier, _ = assign_hostnames(hosts, ("name",))
    second, _ = assign_hostnames(hosts, ("name",))
    assert [n for _, n in premier] == [n for _, n in second]


def test_une_machine_sans_nom_est_ecartee_avec_une_raison() -> None:
    """Écartée, mais dite : c'est la règle « rien ne disparaît en silence »."""
    attribues, avertissements = assign_hostnames((_host("i-1"),), ("name",))
    assert attribues == ()
    assert len(avertissements) == 1
    assert "i-1" in avertissements[0]
