"""Ce qui doit rester vrai de toute entrée, et pas seulement de celles qu'on a écrites.

Le générateur traduit : d'un contrat OpenAPI il tire des noms, des types et des
phrases publiées. Les cas qu'un mainteneur pense à écrire sont un sous-ensemble
de ceux que l'amont peut produire, et Scaleway a ajouté 453 méthodes en douze
mois sans demander l'avis de ce dépôt.

Ces tests énoncent donc des **propriétés** plutôt que des exemples, et laissent
Hypothesis chercher le contre-exemple. Ce qu'il apporte en plus d'une boucle
écrite à la main : il réduit ce qu'il trouve à sa plus petite forme, ce qui est
la moitié du travail de diagnostic.

Chaque propriété ci-dessous protège un défaut déjà rencontré dans ce dépôt, ou
la classe à laquelle il appartenait.
"""

from __future__ import annotations

import re

from hypothesis import given
from hypothesis import strategies as st

from generator.ansible.models import (
    ACRONYMES,
    UNDOCUMENTED,
    AnsibleOption,
    _example_value,
    _lisible,
    _reformulation,
    _sans_la_couche_http,
    _sans_les_actions_refusees,
)
from generator.parser.naming import pluralize_phrase, snake_case

#: Un identifiant tel qu'un contrat en porte : lettres, chiffres, séparateurs.
IDENTIFIANT = st.from_regex(r"\A[a-z][a-z0-9_]{0,30}\Z", fullmatch=True)

#: Un nom de champ, éventuellement en CamelCase comme les schémas Scaleway.
NOM_DE_CHAMP = st.one_of(
    IDENTIFIANT, st.from_regex(r"\A[A-Za-z][A-Za-z0-9]{0,20}\Z", fullmatch=True)
)


@given(IDENTIFIANT)
def test_le_passage_en_snake_case_est_idempotent(nom: str) -> None:
    """Le repasser ne doit rien changer : sinon l'ordre des appels compte.

    Une dérivation qui change de résultat selon le nombre de fois qu'on
    l'applique casse le déterminisme de la génération, que le golden mesure.
    """
    une_fois = snake_case(nom)
    assert snake_case(une_fois) == une_fois


@given(IDENTIFIANT)
def test_la_pluralisation_garde_la_tete_de_lexpression(nom: str) -> None:
    """`server_type` -> `server types` : c'est le dernier mot qui porte le nombre.

    Perdre un mot de tête renommerait la ressource, et c'est le défaut qui a
    déjà coûté deux modules pour une même chose.
    """
    mots = [m for m in nom.split("_") if m]
    pluriel = pluralize_phrase(nom).split(" ")
    assert pluriel[:-1] == mots[:-1]


@given(st.lists(IDENTIFIANT, min_size=1, max_size=6))
def test_les_abreviations_ne_changent_que_de_casse(mots: list[str]) -> None:
    """`_lisible` met en capitales, elle ne réécrit pas.

    Le jour où quelqu'un ajoutera une entrée fautive à la table, cette
    propriété le dira : une valeur qui n'est pas la casse de sa clé n'est plus
    une abréviation, c'est une traduction.
    """
    phrase = " ".join(mots)
    rendu = _lisible(phrase)
    assert rendu.split(" ") == [ACRONYMES.get(m, m) for m in mots]
    assert rendu.casefold() == phrase.casefold()


@given(NOM_DE_CHAMP, IDENTIFIANT)
def test_une_reformulation_est_une_phrase_ou_rien(ressource: str, champ: str) -> None:
    """Jamais une chaîne vide, jamais sans point final.

    Une description vide passe `ansible-test sanity` et publie un champ muet,
    ce qui est exactement ce que la 0.2.0 a fait cent fois.
    """
    phrase = _reformulation(ressource, champ)
    if phrase is not None:
        assert phrase.strip() == phrase
        assert phrase.endswith(".")
        assert len(phrase) > 1


@given(
    st.lists(IDENTIFIANT, min_size=0, max_size=6, unique=True),
    st.lists(IDENTIFIANT, min_size=0, max_size=6, unique=True),
)
def test_le_filtre_dactions_ninvente_aucune_puce(gardees: list[str], autres: list[str]) -> None:
    """Les puces qui sortent sont un sous-ensemble de celles qui entrent.

    Le défaut mesuré allait dans l'autre sens, le `RETURN` promettait
    `terminate` sur un module qui le refuse ; la propriété qui l'empêche est
    qu'aucune puce ne peut apparaître.
    """
    puces = {*gardees, *autres}
    texte = "\n".join(f"* `{nom}`: ce que ça fait." for nom in sorted(puces))
    rendu = _sans_les_actions_refusees(texte, tuple(gardees))
    sorties = set(re.findall(r"\* `([a-z0-9_]+)`", rendu))
    assert sorties <= puces
    assert sorties <= set(gardees)


@given(st.text(max_size=200))
def test_le_nettoyage_http_ne_rallonge_jamais_le_texte(texte: str) -> None:
    """C'est un nettoyage, pas une réécriture.

    Un texte qui grandit est un texte auquel le générateur a ajouté quelque
    chose, et ce quelque chose ne viendrait pas du contrat.
    """
    assert len(_sans_la_couche_http(texte)) <= len(texte.strip())


@given(st.lists(IDENTIFIANT, min_size=1, max_size=5, unique=True), IDENTIFIANT)
def test_une_valeur_dexemple_denum_est_toujours_une_valeur_exposee(
    choix: list[str], nom: str
) -> None:
    """Un exemple qui montre une valeur que le module refuse ne se copie pas.

    Et il ne montre jamais la sentinelle `unknown_*` du protobuf, que l'API
    refuse : « copiable et faux » est pire qu'un trou.
    """
    option = AnsibleOption(
        name=nom, type="str", required=True, description=("x",), choices=tuple(choix)
    )
    valeur = _example_value(option)
    assert valeur in choix
    if any(not c.startswith("unknown") for c in choix):
        assert not str(valeur).startswith("unknown")


@given(IDENTIFIANT)
def test_une_valeur_dexemple_nest_jamais_le_repli_documentaire(nom: str) -> None:
    """Le repli est une phrase de documentation, pas une valeur.

    La propriété est faible et elle a sa raison d'être : les deux mécanismes se
    sont déjà croisés, quand la charge utile d'une action a repris la ligne de
    documentation brute.
    """
    option = AnsibleOption(name=nom, type="str", required=True, description=("x",))
    assert _example_value(option) != UNDOCUMENTED
