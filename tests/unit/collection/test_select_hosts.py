"""Quatre grammaires pour une seule question : de quoi parle-t-on ?

Un groupe pour les enchaînements, un nom pour le lookup, un identifiant pour les
modules. Un rôle appelé depuis le playbook de quelqu'un d'autre doit accepter la
même réponse que les autres (#208).

Ces tests portent sur ce que le sélecteur **refuse**, parce qu'une grammaire qui
accepte tout ne dit rien. Chacun de ces refus existait déjà ailleurs, mesuré :
ici ils valent pour les trois formes à la fois.
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
    / "select_hosts.py"
)

#: Un parc de laboratoire : deux machines de production, une de préproduction,
#: et deux qui portent le même nom dans deux zones, parce que c'est le cas qui
#: doit se refuser plutôt que se trancher.
HOSTVARS = {
    "web-1": {"scaleway_name": "web-1", "scaleway_tags": ["production", "web"]},
    "web-2": {"scaleway_name": "web-2", "scaleway_tags": ["production", "web"]},
    "db-1": {"scaleway_name": "db-1", "scaleway_tags": ["production", "db"]},
    "preprod-1": {"scaleway_name": "preprod-1", "scaleway_tags": ["preprod", "web"]},
    "jumeau-a": {"scaleway_name": "jumeau", "scaleway_tags": ["production"]},
    "jumeau-b": {"scaleway_name": "jumeau", "scaleway_tags": ["production"]},
}
GROUPS = {"scw_tag_production": ["web-1", "web-2", "db-1"], "vide": []}


def _module():
    spec = importlib.util.spec_from_file_location("select_hosts", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["select_hosts"] = module
    spec.loader.exec_module(module)
    return module


def _choisir(selecteur):
    return _module().select_hosts(selecteur, groups=GROUPS, hostvars=HOSTVARS)


# --- les trois formes -----------------------------------------------------


def test_un_groupe_designe_ses_machines() -> None:
    assert _choisir({"group": "scw_tag_production"}) == ["db-1", "web-1", "web-2"]


def test_un_nom_designe_une_machine_exactement() -> None:
    """Le filtre `name` de l'API correspond par préfixe, pas celui-ci.

    `server1` rend aussi `server100` côté Scaleway, ce que le contrat énonce.
    Ici la comparaison est locale et exacte, donc `web-1` ne rend pas `web-2`.
    """
    assert _choisir({"name": "web-1"}) == ["web-1"]


def test_des_etiquettes_designent_celles_qui_les_portent_toutes() -> None:
    """`all` est le défaut : la sélection la plus étroite.

    Pour une opération qui écrit, se tromper du côté sûr veut dire toucher
    moins de machines, jamais plus.
    """
    assert _choisir({"tags": ["production", "web"]}) == ["web-1", "web-2"]


def test_une_seule_etiquette_suffit_quand_on_le_demande() -> None:
    assert _choisir({"tags": ["db", "web"], "match": "any"}) == [
        "db-1",
        "preprod-1",
        "web-1",
        "web-2",
    ]


# --- ce que le sélecteur refuse -------------------------------------------


def test_un_nom_ambigu_est_refuse_et_nomme_les_candidats() -> None:
    """Rendre le premier ferait agir sur une ressource que personne n'a désignée.

    C'est ADR-019, appliquée à l'inventaire plutôt qu'à l'API.
    """
    with pytest.raises(Exception) as erreur:
        _choisir({"name": "jumeau"})

    assert "jumeau-a, jumeau-b" in str(erreur.value)
    assert "ADR-019" in str(erreur.value)


def test_une_cle_inconnue_est_refusee() -> None:
    """`tag` au lieu de `tags` ne doit pas sélectionner zéro machine en silence.

    Une sélection vide et une faute de frappe se ressemblent trop pour qu'on
    les confonde : la première est un fait, la seconde est un défaut.
    """
    with pytest.raises(Exception) as erreur:
        _choisir({"tag": "production"})

    assert "inconnue(s) : tag" in str(erreur.value)


def test_deux_criteres_a_la_fois_sont_refuses() -> None:
    """Deux critères posent deux questions, et la réponse dépendrait de l'ordre."""
    with pytest.raises(Exception) as erreur:
        _choisir({"group": "scw_tag_production", "name": "web-1"})

    assert "à la fois" in str(erreur.value)


def test_un_selecteur_vide_est_refuse() -> None:
    """Ne rien désigner est une décision, pas un sélecteur qui ne désigne rien."""
    with pytest.raises(Exception) as erreur:
        _choisir({})

    assert "sélecteur vide" in str(erreur.value)


def test_une_combinaison_inconnue_est_refusee() -> None:
    """Sans `match`, `tags` ne dit pas s'il faut toutes les étiquettes ou une."""
    with pytest.raises(Exception) as erreur:
        _choisir({"tags": ["production"], "match": "peut-etre"})

    assert "ni all ni any" in str(erreur.value)


# --- ce qu'il laisse passer, et qui n'est pas une erreur ------------------


def test_un_groupe_vide_rend_une_liste_vide() -> None:
    """Le refus appartient à l'opération, pas au sélecteur.

    C'est elle qui sait si une sélection vide est un silence acceptable ou un
    planificateur qui échoue à 20:00 sans que personne ne le sache, et son
    message nomme les groupes que l'inventaire a construits.
    """
    assert _choisir({"group": "vide"}) == []
    assert _choisir({"name": "absente"}) == []


def test_le_filtre_est_publie_sous_son_nom() -> None:
    assert "select_hosts" in _module().FilterModule().filters()
