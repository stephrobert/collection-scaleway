"""Ce que l'artefact d'un run compte comme couvert, et ce qu'il refuse de compter.

Un run contre le compte Scaleway réel ne laissait rien derrière lui : le lanceur
imprimait son compte rendu sur la sortie standard, qui disparaît avec le
terminal. La question « ce module a-t-il jamais tourné contre la vraie API »
n'avait aucune source, et le seul étage de mesure qui compte pour un utilisateur
était le seul que le dépôt ne mesurait pas.

Le journal vient d'Ansible, par un plugin de rappel, et pas d'une analyse du
playbook : **joué n'est pas appelé**. Une tâche gardée par un `when` non
satisfait ne touche jamais l'API, et une route que l'émulateur ne sert pas rend
501 sans rien exercer. Les compter ferait de l'artefact un compteur de bonnes
intentions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import example

REPO_ROOT = Path(__file__).resolve().parents[3]


def _journal(*taches: dict[str, Any], **faits: Any) -> dict[str, Any]:
    return {"taches": list(taches), "faits": faits}


def _tache(module: str, verdict: str = "ok", **reste: Any) -> dict[str, Any]:
    return {"module": module, "tache": module, "verdict": verdict, "changed": False, **reste}


def test_un_module_joue_est_compte() -> None:
    resultat = example.artefact(
        _journal(_tache("stephrobert.scaleway.instance_server_info")), "reel", "abc", "aucun"
    )
    assert resultat["modules_joues"] == ["instance_server_info"]
    assert resultat["modules_declines"] == []
    assert resultat["modules_sautes"] == []
    assert resultat["modules_en_echec"] == []


def test_une_route_non_emulee_est_appelee_mais_pas_jouee() -> None:
    """Un 501 n'exerce rien : le compter ferait passer une limite pour une preuve."""
    resultat = example.artefact(
        _journal(
            _tache("stephrobert.scaleway.instance_dashboard_info", api_type="not_emulated"),
        ),
        "emulateur",
        "abc",
        "sans objet (émulateur)",
    )
    assert resultat["modules_joues"] == []
    assert resultat["modules_declines"] == ["instance_dashboard_info"]
    assert resultat["modules_sautes"] == [], "un appel décliné n'est pas un saut"


def test_une_tache_sautee_nest_pas_une_couverture() -> None:
    """Une tâche que `when` a écartée n'a parlé à personne."""
    resultat = example.artefact(
        _journal(_tache("stephrobert.scaleway.lb_certificate_info", verdict="skipped")),
        "reel",
        "abc",
        "aucun",
    )
    assert resultat["modules_joues"] == []
    assert resultat["modules_sautes"] == ["lb_certificate_info"]
    assert resultat["modules_declines"] == [], "sauter n'est pas se faire décliner"


def test_un_module_joue_une_fois_et_saute_ailleurs_compte_comme_joue() -> None:
    """La question posée est « a-t-il tourné », pas « toutes ses tâches ont-elles tourné »."""
    resultat = example.artefact(
        _journal(
            _tache("stephrobert.scaleway.instance_ip", verdict="skipped"),
            _tache("stephrobert.scaleway.instance_ip", verdict="changed"),
        ),
        "reel",
        "abc",
        "aucun",
    )
    assert resultat["modules_joues"] == ["instance_ip"]
    assert resultat["modules_sautes"] == []


def test_les_modules_dailleurs_ne_gonflent_pas_le_compte() -> None:
    """`ansible.builtin.assert` n'est pas une preuve de couverture de la collection."""
    resultat = example.artefact(
        _journal(
            _tache("ansible.builtin.assert"),
            _tache("ansible.builtin.set_fact"),
            _tache("stephrobert.scaleway.lb_ip_info"),
        ),
        "reel",
        "abc",
        "aucun",
    )
    assert resultat["modules_joues"] == ["lb_ip_info"]
    assert resultat["taches_jouees"] == 3


