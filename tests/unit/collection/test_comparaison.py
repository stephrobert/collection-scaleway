"""Un champ que l'API réordonne ne doit plus faire rendre `changed` à chaque fois.

Le runtime comparait par égalité stricte, et il le disait lui-même :

    demandé            rendu par l'API
    tags:              tags:
      - production       - web
      - web              - production

    égalité stricte  -> changed, à chaque exécution
    comparaison SET  -> unchanged

Un module qui rend `changed` à chaque exécution n'est pas idempotent, quoi
qu'affiche `changed`, et il devient inutilisable dans un handler.

Ces tests portent sur la fonction de comparaison du runtime. Aucun override
`set` n'est posé sur les contrats réels : rien n'a été mesuré qui le
justifierait, et le poser « au cas où » ferait taire un `changed` qui a
peut-être raison. Le mécanisme existe, et la première observation l'emploiera.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

    return scaleway


# --- le cas d'école --------------------------------------------------------


def test_des_tags_reordonnes_ne_sont_pas_un_changement(runtime: Any) -> None:
    """Le défaut mesuré, et la raison d'être de toute cette couche."""
    assert runtime._identique("set", ["production", "web"], ["web", "production"]) is True


def test_en_egalite_stricte_les_memes_tags_sont_un_changement(runtime: Any) -> None:
    """Le contre-exemple : sans lui, le test précédent passerait aussi sur une
    fonction qui rendrait toujours `True`."""
    assert runtime._identique("scalar", ["production", "web"], ["web", "production"]) is False


def test_un_tag_en_plus_reste_un_changement(runtime: Any) -> None:
    """`set` ne doit pas devenir « ne compare rien ».

    Une comparaison qui tairait un ajout serait pire que l'égalité stricte : le
    module annoncerait `ok` sur un état qu'il n'a pas écrit.
    """
    assert runtime._identique("set", ["production", "web"], ["web"]) is False


def test_un_doublon_nest_pas_absorbe(runtime: Any) -> None:
    """Un vrai `set` dirait que `[a, a, b]` vaut `[a, b]`, et c'est faux.

    L'un porte deux tags, l'autre un. Le tri conserve les multiplicités.
    """
    assert runtime._identique("set", ["a", "a", "b"], ["a", "b"]) is False


def test_des_elements_non_triables_entre_eux_se_comparent_quand_meme(runtime: Any) -> None:
    """Un tableau de dictionnaires n'est pas triable par `<`.

    Trier sur la représentation est stable et suffit à comparer deux
    collections ; lever ici ferait échouer un module sur une donnée valide.
    """
    gauche = [{"id": "b"}, {"id": "a"}]
    droite = [{"id": "a"}, {"id": "b"}]

    assert runtime._identique("set", gauche, droite) is True


# --- les autres stratégies -------------------------------------------------


def test_lordre_compte_quand_le_champ_le_demande(runtime: Any) -> None:
    """`ordered_list` est le repli d'un tableau, et il garde l'ordre.

    Adopter `set` par défaut ferait taire un `changed` qui a peut-être raison,
    et un module qui tait un changement réel est pire qu'un module qui en
    annonce un de trop.
    """
    assert runtime._identique("ordered_list", ["a", "b"], ["b", "a"]) is False
    assert runtime._identique("ordered_list", ["a", "b"], ["a", "b"]) is True


def test_une_casse_differente_nest_pas_un_changement_si_le_champ_le_dit(runtime: Any) -> None:
    assert runtime._identique("normalized_string", "Production", " production ") is True
    assert runtime._identique("normalized_string", "production", "staging") is False


def test_un_objet_enrichi_par_lapi_nest_pas_un_changement(runtime: Any) -> None:
    """L'API rend ce qu'on a posé, plus ce qu'elle ajoute.

    Comparer les deux objets entiers conclut « différent » à chaque exécution
    sur des champs que personne n'a demandés.
    """
    demande = {"uri": "https://example.com/hook"}
    rendu = {"uri": "https://example.com/hook", "id": "abc", "created_at": "2026-01-01"}

    assert runtime._identique("normalized_object", demande, rendu) is True
    assert runtime._identique("normalized_object", demande, {"uri": "autre", "id": "abc"}) is False


def test_une_valeur_absente_se_compare_comme_une_liste_vide(runtime: Any) -> None:
    """L'API rend `null` là où la demande porte une liste vide, et inversement."""
    assert runtime._identique("ordered_list", [], None) is True
    assert runtime._identique("set", None, []) is True


# --- ce que le runtime refuse ----------------------------------------------


def test_une_strategie_inconnue_fait_echouer_le_module(runtime: Any) -> None:
    """Retomber en silence sur l'égalité stricte reproduirait le défaut.

    Le générateur et le runtime évoluent ensemble : un module produit par un
    générateur plus récent doit le dire, pas comparer autrement que ce qu'il
    croit.
    """
    with pytest.raises(ValueError) as erreur:
        runtime._identique("comme_je_veux", "a", "a")

    assert "inconnue de ce runtime" in str(erreur.value)


def test_un_module_sans_table_compare_strictement(runtime: Any) -> None:
    """Un module d'une version antérieure n'en porte pas.

    Le repli est l'égalité stricte, qui est le comportement le plus prudent, et
    surtout celui qu'il avait déjà.
    """
    spec = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetWidget", method="GET", path="/w/{id}", path_params=("id",), query_params=()
        ),
        update_operation=runtime.Operation(
            id="UpdateWidget", method="PUT", path="/w/{id}", path_params=("id",), query_params=()
        ),
        managed_params=("tags",),
    )

    assert dict(spec.comparisons) == {}
