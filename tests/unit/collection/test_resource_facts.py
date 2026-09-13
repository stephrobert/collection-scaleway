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
    "id": "b20294e8-d0b9-471e-a78f-bbce79e7ca74",
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
        "id": "b20294e8-d0b9-471e-a78f-bbce79e7ca74",
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


#: Un load balancer tel que `lb_load_balancer_info` le rend. Les trois écarts de
#: vocabulaire sont mesurés sur le contrat : `status` et non `state`, les
#: adresses sous `ip[].ip_address`, et `updated_at` là où Instance dit
#: `modification_date`.
CHARGE_LB = {
    "id": "9f1d0a3c-1111-4222-8333-444455556666",
    "name": "api-prod",
    "zone": "fr-par-1",
    "status": "ready",
    "tags": ["env=prod"],
    "ip": [{"id": "aaaa", "ip_address": "51.15.0.9"}],
    "updated_at": "2026-09-13T06:00:00Z",
    "created_at": "2026-01-01T00:00:00Z",
    "type": "LB-S",
    "backend_count": 2,
}


def test_un_load_balancer_entre_dans_la_meme_forme() -> None:
    """Le produit nomme autrement, la règle ne le sait pas.

    Sans ce normaliseur, un instantané ne porterait que des machines, et le
    diff annoncerait un parc amputé de ses load balancers sans le dire.
    """
    fait = _module().resource_facts([CHARGE_LB], kind="lb")[0]

    assert fait == {
        "kind": "lb",
        "id": "9f1d0a3c-1111-4222-8333-444455556666",
        "name": "api-prod",
        "zone": "fr-par-1",
        "state": "ready",
        "tags": ["env=prod"],
        "public_addresses": ["51.15.0.9"],
        "last_change": "2026-09-13T06:00:00Z",
    }


def test_le_load_balancer_ne_laisse_passer_aucun_champ_du_produit() -> None:
    """Le même voisin que pour Instance : `type` et `backend_count` restent dehors."""
    module = _module()
    fait = module.resource_facts([CHARGE_LB], kind="lb")[0]

    assert set(fait) == set(module.CHAMPS)


def test_une_ressource_sans_identifiant_est_refusee() -> None:
    """Mesuré sur le compte réel : le nom n'est pas une identité.

    Deux machines peuvent porter le même nom dans une zone, et les mentions
    d'unicité du contrat Instance portent toutes sur un identifiant. Une
    ressource sans `id` entrerait dans un instantané que rien ne pourrait
    comparer : le diff la verrait apparaître puis disparaître à chaque run.
    """
    module = _module()
    sans_id = {cle: valeur for cle, valeur in CHARGE.items() if cle != "id"}

    with pytest.raises(Exception, match="sans identifiant"):
        module.resource_facts([sans_id], kind="instance")


def test_une_charge_qui_porte_un_identifiant_vide_est_refusee() -> None:
    """La chaîne vide est un identifiant absent qui a l'air présent.

    C'est la forme que prend une charge utile tronquée, et la distinguer de
    l'absence coûterait une règle de plus pour aucun gain : ni l'une ni l'autre
    ne permet de reconnaître la ressource demain.
    """
    module = _module()

    with pytest.raises(Exception, match="sans identifiant"):
        module.resource_facts([{**CHARGE, "id": ""}], kind="instance")