def test_le_recensement_du_playbook_est_repris_tel_quel() -> None:
    """Les trois listes que le playbook construisait pour ses assertions, et jetait."""
    resultat = example.artefact(
        _journal(
            idempotences_prouvees=["repris_serveur"],
            reecritures_non_mesurees=["repris_carte"],
            non_emules=["GetDashboard"],
        ),
        "emulateur",
        "abc",
        "sans objet (émulateur)",
    )
    assert resultat["idempotence_prouvee"] == ["repris_serveur"]
    assert resultat["reecritures_non_mesurees"] == ["repris_carte"]
    assert resultat["routes_non_emulees"] == ["GetDashboard"]


def test_sans_journal_aucun_artefact_nest_ecrit(tmp_path: Path) -> None:
    """Un artefact vide se lirait comme une exécution qui n'a rien couvert."""
    assert example.ecrire_artefact(tmp_path / "absent.json", "reel", "abc", "aucun") is None


def test_lartefact_ecrit_porte_un_nom_stable_en_plus_du_sien(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """La mesure suivante ne doit pas avoir à deviner quel `run_id` était le dernier."""
    monkeypatch.setattr(example, "TRAVAIL", tmp_path)
    journal = tmp_path / "journal.json"
    journal.write_text(
        json.dumps(_journal(_tache("stephrobert.scaleway.lb_ip_info"))), encoding="utf-8"
    )
    ecrit = example.ecrire_artefact(journal, "reel", "abc", "aucun")
    assert ecrit == tmp_path / "reel-abc.json"
    stable = tmp_path / "dernier-reel.json"
    assert json.loads(stable.read_text(encoding="utf-8"))["modules_joues"] == ["lb_ip_info"]


# --- quatre sorts, et les confondre envoie un rapport chez le mauvais projet ---


def test_un_appel_decline_et_une_tache_sautee_ne_vont_pas_dans_la_meme_liste() -> None:
    """C'est le défaut de #189, en une assertion.

    Les deux finissaient dans `modules_appeles_sans_reponse`, et la comparaison
    publiait « chacun a été appelé des deux côtés » sur l'ensemble.
    """
    resultat = example.artefact(
        _journal(
            _tache("stephrobert.scaleway.instance_volume_type_info", api_type="not_emulated"),
            _tache("stephrobert.scaleway.lb_certificate", verdict="skipped"),
        ),
        "emulateur",
        "abc",
        "sans objet (émulateur)",
    )
    assert resultat["modules_declines"] == ["instance_volume_type_info"]
    assert resultat["modules_sautes"] == ["lb_certificate"]


def test_une_tache_en_echec_est_appelee_et_nest_pas_un_refus_de_la_route() -> None:
    """Un échec peut venir de la stack : le ranger avec les refus accuse à tort."""
    resultat = example.artefact(
        _journal(_tache("stephrobert.scaleway.lb_frontend", verdict="failed")),
        "reel",
        "abc",
        "aucun",
    )
    assert resultat["modules_en_echec"] == ["lb_frontend"]
    assert resultat["modules_declines"] == []
    assert resultat["modules_sautes"] == []


def test_un_appel_l_emporte_sur_un_saut_ailleurs() -> None:
    """Sauté ici, décliné là : il a bien été appelé une fois."""
    resultat = example.artefact(
        _journal(
            _tache("stephrobert.scaleway.instance_image", verdict="skipped"),
            _tache("stephrobert.scaleway.instance_image", api_type="not_emulated"),
        ),
        "emulateur",
        "abc",
        "sans objet (émulateur)",
    )
    assert resultat["modules_declines"] == ["instance_image"]
    assert resultat["modules_sautes"] == []


def test_un_module_joue_ailleurs_ne_figure_dans_aucune_autre_liste() -> None:
    resultat = example.artefact(
        _journal(
            _tache("stephrobert.scaleway.instance_ip", api_type="not_emulated"),
            _tache("stephrobert.scaleway.instance_ip", verdict="skipped"),
            _tache("stephrobert.scaleway.instance_ip", verdict="changed"),
        ),
        "reel",
        "abc",
        "aucun",
    )
    assert resultat["modules_joues"] == ["instance_ip"]
    assert resultat["modules_declines"] == []
    assert resultat["modules_sautes"] == []
    assert resultat["modules_en_echec"] == []
