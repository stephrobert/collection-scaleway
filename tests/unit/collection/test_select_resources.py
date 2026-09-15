"""Ce qu'un sélecteur désigne dans une population lue par l'API.

Le pendant de `select_hosts` pour ce qui ne vient pas de l'inventaire. La
grammaire est la même, écrite une fois ; ce qui change d'une population à
l'autre est le vocabulaire : un groupe de nœuds est un pool.
"""

from __future__ import annotations

import pytest

from ansible_collections.stephrobert.scaleway.plugins.filter.select_resources import (
    reboot_target,
    select_resources,
)


def _noeud(nom: str, pool: str = "production", **reste: object) -> dict:
    return {
        "kind": "k8s_node",
        "id": f"id-{nom}",
        "name": nom,
        "zone": "fr-par",
        "state": "ready",
        "pool": pool,
        **reste,
    }


NOEUDS = [
    _noeud("scw-prod-1"),
    _noeud("scw-prod-2"),
    _noeud("scw-bac-1", pool="bac-a-sable"),
]


# ---- Ce qu'un groupe veut dire selon le produit ---------------------------


def test_un_groupe_de_noeuds_est_un_pool() -> None:
    """Un pool groupe des nœuds comme un groupe d'inventaire groupe des machines."""
    designes = select_resources({"group": "production"}, NOEUDS, kind="k8s_node")

    assert [n["name"] for n in designes] == ["scw-prod-1", "scw-prod-2"]


def test_plusieurs_noeuds_designes_ne_sont_pas_une_ambiguite() -> None:
    """C'est le but : une vague porte sur une classe, pas sur une chose."""
    assert len(select_resources({"group": "production"}, NOEUDS, kind="k8s_node")) > 1


def test_un_nom_porte_par_deux_ressources_est_refuse() -> None:
    """Un nom désigne une chose ; rendre la première agirait sur ce que personne
    n'a désigné (ADR-019)."""
    jumeaux = [_noeud("scw-prod-1"), _noeud("scw-prod-1", pool="bac-a-sable")]

    with pytest.raises(Exception, match="n'est pas une identité"):
        select_resources({"name": "scw-prod-1"}, jumeaux, kind="k8s_node")


def test_un_nom_unique_designe_sans_ambiguite() -> None:
    """Le voisin qui ne doit pas bouger."""
    designes = select_resources({"name": "scw-bac-1"}, NOEUDS, kind="k8s_node")

    assert [n["name"] for n in designes] == ["scw-bac-1"]


def test_un_pool_inconnu_ne_designe_rien_sans_echouer() -> None:
    """Ne rien désigner est un fait ; c'est à l'appelant d'en décider."""
    assert select_resources({"group": "absent"}, NOEUDS, kind="k8s_node") == []


# ---- Ce que chaque produit accepte ----------------------------------------


def test_un_noeud_naccepte_pas_les_etiquettes() -> None:
    """Mesuré : `scaleway.k8s.v1.Node` ne porte pas d'étiquettes.

    `scaleway.k8s.v1.Pool` en porte, et faire passer celles du pool pour celles
    du nœud ajouterait un saut que l'utilisateur ne voit pas.
    """
    with pytest.raises(Exception, match="group, name, id"):
        select_resources({"tags": ["role=web"]}, NOEUDS, kind="k8s_node")


def test_une_instance_naccepte_pas_de_groupe() -> None:
    """Hors de l'inventaire, une machine n'a pas de groupe : `select_hosts` l'y trouve."""
    with pytest.raises(Exception, match="name, tags, id"):
        select_resources({"group": "web"}, [], kind="instance")


def test_un_produit_inconnu_est_refuse_avec_les_connus() -> None:
    """Sélectionner au mieux chercherait un champ absent, donc ne désignerait rien."""
    with pytest.raises(Exception, match="k8s_node") as echec:
        select_resources({"name": "x"}, [], kind="elastic_metal")
    assert "aucune table de sélection" in str(echec.value)


def test_des_ressources_qui_ne_sont_pas_une_liste_sont_refusees() -> None:
    with pytest.raises(Exception, match="ressources sont une liste"):
        select_resources({"name": "x"}, "scw-prod-1", kind="k8s_node")


# ---- La forme commune que la vague consomme -------------------------------


def test_une_cible_porte_ce_quil_faut_pour_redemarrer() -> None:
    """`scope` est la zone d'une machine et la région d'un nœud, sous un seul nom."""
    cible = reboot_target(_noeud("scw-prod-1"), kind="k8s_node")

    assert cible == {
        "kind": "k8s_node",
        "scope": "fr-par",
        "id": "id-scw-prod-1",
        "name": "scw-prod-1",
    }


def test_une_ressource_sans_portee_est_refusee() -> None:
    """Redémarrer sans savoir où viserait une ressource que personne n'a désignée."""
    sans = {cle: valeur for cle, valeur in _noeud("scw-prod-1").items() if cle != "zone"}

    with pytest.raises(Exception, match="ne porte pas zone et id"):
        reboot_target(sans, kind="k8s_node")


def test_une_ressource_sans_identite_est_refusee() -> None:
    sans = {cle: valeur for cle, valeur in _noeud("scw-prod-1").items() if cle != "id"}

    with pytest.raises(Exception, match="ne porte pas zone et id"):
        reboot_target(sans, kind="k8s_node")


def test_un_produit_que_ce_role_ne_redemarre_pas_est_refuse() -> None:
    """Un roulement sur ce dont il ne sait pas observer le retour est une temporisation."""
    with pytest.raises(Exception, match="aucune portée connue"):
        reboot_target(_noeud("scw-prod-1"), kind="lb_certificate")
