"""La couture entre ce qu'un produit nomme et ce qu'une règle demande.

Une politique dont les règles lisent `modification_date` et `public_ips` lit un
objet Instance. Le jour où Elastic Metal aura des modules, il faudrait ou bien
réécrire les règles, ou bien les remplir de conditions par produit, et un
playbook géant de règles par produit est ce que « les règles sont des données »
existe pour éviter (#210).

Ces tests tiennent la traduction, et surtout son refus : normaliser au mieux un
produit inconnu rendrait des champs absents qui se liraient comme des absences.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]
PLUGIN = (
    RACINE
    / "ansible_collections"
    / "stephrobert"
    / "scaleway"
    / "plugins"
    / "filter"
    / "resource_facts.py"
)

#: Une charge utile telle qu'`instance_server_info` la rend, mesurée contre
#: l'émulateur : les noms sont ceux de l'API, pas ceux des règles.
CHARGE = {
    "name": "web-1",
    "zone": "fr-par-1",
    "state": "running",
    "tags": ["role=web", "env=lab"],
    "public_ips": [{"address": "51.15.0.1"}],
    "modification_date": "2026-09-12T11:00:00Z",
    "creation_date": "2026-01-01T00:00:00Z",
    "commercial_type": "DEV1-S",
}


def _module():
    spec = importlib.util.spec_from_file_location("resource_facts", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["resource_facts"] = module
    spec.loader.exec_module(module)
    return module


def test_une_instance_devient_la_forme_que_les_regles_lisent() -> None:
    """Les noms changent, et c'est tout l'intérêt.

    `last_change` dit ce que la règle cherche ; `modification_date` dit ce que
    l'API d'un produit a choisi d'appeler son champ.
    """
    fait = _module().resource_facts([CHARGE], kind="instance")[0]

    assert fait == {
        "kind": "instance",
        "name": "web-1",
        "zone": "fr-par-1",
        "state": "running",
        "tags": ["role=web", "env=lab"],
        "public_addresses": ["51.15.0.1"],
        "last_change": "2026-09-12T11:00:00Z",
    }


def test_la_forme_ne_laisse_passer_aucun_champ_du_produit() -> None:
    """Un champ d'Instance qui traverserait serait une porte ouverte.

    Une règle finirait par le lire, et cesserait de valoir pour les autres
    produits sans que rien ne le dise.
    """
    module = _module()
    fait = module.resource_facts([CHARGE], kind="instance")[0]

    assert set(fait) == set(module.CHAMPS)
    assert "commercial_type" not in fait


def test_une_date_manquante_retombe_sur_la_creation() -> None:
    """Sans date de modification, la création est la seule mesure disponible.

    Ce n'est pas la même chose, et la règle qui la lit le dit à sa façon : elle
    parle de ce qu'elle a pu mesurer, pas de ce qu'elle aurait voulu.
    """
    sans_modification = {
        cle: valeur for cle, valeur in CHARGE.items() if cle != "modification_date"
    }

    assert (
        _module().resource_facts([sans_modification], kind="instance")[0]["last_change"]
        == "2026-01-01T00:00:00Z"
    )


def test_un_produit_inconnu_est_refuse() -> None:
    """Normaliser au mieux rendrait une ressource dont les manques mentent.

    Une machine sans étiquette et une machine dont on ne sait pas lire les
    étiquettes se ressemblent trop pour qu'on les confonde : la première est un
    constat, la seconde est une ignorance.
    """
    with pytest.raises(Exception) as erreur:
        _module().resource_facts([CHARGE], kind="elastic_metal")

    message = str(erreur.value)
    assert "aucun normaliseur pour `elastic_metal`" in message
    assert "instance" in message


def test_le_filtre_est_publie_sous_son_nom() -> None:
    assert "resource_facts" in _module().FilterModule().filters()
