"""Ce que la navigation du site doit dire, et ce que ce contrôle ne juge pas.

Le site agrégeait trois documentations dans un seul menu sans annoncer laquelle
sert à quoi, et ouvrait sur l'architecture du générateur. Quelqu'un qui venait
d'installer la collection tombait dans le pipeline OpenAPI (#164).

Ce contrôle ne juge pas le goût : un ratio de pages avec un seuil serait un
nombre inventé. Il vérifie des faits binaires, et ces tests portent sur eux.
"""

from __future__ import annotations

import navigation
import pytest

CONF = 'language = "en"\n'

INDEX = """\
# collection-scaleway

Two paths.

**Use the collection**
: install and operate.

**Build the collection**
: the pipeline.

```{toctree}
:caption: Use the collection
:maxdepth: 2

guides/using-the-collection
guides/dynamic-inventory
```

```{toctree}
:caption: Decisions
:maxdepth: 1

adr/index
```
"""


def test_une_navigation_conforme_ne_dit_rien() -> None:
    assert navigation.refus(INDEX, CONF) == []


def test_lusage_doit_venir_en_premier() -> None:
    """Le défaut d'origine : la première section était « Understand ».

    L'ordre n'est pas une préférence de mise en page, c'est le parcours qu'un
    lecteur suit sans le choisir.
    """
    inverse = INDEX.replace(":caption: Use the collection", ":caption: Understand")

    manques = navigation.refus(inverse, CONF)

    assert any("première section" in ligne for ligne in manques)


def test_la_page_dusage_doit_etre_servie() -> None:
    """Une section d'usage qui ne sert pas le README ne sert rien.

    C'est le cas exact d'avant : la section existait, et ne portait que le
    guide de l'inventaire dynamique.
    """
    sans = INDEX.replace("guides/using-the-collection\n", "")

    manques = navigation.refus(sans, CONF)

    assert any("README" in ligne for ligne in manques)


def test_la_page_daccueil_doit_nommer_ses_deux_parcours() -> None:
    """Sans eux, le site n'annonce pas à quoi il sert, ce qui était le constat."""
    muette = INDEX.replace("**Build the collection**", "**Autre chose**")

    manques = navigation.refus(muette, CONF)

    assert any("deux parcours" in ligne for ligne in manques)


def test_le_site_publie_est_en_anglais() -> None:
    """La frontière de langue du dépôt est ce qui est publié.

    Laisser `fr` mettait « Rechercher docs » autour d'un contenu anglais.
    """
    manques = navigation.refus(INDEX, 'language = "fr"\n')

    assert any("anglais" in ligne for ligne in manques)


def test_une_navigation_sans_toctree_est_une_erreur_pas_un_succes() -> None:
    """Un contrôle qui ne lit rien rend vert sur n'importe quoi."""
    with pytest.raises(navigation.NavigationError, match="aucune `toctree`"):
        navigation.refus("# Titre seul\n", CONF)


def test_la_navigation_du_depot_est_conforme() -> None:
    """Le seul test du fichier qui regarde le dépôt, et c'est voulu."""
    assert (
        navigation.refus(
            navigation.INDEX.read_text(encoding="utf-8"),
            navigation.CONF.read_text(encoding="utf-8"),
        )
        == []
    )


def test_la_reference_ouvre_sur_ce_qui_ordonne() -> None:
    """`antsibull` rend les modules à plat, par ordre alphabétique.

    La section « Reference » doit ouvrir sur la page qui les groupe, pas sur
    cette liste : c'est elle qu'un lecteur voit en premier.
    """
    avec = (
        INDEX
        + """
```{toctree}
:caption: Reference
:maxdepth: 2

guides/module-reference
collections/stephrobert/scaleway/index
```
"""
    )
    assert navigation.refus(avec, CONF) == []

    sans = avec.replace("guides/module-reference\n", "")
    manques = navigation.refus(sans, CONF)

    assert any("Reference" in ligne for ligne in manques)
