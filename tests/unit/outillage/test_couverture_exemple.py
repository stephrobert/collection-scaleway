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
    """Un dépôt de laboratoire : des modules, un playbook, aucun run."""
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
    # Les écarts déclarés du vrai dépôt n'ont rien à faire dans un dépôt
    # de laboratoire : chaque test qui en veut un le pose lui-même.
    monkeypatch.setattr(example_coverage, "SANS_CIBLE", {})
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


# --- la porte, et ce qu'elle refuse ----------------------------------------


def test_un_module_nomme_en_commentaire_ne_compte_pas(faux_depot: Path) -> None:
    """La porte lit les clés de tâches, pas le texte du fichier.

    Le premier jet cherchait `stephrobert.scaleway.<nom>` dans le fichier
    entier, ce qui était tenable tant que ce compte n'était qu'un ratio publié.
    Depuis qu'il est une porte, un module cité dans un commentaire qui explique
    son absence suffirait à la franchir : le contrôle mesurerait la prose du
    playbook, pas ce qu'il joue.
    """
    _playbook(
        faux_depot,
        "# stephrobert.scaleway.instance_server n'a pas de cible ici\n"
        "- stephrobert.scaleway.lb_ip:\n",
    )
    assert example_coverage.mesurer()["appeles_par_lexemple"] == ["lb_ip"]


def test_un_module_dans_un_block_compte(faux_depot: Path) -> None:
    """Une tâche reste une tâche sous `block`, `rescue` ou `always`."""
    _playbook(
        faux_depot,
        "- hosts: localhost\n"
        "  tasks:\n"
        "    - block:\n"
        "        - stephrobert.scaleway.instance_server: {}\n"
        "      rescue:\n"
        "        - stephrobert.scaleway.lb_ip: {}\n",
    )
    assert example_coverage.mesurer()["appeles_par_lexemple"] == ["instance_server", "lb_ip"]


def test_un_module_sans_cible_declaree_ne_fait_pas_echouer(
    faux_depot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un écart se déclare avec sa raison, et alors seulement il passe."""
    monkeypatch.setattr(
        example_coverage,
        "SANS_CIBLE",
        {
            "instance_server_info": example_coverage.SansCible(
                raison="aucune cible, pour la mesure", preuve="stack", revoir_en="9.9.9"
            )
        },
    )
    _playbook(
        faux_depot,
        "- stephrobert.scaleway.instance_server:\n- stephrobert.scaleway.lb_ip:\n",
    )
    mesure = example_coverage.mesurer()
    assert mesure["non_couverts"] == []
    assert mesure["sans_cible_declaree"] == ["instance_server_info"]


def test_un_module_non_couvert_et_non_declare_est_refuse(faux_depot: Path) -> None:
    """Le cas voisin : sans la déclaration, le même module fait échouer."""
    _playbook(
        faux_depot,
        "- stephrobert.scaleway.instance_server:\n- stephrobert.scaleway.lb_ip:\n",
    )
    assert example_coverage.mesurer()["non_couverts"] == ["instance_server_info"]


# --- l'échéance de revue d'une exemption -------------------------------------


def _exemption(revoir_en: str, preuve: str = "stack") -> example_coverage.SansCible:
    return example_coverage.SansCible(raison="pour la mesure", preuve=preuve, revoir_en=revoir_en)


def test_une_echeance_atteinte_est_nommee(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une échéance qu'on peut ignorer n'est pas une échéance.

    L'exemption dit ce qu'elle attend et quand la rouvrir ; sans le contrôle,
    ces deux champs seraient de la décoration, et la dette vieillirait comme
    avant.
    """
    monkeypatch.setattr(example_coverage, "SANS_CIBLE", {"un_module": _exemption("0.4.0")})

    rattrapees = example_coverage.echeances_depassees("0.4.0")

    assert len(rattrapees) == 1
    assert "un_module" in rattrapees[0]
    assert "0.4.0" in rattrapees[0]
    assert "stack" in rattrapees[0], "ce qu'elle attend est la partie actionnable"


def test_une_echeance_a_venir_ne_dit_rien(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le contre-exemple, sans lequel le contrôle refuserait toute exemption."""
    monkeypatch.setattr(example_coverage, "SANS_CIBLE", {"un_module": _exemption("0.9.0")})

    assert example_coverage.echeances_depassees("0.4.0") == []


def test_une_version_depassee_est_rattrapee(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dépassée, pas seulement atteinte : une release sautée ne doit rien effacer."""
    monkeypatch.setattr(example_coverage, "SANS_CIBLE", {"un_module": _exemption("0.5.0")})

    assert example_coverage.echeances_depassees("0.7.0") != []


def test_les_versions_se_comparent_par_nombres(monkeypatch: pytest.MonkeyPatch) -> None:
    """`0.10.0` est postérieure à `0.9.0`, ce qu'une comparaison de chaînes nie.

    Le défaut ne mordrait qu'à la dixième mineure, et il mordrait en silence :
    l'échéance passerait sans que le contrôle la voie.
    """
    monkeypatch.setattr(example_coverage, "SANS_CIBLE", {"un_module": _exemption("0.9.0")})

    assert example_coverage.echeances_depassees("0.10.0") != []


def test_toutes_les_exemptions_du_depot_attendent_une_preuve_connue() -> None:
    """Une faute de frappe ferait une exemption dont personne ne sait ce qu'elle attend.

    Le seul test du fichier qui regarde le dépôt, et c'est voulu : les autres
    prouvent que la règle décide bien.
    """
    inconnues = {
        nom: exemption.preuve
        for nom, exemption in example_coverage.SANS_CIBLE.items()
        if exemption.preuve not in example_coverage.PREUVES
    }

    assert example_coverage.SANS_CIBLE, "aucune exemption : le test ne mesure plus rien"
    assert inconnues == {}


def test_aucune_echeance_du_depot_nest_deja_depassee() -> None:
    """Ce que le contrôle dit du dépôt aujourd'hui.

    Il rougira le jour où une version publiée rattrapera une exemption, et
    c'est exactement ce jour-là qu'il faut rouvrir la question.
    """
    from generator.ansible.collection import load_collection

    assert example_coverage.echeances_depassees(load_collection().version) == []
