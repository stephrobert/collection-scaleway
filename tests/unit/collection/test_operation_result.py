"""Un compte rendu qu'une machine ne lit pas oblige à analyser du texte.

Chaque enchaînement rendait son résultat à sa façon, et un analyseur de sortie
standard casse au premier mot reformulé (#206). Ces tests portent sur ce que la
structure **refuse**, parce que c'est là qu'elle vaut quelque chose : une forme
commune qu'on peut remplir de n'importe quoi ne serait qu'une convention de
plus.
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
    / "operation_result.py"
)


def _module():
    """Le plugin, chargé depuis son fichier plutôt que par le chemin d'Ansible.

    `init_plugin_loader` installe le chercheur de collections globalement et
    casse tous les tests qui importent `ansible_collections` par `sys.path` :
    mesuré, et c'est pour ça que le chargement se fait ici à la main.
    """
    spec = importlib.util.spec_from_file_location("operation_result", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["operation_result"] = module
    spec.loader.exec_module(module)
    return module


DEBUT = "2026-09-12T06:00:00Z"
FIN = "2026-09-12T06:00:12Z"


def _resultat(**surcharges):
    module = _module()
    arguments = {
        "target": "scw_tag_office_hours",
        "mode": "apply",
        "started_at": DEBUT,
        "completed_at": FIN,
    }
    arguments.update(surcharges)
    return module.operation_result("power_schedule", **arguments)


# --- ce que la structure garantit -----------------------------------------


def test_les_comptes_se_deduisent_des_noms() -> None:
    """C'est la décision qui porte tout le reste.

    Un `changed: 3` transmis à côté de la liste serait une seconde source du
    même fait, et deux sources d'un même fait finissent par se contredire. Ici
    l'une ne peut pas mentir sur l'autre : elle en est la longueur.
    """
    resultat = _resultat(
        changed=["web-03", "web-01"],
        already_compliant=["web-02"],
        refused=[{"name": "db-01", "reason": "locked"}],
    )

    assert resultat["changed"] == 2
    assert resultat["already_compliant"] == 1
    assert resultat["refused"] == 1
    assert resultat["examined"] == 4
    # Trié, parce que deux exécutions sur le même parc doivent produire les
    # mêmes octets : un JSON qu'on ne peut pas comparer est une décoration.
    assert resultat["names"]["changed"] == ["web-01", "web-03"]


def test_le_mode_est_porte_et_jamais_devine() -> None:
    """En répétition, `changed` compte ce qui **bougerait**.

    Taire le mode a déjà fait lire « machines éteintes » à un opérateur dont
    les machines tournaient encore.
    """
    assert _resultat(mode="check", changed=["web-01"])["mode"] == "check"


# --- ce qu'elle refuse ----------------------------------------------------


def test_un_mode_inconnu_est_refuse() -> None:
    with pytest.raises(Exception) as erreur:
        _resultat(mode="peut-etre")

    assert "machines éteintes" in str(erreur.value)


def test_une_operation_sans_cible_est_refusee() -> None:
    """Une opération qui ne dit pas sur quoi elle a agi ne se relit pas."""
    with pytest.raises(Exception) as erreur:
        _resultat(target="")

    assert "pas de cible" in str(erreur.value)


def test_un_refus_sans_raison_est_refuse() -> None:
    """Une machine écartée sans raison ne se distingue pas d'une oubliée.

    C'est le motif que ce dépôt traque partout : une affirmation que rien
    n'étaye, présentée dans la même forme qu'un fait mesuré.
    """
    with pytest.raises(Exception) as erreur:
        _resultat(refused=[{"name": "db-01"}])

    assert "sans nom ou sans raison" in str(erreur.value)


def test_un_compte_passe_au_lieu_dune_liste_est_refuse() -> None:
    """Sinon la seconde source du même fait revient par la fenêtre."""
    with pytest.raises(Exception) as erreur:
        _resultat(changed=3)

    assert "doit être une liste de noms" in str(erreur.value)


# --- rien mesuré n'est pas rien trouvé ------------------------------------


def test_rien_de_mesurable_rend_null_et_pas_zero() -> None:
    """Un total nul se lit « il n'y avait rien ».

    C'est la règle que le rapport de parc applique déjà à ses zones muettes, et
    celle que le rapport de couverture applique à un ratio sans dénominateur :
    `n/a` plutôt que `0.0 %`.
    """
    resultat = _resultat(unmeasured=["fr-par-3", "it-mil-1"])

    assert resultat["examined"] is None
    assert resultat["changed"] is None
    assert resultat["unmeasured"] == 2
    assert resultat["names"]["unmeasured"] == ["fr-par-3", "it-mil-1"]


def test_un_parc_vraiment_vide_compte_zero() -> None:
    """Et la distinction ne va pas dans l'autre sens.

    Une opération qui a tout lu et n'a rien trouvé a bien mesuré zéro. Rendre
    `null` ici ferait disparaître un fait réel.
    """
    resultat = _resultat()

    assert resultat["examined"] == 0
    assert resultat["unmeasured"] == 0


def test_le_filtre_est_publie_sous_son_nom() -> None:
    """Un plugin que la collection ne publie pas n'existe pas pour un playbook."""
    assert "operation_result" in _module().FilterModule().filters()
