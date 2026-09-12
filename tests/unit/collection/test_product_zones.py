"""Un signal qui crie au loup est un signal que personne ne lit.

Le rapport de parc demandait au Load Balancer des zones que son contrat ne
déclare pas, et les rendait « non mesurées ». Chaque exécution propre en
annonçait deux, alors que `zones_unmeasured` porte l'affirmation la plus
répétée de ce dépôt : rien n'a été mesuré n'est pas rien n'a été trouvé (#222).

Le jour où une zone ne répond vraiment pas, la ligne aurait eu la même allure
que les deux autres.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parents[3]
COLLECTION = RACINE / "ansible_collections" / "stephrobert" / "scaleway"
PLUGIN = COLLECTION / "plugins" / "filter" / "product_zones.py"
CARTE = COLLECTION / "plugins" / "module_utils" / "zones.py"
RAPPORT = COLLECTION / "roles" / "fleet_report" / "tasks" / "main.yml"

DIX = [
    "fr-par-1",
    "fr-par-2",
    "fr-par-3",
    "it-mil-1",
    "nl-ams-1",
    "nl-ams-2",
    "nl-ams-3",
    "pl-waw-1",
    "pl-waw-2",
    "pl-waw-3",
]


def _carte():
    """La carte générée, chargée depuis son fichier."""
    spec = importlib.util.spec_from_file_location("zones_generees", CARTE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module():
    """Le plugin, avec sa carte injectée sous le nom qu'il importe.

    Le plugin importe `ansible_collections...module_utils.zones`, qui n'est pas
    sur le chemin d'un test. Ce qui est mesuré reste le partage, et pas la
    mécanique d'import d'Ansible.
    """
    sys.modules["ansible_collections.stephrobert.scaleway.plugins.module_utils.zones"] = _carte()

    spec = importlib.util.spec_from_file_location("product_zones", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["product_zones"] = module
    spec.loader.exec_module(module)
    return module


def test_la_carte_vient_des_contrats_et_les_produits_different() -> None:
    """Si les deux produits déclaraient les mêmes zones, ce test ne mesurerait rien.

    C'est la différence qui crée le défaut, et une carte où elle aurait disparu
    rendrait la garde verte sur un sujet vide.
    """
    module = _module()
    ZONES = _carte().ZONES

    assert set(ZONES) >= {"instance", "lb"}, "la carte ne couvre plus les deux produits"
    assert ZONES["instance"] != ZONES["lb"], (
        "les deux produits déclarent les mêmes zones : le partage ne mesure plus rien"
    )
    assert module.product_zones(DIX, kind="lb")["not_offered"], (
        "aucune zone non offerte : le cas que #222 corrige a disparu"
    )


def test_une_zone_non_offerte_nest_pas_une_zone_non_mesuree() -> None:
    """C'est toute la correction : deux faits distincts, deux champs."""
    partage = _module().product_zones(DIX, kind="lb")

    assert partage["not_offered"] == ["fr-par-3", "it-mil-1"]
    assert "fr-par-3" not in partage["offered"]
    assert len(partage["offered"]) + len(partage["not_offered"]) == len(DIX)


def test_un_produit_qui_offre_tout_ne_laisse_rien_de_cote() -> None:
    partage = _module().product_zones(DIX, kind="instance")

    assert partage["not_offered"] == []
    assert partage["offered"] == sorted(DIX)


def test_un_produit_sans_carte_est_refuse() -> None:
    """Un produit absent de la carte n'a pas de module, donc rien à interroger.

    Le deviner reviendrait à demander des zones au hasard à une API qui n'a pas
    de client ici.
    """
    with pytest.raises(Exception) as erreur:
        _module().product_zones(DIX, kind="rdb")

    assert "aucune zone connue pour `rdb`" in str(erreur.value)


def test_le_rapport_demande_a_chaque_produit_ce_quil_offre() -> None:
    """La garde vise le rôle : une boucle qui reprendrait la liste brute
    ferait revenir les deux fausses alertes sans que rien ne le dise."""
    taches = yaml.safe_load(RAPPORT.read_text(encoding="utf-8"))
    boucles = [
        str(tache.get("loop", ""))
        for tache in taches
        if str(tache.get("name", "")).startswith("Ask each zone")
    ]
    assert len(boucles) == 2, f"les deux sondes ne sont plus reconnues : {boucles}"

    for boucle in boucles:
        assert ".offered" in boucle, (
            f"une sonde boucle sur `{boucle}` : elle demandera à un produit des "
            "zones que son contrat ne déclare pas"
        )
