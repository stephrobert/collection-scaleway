"""Une documentation générée tient dans la ligne qu'`ansible-test sanity` accepte.

PyYAML ne coupe jamais à l'intérieur d'un mot : il coupe à l'espace suivant. Une
description qui porte une URL de plus de cent caractères au milieu d'une phrase
produisait donc une ligne de près de deux cents caractères, que le sanity
refuse. Le dépôt n'a aucune exemption de sanity, et en introduire une pour un
défaut de mise en forme serait un recul.
"""

from __future__ import annotations

import pytest

from generator.renderer.modules import LIGNE_MAXIMALE, RenderError, _yaml_block

#: L'URL du contrat Kubernetes qui a déclenché le cas, raccourcie de ce qui
#: n'apporte rien : ce qui compte est qu'elle soit un seul mot très long.
URL = "https://www.scaleway.com/en/docs/console/account/reference-content/scaleway-network-information/#ip-ranges-used-by-scaleway"


def test_une_url_longue_ne_depasse_pas_la_ligne_du_sanity() -> None:
    """Le cas mesuré, et la seule propriété qui compte."""
    rendu = _yaml_block(
        {"description": [f"Allow access to cluster from all Scaleway ranges as defined in {URL}."]}
    )

    assert max(len(ligne) for ligne in rendu.splitlines()) <= LIGNE_MAXIMALE


def test_une_description_courte_garde_la_largeur_confortable() -> None:
    """Le voisin qui ne doit pas bouger : on ne reflue pas tout le monde.

    Réduire la largeur pour tout le monde reflouerait chaque description de
    chaque module pour un cas, et le diff de régénération ne se lirait plus.
    """
    phrase = "Une phrase ordinaire, faite de mots ordinaires, sans aucun jeton très long."
    rendu = _yaml_block({"description": [phrase]})

    assert max(len(ligne) for ligne in rendu.splitlines()) <= LIGNE_MAXIMALE
    assert len(rendu.splitlines()) <= 3


def test_un_mot_plus_long_que_la_ligne_est_refuse() -> None:
    """Le replier le couperait : le dire vaut mieux que produire l'infaisable.

    Et mieux encore que l'exempter en silence, ce que le dépôt n'a jamais fait.
    """
    with pytest.raises(RenderError, match="aucune largeur de repli"):
        _yaml_block({"description": ["x" * (LIGNE_MAXIMALE + 10)]})
