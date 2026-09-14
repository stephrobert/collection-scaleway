"""Ce que la collection officielle livre, et ce qu'on s'interdit à cause d'elle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import officielle  # noqa: E402


def _mesure() -> dict:
    return json.loads(officielle.MESURE.read_text(encoding="utf-8"))


# ---- La mesure versionnée ------------------------------------------------


def test_la_mesure_est_versionnee_et_lisible_hors_ligne() -> None:
    """C'est tout l'intérêt : `admission` ne va jamais sur le réseau."""
    mesure = officielle.lire()

    assert mesure["collection"] == "scaleway.scaleway"
    assert mesure["version"]
    assert mesure["measured_at"]


def test_leur_depot_porte_bien_plus_de_modules_que_leur_archive() -> None:
    """**Le fait qui justifie tout ce script.**

    Un décompte fait sur le dépôt se trompe d'un ordre de grandeur, et il se lit
    exactement comme un décompte juste.
    """
    mesure = _mesure()

    assert len(mesure["modules_ecartes"]) > len(mesure["modules_livres"])


def test_chaque_module_livre_porte_sa_forme_lue_dans_son_code() -> None:
    """La forme est mesurée, pas déduite du nom."""
    formes = set(_mesure()["modules_livres"].values())

    assert formes == {"absent/present"}


# ---- La garde : une interdiction fantôme ---------------------------------


def test_ce_quon_sinterdit_porte_une_raison() -> None:
    """Une frontière sans raison est une frontière que le suivant déplacera."""
    for entree in officielle.CE_QUON_LEUR_LAISSE:
        assert entree["raison"].strip()
        assert entree["nous"].strip()
        assert entree["sert"].strip()


def test_ce_quon_sinterdit_est_encore_servi_par_eux() -> None:
    """Une interdiction fantôme se lit comme une décision en vigueur.

    Le jour où ils cessent de livrer leur lookup de secrets, la raison de ne pas
    écrire `AccessSecretVersion` tombe, et personne ne le remarquerait si rien
    ne recoupait les deux.
    """
    assert officielle._verifier_ce_quon_leur_laisse(_mesure()) == []


def test_une_interdiction_qui_ne_correspond_plus_est_nommee() -> None:
    """Le recoupement doit **mordre**, pas seulement exister."""
    mesure = _mesure()
    mesure["plugins_livres"] = {}
    mesure["modules_livres"] = {}

    perimees = officielle._verifier_ce_quon_leur_laisse(mesure)

    assert perimees
    assert "AccessSecretVersion" in perimees[0]


# ---- Le refus de deviner --------------------------------------------------


def test_une_mesure_absente_est_un_echec_de_programme_pas_un_verdict() -> None:
    """« Je n'ai pas la mesure » et « la mesure dit non » ne sont pas la même chose."""
    ancienne = officielle.MESURE
    officielle.MESURE = ROOT / "specs" / "officielle" / "personne.json"
    try:
        with pytest.raises(SystemExit, match="sync:officielle"):
            officielle.lire()
    finally:
        officielle.MESURE = ancienne


def test_un_module_sans_state_est_rendu_tel_quel() -> None:
    """Le module qui ne suit pas leur patron est celui dont la frontière compte."""
    assert officielle._forme("def main():\n    pass\n") is None
    assert (
        officielle._forme("    state = dict(type='str', choices=['present', 'absent'])")
        == "absent/present"
    )
