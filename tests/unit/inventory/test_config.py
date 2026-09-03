"""La configuration : ce qu'elle accepte, ce qu'elle refuse, ce qu'elle hache.

Deux exigences distinctes :

* un nom inconnu est **refusé**, pas ignoré. Ignorer `group_by: [regionn]`
  produirait un inventaire silencieusement différent de celui demandé ;
* la clé de cache couvre tout ce qui change le résultat. Le plugin officiel n'y
  met que le chemin du fichier, donc deux profils partagent un cache.
"""

from __future__ import annotations

import pytest

from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.config import (
    DEFAULT_GROUP_BY,
    DEFAULT_HOSTNAMES,
    ConfigError,
    from_options,
)

PRODUITS = ("instance", "elastic_metal", "apple_silicon")


def _options(**surcharges):
    valeurs = {
        "products": None,
        "zones": None,
        "regions": None,
        "projects": None,
        "organizations": None,
        "hostnames": None,
        "address_priority": None,
        "address": None,
        "require_address": False,
        "group_by": None,
        "tags": None,
        "tags_match": None,
        "states": None,
        "exclude": None,
        "include_raw": False,
        "strict": False,
    }
    valeurs.update(surcharges)
    return valeurs.__getitem__


def test_les_defauts_sont_ceux_documentes() -> None:
    config = from_options(_options(), PRODUITS)
    assert config.products == PRODUITS
    assert config.group_by == DEFAULT_GROUP_BY
    assert config.hostnames == DEFAULT_HOSTNAMES


def test_une_chaine_seule_vaut_une_liste_dun_element() -> None:
    """`zones: fr-par-1` est ce qu'un utilisateur écrit naturellement."""
    assert from_options(_options(zones="fr-par-1"), PRODUITS).zones == ("fr-par-1",)


def test_un_produit_inconnu_est_refuse_avec_la_liste_des_connus() -> None:
    with pytest.raises(ConfigError) as echec:
        from_options(_options(products=["instance", "kubernetes"]), PRODUITS)
    assert "kubernetes" in str(echec.value)
    assert "instance" in str(echec.value)


def test_un_axe_de_groupe_inconnu_est_refuse() -> None:
    with pytest.raises(ConfigError, match="regionn"):
        from_options(_options(group_by=["regionn"]), PRODUITS)


def test_une_famille_dadresse_inconnue_est_refusee() -> None:
    with pytest.raises(ConfigError, match="carrier_pigeon"):
        from_options(_options(address_priority=["carrier_pigeon"]), PRODUITS)


def test_un_tags_match_hors_any_ou_all_est_refuse() -> None:
    with pytest.raises(ConfigError, match="quelques"):
        from_options(_options(tags_match="quelques"), PRODUITS)


def test_le_reseau_prive_se_nomme_par_nom_ou_par_identifiant() -> None:
    par_nom = from_options(_options(address={"private_network": "backend"}), PRODUITS)
    par_id = from_options(_options(address={"private_network_id": "pn-1"}), PRODUITS)
    assert par_nom.address.private_network == "backend"
    assert par_id.address.private_network == "pn-1"


def test_les_exclusions_sont_lues_sous_leur_bloc() -> None:
    config = from_options(_options(exclude={"tags": ["canary"], "states": ["stopped"]}), PRODUITS)
    assert config.filters.exclude_tags == ("canary",)
    assert config.filters.exclude_states == ("stopped",)


def test_deux_configurations_identiques_partagent_leur_cache() -> None:
    empreinte = from_options(_options(), PRODUITS).cache_fingerprint("prod", None)
    assert from_options(_options(), PRODUITS).cache_fingerprint("prod", None) == empreinte


@pytest.mark.parametrize(
    "changement",
    [
        {"products": ["instance"]},
        {"zones": ["fr-par-1"]},
        {"projects": ["proj-1"]},
        {"tags": ["env=prod"]},
        {"tags_match": "all"},
        {"states": ["running"]},
        {"exclude": {"tags": ["canary"]}},
        {"group_by": ["zone"]},
        {"hostnames": ["id"]},
        {"address_priority": ["public_ipv4"]},
        {"address": {"private_network": "backend"}},
        {"include_raw": True},
    ],
)
def test_tout_ce_qui_change_le_resultat_change_la_cle(changement) -> None:
    """Le défaut mesuré sur le plugin officiel : un cache partagé à tort."""
    reference = from_options(_options(), PRODUITS).cache_fingerprint("prod", None)
    variante = from_options(_options(**changement), PRODUITS).cache_fingerprint("prod", None)
    assert variante != reference


