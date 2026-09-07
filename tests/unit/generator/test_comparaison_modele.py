"""Qui décide comment un champ se compare, et ce que personne n'a le droit de deviner.

Le contrat ne dit ni l'ordre ni l'unicité d'un tableau. Mesuré sur les deux
documents vendorisés : aucun ne porte `uniqueItems`, et aucune description de
tableau ne parle d'ordre. `SET` est donc une décision humaine, jamais une
déduction, et elle porte sa raison comme tous les arbitrages de ce dépôt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.comparison import (
    ComparisonStrategy,
    depuis_le_nom,
    strategie_par_defaut,
)
from generator.ir.enums import ApiType
from generator.overrides.loader import OverrideError, load_overrides

# --- ce que le type décide -------------------------------------------------


def test_un_tableau_reste_compare_dans_lordre() -> None:
    """`ordered_list` est le repli, et c'est le comportement d'avant.

    Adopter `set` par défaut ferait taire un `changed` qui a peut-être raison,
    et un module qui tait un changement réel est pire qu'un module qui en
    annonce un de trop.
    """
    assert strategie_par_defaut(ApiType.ARRAY) is ComparisonStrategy.ORDERED_LIST


@pytest.mark.parametrize("type_api", [ApiType.OBJECT, ApiType.MAP])
def test_un_objet_se_compare_cle_par_cle(type_api: ApiType) -> None:
    """L'égalité de deux dictionnaires ne dépend déjà pas de l'ordre.

    Le nommer rend l'intention lisible plutôt qu'implicite.
    """
    assert strategie_par_defaut(type_api) is ComparisonStrategy.MAPPING


@pytest.mark.parametrize(
    "type_api", [ApiType.STRING, ApiType.INTEGER, ApiType.BOOLEAN, ApiType.ENUM, ApiType.UNKNOWN]
)
def test_le_reste_se_compare_strictement(type_api: ApiType) -> None:
    """Y compris un type que le parser n'a pas su lire.

    L'égalité stricte est le comportement le plus prudent : elle peut annoncer
    un changement de trop, jamais en taire un.
    """
    assert strategie_par_defaut(type_api) is ComparisonStrategy.SCALAR


# --- ce qu'un override peut poser -----------------------------------------


def test_un_nom_de_strategie_inconnu_est_refuse() -> None:
    """Une faute de frappe produirait un override silencieusement inerte.

    Le module comparerait strictement en croyant comparer autrement, et
    personne ne s'en apercevrait : c'est exactement le mode de défaillance que
    le chargeur d'overrides existe pour empêcher.
    """
    with pytest.raises(ValueError) as erreur:
        depuis_le_nom("ensemble")

    assert "inconnue" in str(erreur.value)


def _override(dossier: Path, corps: str) -> Path:
    chemin = dossier / "widget.yml"
    chemin.write_text(corps, encoding="utf-8")
    return dossier


def test_un_override_de_comparaison_exige_sa_raison(tmp_path: Path) -> None:
    """Poser `set` est une décision, prise sur une observation.

    Sans `reason`, personne ne peut savoir si l'observation a eu lieu.
    """
    racine = _override(
        tmp_path,
        "operations:\n"
        "  widget.v1.Widget.UpdateWidget:\n"
        "    parameters:\n"
        "      tags:\n"
        "        comparison: set\n",
    )

    with pytest.raises(OverrideError) as erreur:
        load_overrides("widget", racine)

    assert "reason" in str(erreur.value)


def test_un_override_ne_pose_pas_ce_que_le_type_decide(tmp_path: Path) -> None:
    """`scalar`, `ordered_list` et `mapping` viennent du type.

    Les laisser s'écrire à la main ferait deux sources pour la même décision,
    et elles divergeraient sans que rien ne le dise.
    """
    racine = _override(
        tmp_path,
        "operations:\n"
        "  widget.v1.Widget.UpdateWidget:\n"
        "    parameters:\n"
        "      tags:\n"
        "        comparison: ordered_list\n"
        "        reason: parce que\n",
    )

    with pytest.raises(OverrideError) as erreur:
        load_overrides("widget", racine)

    assert "que le type du paramètre décide déjà" in str(erreur.value)


def test_un_override_de_comparaison_complet_est_accepte(tmp_path: Path) -> None:
    """Le contre-exemple, sans lequel les deux tests précédents passeraient
    aussi sur un chargeur qui refuserait tout."""
    racine = _override(
        tmp_path,
        "operations:\n"
        "  widget.v1.Widget.UpdateWidget:\n"
        "    parameters:\n"
        "      tags:\n"
        "        comparison: set\n"
        "        reason: l'API rend les tags dans un ordre qu'elle ne promet pas\n",
    )

    charges = load_overrides("widget", racine)
    restriction = charges.get("widget.v1.Widget.UpdateWidget").parameters["tags"]

    assert restriction.comparison is ComparisonStrategy.SET
