"""Un émulateur adopté sert-il le mode que la cible demande.

`refuser_emulateur_habite` pose une bonne question : cet émulateur contient-il
déjà quelque chose. Elle ne dit rien du mode, et `cible["vm"]` ne servait qu'au
démarrage d'un émulateur neuf.

Le cas était vivant le 2026-09-11 : un émulateur en `--vm off` écoutait sur le
port de l'exercice depuis deux jours, vide. `machines` l'aurait adopté, aurait
déployé le plan de contrôle, puis aurait joué des playbooks SSH contre des
machines que personne ne démarre. L'échec serait arrivé après plusieurs minutes
d'attente et aurait accusé les playbooks.
"""

from __future__ import annotations

import json
from typing import Any

import example
import pytest

ADRESSE = "127.0.0.1:4877"
EMULATEUR = {"emulateur": True, "vm": "off", "ssh": False}
MACHINES = {"emulateur": True, "vm": "incus-ovn", "ssh": True}


def _declare(monkeypatch: pytest.MonkeyPatch, charge: Any, code: int = 0) -> None:
    """Fait dire à `feint status` ce que le test veut mesurer.

    **`binaire` est remplacé aussi, et c'est le point.** `mode_servi` le résout
    avant d'appeler `lancer`, et il refuse quand `feint` n'est pas sur le
    `PATH` : la première version de ce test passait sur un poste où feint est
    installé et rougissait sur le runner. Un test qui mesure la machine plutôt
    que la fonction ne mesure pas ce qu'il annonce.
    """

    def _lancer(commande: list[str], **_: Any) -> Any:
        assert "status" in commande, "la garde doit interroger `feint status`"
        sortie = charge if isinstance(charge, str) else json.dumps(charge)
        return type("Resultat", (), {"returncode": code, "stdout": sortie})()

    monkeypatch.setattr(example, "binaire", lambda nom: f"/introuvable/{nom}")
    monkeypatch.setattr(example, "lancer", _lancer)


def test_le_mode_declare_est_celui_que_feint_rend(monkeypatch: pytest.MonkeyPatch) -> None:
    _declare(monkeypatch, {"running": True, "machines": "incus-ovn"})
    assert example.mode_servi(ADRESSE) == "incus-ovn"


def test_un_emulateur_muet_ne_rend_pas_un_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _declare(monkeypatch, "", code=1)
    assert example.mode_servi(ADRESSE) is None


def test_une_sortie_qui_nest_pas_du_json_ne_rend_pas_un_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Une version de feint qui change sa sortie ne doit pas passer pour un mode."""
    _declare(monkeypatch, "running on 127.0.0.1:4877")
    assert example.mode_servi(ADRESSE) is None


# --- ce que la garde refuse ------------------------------------------------


def test_le_cas_mesure_du_2026_09_11_est_refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un émulateur vide en `--vm off`, et la cible `machines` qui l'adopterait."""
    _declare(monkeypatch, {"running": True, "machines": "none"})

    with pytest.raises(example.ExempleError) as erreur:
        example.refuser_un_mode_incompatible(MACHINES, ADRESSE)

    message = str(erreur.value)
    # Les deux valeurs sont nommées : « incompatible » tout seul oblige à
    # rejouer la commande pour apprendre laquelle des deux est en cause.
    assert "none" in message
    assert "incus-ovn" in message
    # Et la sortie non hostile est proposée, plutôt que d'arrêter le processus
    # de quelqu'un d'autre.
    assert "FEINT_ADDR" in message


def test_un_emulateur_qui_ne_dit_pas_son_mode_est_refuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ne pas savoir n'est pas savoir que ça va : la garde refuse plutôt que de supposer."""
    _declare(monkeypatch, "", code=1)

    with pytest.raises(example.ExempleError) as erreur:
        example.refuser_un_mode_incompatible(MACHINES, ADRESSE)

    assert "ne dit pas dans quel mode" in str(erreur.value)
    assert "FEINT_ADDR" in str(erreur.value)


# --- ce qu'elle laisse passer ----------------------------------------------


def test_le_mode_demande_par_la_cible_passe(monkeypatch: pytest.MonkeyPatch) -> None:
    _declare(monkeypatch, {"running": True, "machines": "incus-ovn"})
    example.refuser_un_mode_incompatible(MACHINES, ADRESSE)


def test_off_se_lit_none_et_la_cible_emulateur_passe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mesuré : `--vm off` se déclare `none`.

    Comparer `off` à `none` sans cette table refuserait la cible la plus
    courante du dépôt, ce qui est pire que l'absence de garde.
    """
    _declare(monkeypatch, {"running": True, "machines": "none"})
    example.refuser_un_mode_incompatible(EMULATEUR, ADRESSE)


def test_la_table_des_modes_ne_traduit_que_ce_qui_a_ete_mesure() -> None:
    """`incus-ovn` se déclare sous son propre nom : rien à traduire.

    Ajouter une entrée non mesurée ici ferait accepter un émulateur qui ne sert
    pas ce que la cible demande, ce que cette garde existe pour empêcher.
    """
    assert example.MODES_DECLARES == {"off": "none"}
