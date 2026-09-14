"""Deux options de leur inventaire, pour qu'on ne perde rien en venant.

Le plugin d'inventaire est le seul endroit où les deux collections se marchent
dessus. Mesuré sur `scaleway.scaleway` 2.7.2, deux de leurs options nous
manquaient, et leur sémantique a été **lue dans leur code** plutôt que déduite
de leur nom : un alias qui filtre autrement sous le même nom est pire que pas
d'alias.
"""

from __future__ import annotations

import pytest

from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory import config


def _reglages(**options: object):
    defauts = {
        "products": ["instance"],
        "zones": [],
        "regions": [],
        "projects": [],
        "organizations": [],
        "hostnames": [],
        "address": {},
        "require_address": False,
        "group_by": [],
        "tags": [],
        "tags_match": "any",
        "states": [],
        "state": [],
        "exclude": {},
        "include_raw": False,
        "strict": False,
        "variables": {},
    }
    defauts.update(options)
    return config.from_options(defauts.get, known_products=("instance", "elastic_metal"))


# ---- `state`, leur nom pour notre idée ------------------------------------


def test_leur_nom_filtre_comme_le_notre() -> None:
    """Un fichier écrit pour eux se lit ici sans être réécrit."""
    assert _reglages(state=["stopped"]).filters.states == ("stopped",)


def test_notre_nom_lemporte_quand_les_deux_sont_donnes() -> None:
    """Deux noms pour une chose se contredisent un jour ; celui d'ici tranche."""
    reglages = _reglages(states=["running"], state=["stopped"])

    assert reglages.filters.states == ("running",)


def test_sans_ni_lun_ni_lautre_rien_nest_filtre() -> None:
    """**Leur défaut n'est pas repris.**

    Mesuré : leur `state` vaut `[running]` par défaut, si bien que leur
    inventaire cache les machines arrêtées sans le dire. Le reprendre ferait
    disparaître des machines des inventaires d'ici.
    """
    assert _reglages().filters.states == ()


# ---- `variables`, et le refus qui les sépare ------------------------------


def test_une_correspondance_est_traduite_vers_nos_noms() -> None:
    """`hostname`, `vpc_ipv4` et `vpc_ipv6` sont leurs noms pour trois des nôtres."""
    table = _reglages(variables={"ansible_host": "public_ipv4", "nom": "hostname"}).variables

    assert table == {"ansible_host": "public_ipv4", "nom": "name"}


def test_une_source_inconnue_est_refusee_et_non_sautee() -> None:
    """**Le seul écart délibéré avec eux, et il est mesuré.**

    Leur plugin ignore l'hôte entier quand la source manque. Une faute de frappe
    y vide l'inventaire, l'avertissement se noie, et un playbook joué dessus ne
    touche rien et sort vert.
    """
    with pytest.raises(Exception, match="public_dns"):
        _reglages(variables={"ansible_host": "public_dns"})


def test_le_refus_nomme_les_sources_possibles() -> None:
    """Un refus qui ne dit pas quoi écrire à la place est une porte fermée."""
    with pytest.raises(Exception, match="private_ipv4"):
        _reglages(variables={"x": "inventee"})


def test_une_correspondance_qui_nen_est_pas_une_est_refusee() -> None:
    with pytest.raises(Exception, match="table"):
        _reglages(variables=["ansible_host"])


def test_sans_correspondance_rien_nest_pose_en_plus() -> None:
    assert _reglages().variables == {}


# ---- Les deux listes qui ne doivent pas diverger --------------------------


def test_les_sources_declarees_sont_celles_que_le_plugin_pose() -> None:
    """Une liste recopiée finit par ne plus correspondre.

    `config.py` ne connaît pas le plugin, et l'inverse serait une dépendance à
    l'envers : le contrôle rapproche donc les deux, lu dans le code plutôt que
    recopié à côté.
    """
    import ast
    from pathlib import Path

    collection = Path(config.__file__).resolve().parents[3]
    source = ast.parse(
        (collection / "plugins" / "inventory" / "compute.py").read_text(encoding="utf-8")
    )
    fonction = next(
        n
        for n in ast.walk(source)
        if isinstance(n, ast.FunctionDef) and n.name == "_host_variables"
    )
    posees = {
        cle.value.removeprefix("scaleway_")
        for n in ast.walk(fonction)
        if isinstance(n, ast.Dict)
        for cle in n.keys
        if isinstance(cle, ast.Constant) and str(cle.value).startswith("scaleway_")
    }

    assert posees == set(config.VARIABLES_POSEES)