def test_le_profil_et_lurl_dapi_entrent_aussi_dans_la_cle() -> None:
    """Deux profils, deux parcs : ils ne doivent jamais partager un inventaire."""
    config = from_options(_options(), PRODUITS)
    assert config.cache_fingerprint("prod", None) != config.cache_fingerprint("staging", None)
    assert config.cache_fingerprint("prod", None) != config.cache_fingerprint(
        "prod", "http://127.0.0.1:8080"
    )


def test_deux_filtrages_differents_ne_partagent_pas_leur_cache() -> None:
    """Le cas concret du défaut mesuré : deux parcs, un seul fichier de cache.

    Ce test double le paramétrage ci-dessus à dessein : une entrée paramétrée
    est une cible fragile pour `/falsify`, qui doit nommer un test précis.
    """
    prod = from_options(_options(tags=["env=prod"]), PRODUITS)
    staging = from_options(_options(tags=["env=staging"]), PRODUITS)
    assert prod.cache_fingerprint("scw", None) != staging.cache_fingerprint("scw", None)


def test_le_mode_strict_entre_dans_la_cle_de_cache() -> None:
    """Sans lui, un inventaire partiel enregistré en mode tolérant était
    resservi à une exécution qui demandait un refus, et `_collect()` n'étant
    pas rejoué, les erreurs ne provoquaient plus rien."""
    tolerant = from_options(_options(strict=False), PRODUITS).cache_fingerprint("scw", None)
    exigeant = from_options(_options(strict=True), PRODUITS).cache_fingerprint("scw", None)
    assert tolerant != exigeant


def test_les_organisations_entrent_dans_la_cle_de_cache() -> None:
    une = from_options(_options(organizations=["org-1"]), PRODUITS).cache_fingerprint("scw", None)
    autre = from_options(_options(organizations=["org-2"]), PRODUITS).cache_fingerprint("scw", None)
    assert une != autre


def test_une_zone_inconnue_est_refusee() -> None:
    """Une faute de frappe donnait zéro zone interrogée, zéro appel, zéro
    avertissement, et un inventaire vide en code 0."""
    with pytest.raises(ConfigError, match="fr-par1"):
        from_options(_options(zones=["fr-par1"]), PRODUITS, ("fr-par-1", "fr-par-2"))


def test_une_zone_connue_passe() -> None:
    config = from_options(_options(zones=["fr-par-1"]), PRODUITS, ("fr-par-1", "fr-par-2"))
    assert config.zones == ("fr-par-1",)


def test_une_source_de_nom_dhote_inconnue_est_refusee() -> None:
    """`hostnames: [nmae]` était accepté, et chaque machine écartée ensuite."""
    with pytest.raises(ConfigError, match="nmae"):
        from_options(_options(hostnames=["nmae"]), PRODUITS)


def test_une_source_qui_lit_un_objet_est_refusee() -> None:
    """`private_networks` rendait un objet là où le type promet une chaîne."""
    with pytest.raises(ConfigError, match="private_networks"):
        from_options(_options(hostnames=["private_networks"]), PRODUITS)


def test_les_sources_par_tag_et_les_alias_restent_acceptes() -> None:
    config = from_options(_options(hostnames=["tag:role", "hostname", "id"]), PRODUITS)
    assert config.hostnames == ("tag:role", "hostname", "id")


def test_deux_comptes_ne_partagent_pas_leur_inventaire_en_cache() -> None:
    """Sans `profile` déclaré, deux clés d'accès différentes produisaient la
    même empreinte, et la seconde exécution recevait le parc de la première."""
    config = from_options(_options(), PRODUITS)
    un = config.cache_fingerprint(None, None, "SCW-COMPTE-A")
    autre = config.cache_fingerprint(None, None, "SCW-COMPTE-B")
    assert un != autre


def test_la_cle_dacces_nentre_jamais_en_clair_dans_lempreinte() -> None:
    config = from_options(_options(), PRODUITS)
    assert "SCW-SECRET" not in config.cache_fingerprint(None, None, "SCW-SECRET")
