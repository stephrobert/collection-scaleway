"""La grammaire d'un sélecteur, écrite une fois pour deux populations.

`select_hosts` désigne des hôtes d'inventaire, `audit_exceptions` désigne des
ressources lues par l'API. Les deux validaient la même grammaire, avec les mêmes
refus et deux jeux de messages qui avaient déjà commencé à diverger.

La grammaire se partage ; la résolution ne se partage pas, et c'est correct : un
groupe d'inventaire n'est pas un pool, et un `id` de ressource n'a pas
d'équivalent dans un inventaire.
"""

from __future__ import annotations

import pytest

from ansible_collections.stephrobert.scaleway.plugins.module_utils.selecteur import (
    SelecteurError,
    correspond,
    etiquettes_voulues,
    valider,
)

HOTES = ("group", "name", "tags")
RESSOURCES = ("name", "tags", "id")


def test_un_critere_pose_ressort_avec_sa_valeur() -> None:
    """L'appelant a le critère sous la main et n'a plus à le redéduire.

    C'était le second endroit où les deux implémentations se répétaient.
    """
    assert valider({"group": "web"}, HOTES) == ("group", "web", "all")


def test_les_criteres_acceptes_sont_ceux_de_lappelant() -> None:
    """`id` désigne une ressource et rien dans un inventaire."""
    assert valider({"id": "aaaa"}, RESSOURCES)[0] == "id"
    with pytest.raises(SelecteurError, match="group, name, tags"):
        valider({"id": "aaaa"}, HOTES)


def test_la_combinaison_par_defaut_est_la_plus_etroite() -> None:
    """Pour une opération qui écrit, se tromper du côté sûr touche moins."""
    assert valider({"tags": ["a", "b"]}, HOTES)[2] == "all"


# ---- Les quatre refus -----------------------------------------------------


def test_un_selecteur_qui_nest_pas_un_objet_est_refuse() -> None:
    with pytest.raises(SelecteurError, match="est un objet, pas str"):
        valider("web", HOTES)


def test_une_cle_inconnue_est_refusee_et_les_criteres_sont_nommes() -> None:
    """Une faute de frappe qui ne désigne rien se lit comme un parc vide."""
    with pytest.raises(SelecteurError, match="groupe") as echec:
        valider({"groupe": "web"}, HOTES)
    assert "group, name, tags" in str(echec.value)


def test_un_selecteur_vide_est_refuse() -> None:
    """Ne rien désigner est une décision qui se prend avant d'appeler."""
    with pytest.raises(SelecteurError, match="sélecteur vide"):
        valider({}, HOTES)


def test_deux_criteres_a_la_fois_sont_refuses() -> None:
    """Deux critères posent deux questions, et la réponse dépendrait de l'ordre."""
    with pytest.raises(SelecteurError, match="group, name"):
        valider({"group": "web", "name": "web-1"}, HOTES)


def test_une_combinaison_inconnue_est_refusee() -> None:
    """Sans elle, `tags` ne dit pas s'il faut toutes les étiquettes ou une seule."""
    with pytest.raises(SelecteurError, match="ni all ni any"):
        valider({"tags": ["a"], "match": "peut-être"}, HOTES)


def test_le_contexte_de_lappelant_entre_dans_le_message() -> None:
    """Un message commun sans contexte ne dit pas de quoi il parle."""
    with pytest.raises(SelecteurError, match="le `selector` de l'exception 3"):
        valider("web", RESSOURCES, quoi="le `selector` de l'exception 3")


# ---- Les étiquettes -------------------------------------------------------


def test_des_etiquettes_qui_ne_sont_pas_une_liste_sont_refusees() -> None:
    with pytest.raises(SelecteurError, match="liste non vide"):
        etiquettes_voulues("role=web")


def test_une_liste_detiquettes_vide_est_refusee() -> None:
    """Elle désignerait tout, ce qui est le contraire d'un sélecteur."""
    with pytest.raises(SelecteurError, match="liste non vide"):
        etiquettes_voulues([])


def test_all_exige_toutes_les_etiquettes() -> None:
    assert correspond({"a", "b"}, {"a", "b", "c"}, "all")
    assert not correspond({"a", "b"}, {"a"}, "all")


def test_any_en_exige_une_seule() -> None:
    assert correspond({"a", "b"}, {"a"}, "any")
    assert not correspond({"a", "b"}, {"c"}, "any")
