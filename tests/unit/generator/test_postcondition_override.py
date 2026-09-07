"""Écarter un champ de la vérification d'après écriture est une décision.

Le cas prévu est une API qui applique le champ de façon différée : le vérifier
ferait échouer un playbook correct sur un délai plutôt que sur une erreur.

C'est une observation, pas une propriété du contrat, donc un override, donc une
`reason`. Sans elle, l'échappatoire deviendrait le moyen commode de faire taire
une vérification gênante, ce qui rendrait la vérification décorative.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.overrides.loader import OverrideError, load_overrides

CLE = "widget.v1.Widget.UpdateWidget"


def _override(dossier: Path, lignes: str) -> Path:
    (dossier / "widget.yml").write_text(
        f"operations:\n  {CLE}:\n    parameters:\n      name:\n{lignes}",
        encoding="utf-8",
    )
    return dossier


def test_ecarter_un_champ_exige_sa_raison(tmp_path: Path) -> None:
    racine = _override(tmp_path, "        postcondition: false\n")

    with pytest.raises(OverrideError) as erreur:
        load_overrides("widget", racine)

    assert "reason" in str(erreur.value)


def test_remettre_un_champ_dans_la_verification_est_refuse(tmp_path: Path) -> None:
    """`true` est déjà le comportement.

    Un override qui redit le défaut n'a aucun effet, et il se lit comme une
    décision : c'est la même famille que l'override orphelin.
    """
    racine = _override(tmp_path, "        postcondition: true\n        reason: parce que\n")

    with pytest.raises(OverrideError) as erreur:
        load_overrides("widget", racine)

    assert "déjà le comportement" in str(erreur.value)


def test_une_valeur_qui_nest_pas_un_booleen_est_refusee(tmp_path: Path) -> None:
    racine = _override(tmp_path, "        postcondition: peut-être\n        reason: parce que\n")

    with pytest.raises(OverrideError) as erreur:
        load_overrides("widget", racine)

    assert "booléen" in str(erreur.value)


def test_un_ecart_complet_est_accepte(tmp_path: Path) -> None:
    """Le contre-exemple, sans lequel les refus ci-dessus passeraient aussi sur
    un chargeur qui refuserait tout."""
    racine = _override(
        tmp_path,
        "        postcondition: false\n"
        "        reason: l'API applique ce champ de façon différée, observé le 7 septembre\n",
    )

    charges = load_overrides("widget", racine)

    assert charges.get(CLE).parameters["name"].postcondition is False
