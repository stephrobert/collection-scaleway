"""Le troisième étage de couverture compte-t-il ce qu'il annonce ?

Le dépôt publiait deux ratios, chacun nommé, chacun avec sa fraction. Il en
manquait un troisième, et c'est le seul qui parle d'usage : **un module écrit
n'est pas un module éprouvé**.

Trois nombres distincts, et les confondre serait le maquillage que la règle du
dépôt sur les ratios interdit : appelé par l'exemple se dérive hors ligne du
texte des playbooks, joué contre une cible vient d'un artefact de run, et
l'idempotence ne concerne que les modules de gestion.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import example_coverage
import pytest


@pytest.fixture
def faux_depot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un dépôt de laboratoire : trois modules, un playbook, aucun run."""
    modules = tmp_path / "modules"
    playbooks = tmp_path / "playbooks"
    artefacts = tmp_path / "artefacts"
    inventaire = tmp_path / "inventory"
    for dossier in (modules, playbooks, artefacts, inventaire):
        dossier.mkdir(parents=True)
    # Le plugin d'inventaire se lit sur le disque : le nommer dans le test
    # referait le défaut que ce test vient d'attraper sur un renommage.
    (inventaire / "compute.py").write_text("", encoding="utf-8")
    for nom in ("instance_server", "instance_server_info", "lb_ip"):
        (modules / f"{nom}.py").write_text("", encoding="utf-8")
    (modules / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(example_coverage, "MODULES", modules)
    monkeypatch.setattr(example_coverage, "PLAYBOOKS", playbooks)
    monkeypatch.setattr(example_coverage, "ARTEFACTS", artefacts)
    monkeypatch.setattr(example_coverage, "INVENTAIRE", inventaire)
    return tmp_path


def _playbook(depot: Path, contenu: str) -> None:
    (depot / "playbooks" / "modules.yml").write_text(contenu, encoding="utf-8")


def test_le_ratio_compte_les_modules_que_lexemple_nomme(faux_depot: Path) -> None:
    _playbook(
        faux_depot,
        "- stephrobert.scaleway.instance_server:\n- stephrobert.scaleway.lb_ip:\n",
    )
    mesure = example_coverage.mesurer()
    assert mesure["appeles_par_lexemple"] == ["instance_server", "lb_ip"]
    assert mesure["jamais_appeles"] == ["instance_server_info"]
    assert mesure["ratio_appeles"] == "66,7 %"


def test_le_plugin_dinventaire_nest_pas_un_module(faux_depot: Path) -> None:
    """Il porte le même préfixe sans en être un : le compter fausserait les deux bouts.

    Son nom vient du répertoire des plugins, pas d'une liste écrite ici. Cette
    liste a existé, elle valait ``{"scaleway"}``, et le renommage du plugin en
    ``compute`` a fait refuser un playbook parfaitement correct.
    """
    _playbook(faux_depot, "plugin: stephrobert.scaleway.compute\n")
    assert example_coverage.mesurer()["appeles_par_lexemple"] == []


def test_un_nom_qui_ne_designe_aucun_module_est_refuse(faux_depot: Path) -> None:
    """Une faute de frappe ne doit pas se ranger en silence du côté « pas un module ».

    Sans ce refus, `instance_serveur` sortirait du compte comme le plugin
    d'inventaire, et le ratio se lirait comme une mesure sur un playbook qui
    produit une tâche inexistante.
    """
    _playbook(faux_depot, "- stephrobert.scaleway.instance_serveur:\n")
    with pytest.raises(example_coverage.CouvertureError, match="instance_serveur"):
        example_coverage.mesurer()


def test_sans_module_le_ratio_est_indefini_pas_nul(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La règle du dépôt sur les dénominateurs, appliquée au troisième étage."""
    vide = tmp_path / "vide"
    vide.mkdir()
    monkeypatch.setattr(example_coverage, "MODULES", vide)
    monkeypatch.setattr(example_coverage, "PLAYBOOKS", vide)
    monkeypatch.setattr(example_coverage, "ARTEFACTS", vide)
    monkeypatch.setattr(example_coverage, "INVENTAIRE", vide)
    assert example_coverage.mesurer()["ratio_appeles"] == "n/a"


def test_sans_run_enregistre_on_le_dit_plutot_que_decrire_zero(faux_depot: Path) -> None:
    """Rien n'a été mesuré n'est pas rien n'a marché."""
    _playbook(faux_depot, "- stephrobert.scaleway.lb_ip:\n")
    mesure = example_coverage.mesurer()
    assert mesure["runs"] == {}
    assert "aucun run enregistré" in example_coverage.rendre(mesure)


def test_un_run_enregistre_publie_ce_quil_a_joue(faux_depot: Path) -> None:
    """Joué vient de l'artefact, et il ne vaut que pour le run qui l'a produit."""
    _playbook(faux_depot, "- stephrobert.scaleway.lb_ip:\n")
    artefact: dict[str, Any] = {
        "cible": "reel",
        "run_id": "abc",
        "horodatage": "2026-09-04T06:00:00+00:00",
        "modules_joues": ["lb_ip"],
        "idempotence_prouvee": ["repris_adresse_lb"],
        "residu": "aucun",
    }
    (faux_depot / "artefacts" / "dernier-reel.json").write_text(
        json.dumps(artefact), encoding="utf-8"
    )
    run = example_coverage.mesurer()["runs"]["reel"]
    assert run["modules_joues"] == ["lb_ip"]
    assert run["ratio_joues"] == "33,3 %"
    assert run["idempotence_prouvee"] == 1
