"""Ce que le contrôle des artefacts générés retient, et ce qu'il laisse passer.

Le défaut qu'il a eu : compter un fichier **indexé** comme une dérive. Le
crochet de pré-commit devenait alors auto-contradictoire, en refusant le commit
qui portait la régénération qu'il réclamait, et la seule issue était de le
contourner.
"""

from __future__ import annotations

import check_generated


def test_un_fichier_regenere_puis_indexe_nest_pas_une_derive() -> None:
    """Il a exactement le contenu que le générateur produit : c'est le but."""
    assert check_generated.derives("M  plugins/modules/lb_ip.py") == []
    assert check_generated.derives("A  changelogs/fragments/neuf.yml") == []


def test_un_fichier_modifie_apres_avoir_ete_indexe_est_une_derive() -> None:
    """La régénération a changé le disque depuis le `git add` : c'est le cas visé."""
    assert check_generated.derives("MM plugins/modules/lb_ip.py") == ["MM plugins/modules/lb_ip.py"]


def test_un_fichier_modifie_et_non_indexe_est_une_derive() -> None:
    assert check_generated.derives(" M plugins/modules/lb_ip.py") == [" M plugins/modules/lb_ip.py"]


def test_un_fichier_non_suivi_reste_une_derive() -> None:
    """C'est le cas que `git diff --exit-code` ne voit pas, et la raison du script."""
    assert check_generated.derives("?? plugins/modules/neuf.py") == ["?? plugins/modules/neuf.py"]


def test_un_arbre_propre_ne_derive_de_rien() -> None:
    assert check_generated.derives("") == []
