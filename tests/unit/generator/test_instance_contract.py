"""Garanties portant sur le contrat Instance réel, versionné dans `specs/`.

Ces tests ont deux rôles. Ils vérifient que la chaîne tient sur des données
réelles, et ils font office de détecteur de dérive : quand Scaleway modifie
l'API Instance, c'est ici que le changement se voit d'abord, sous la forme
d'un golden qui ne correspond plus.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.ir.enums import ApiType, OperationKind
from generator.ir.models import ApiService
from generator.plan import ProductPlan
from generator.report import render

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
GOLDEN = FIXTURES / "instance" / "expected_ir.json"


def test_le_contrat_instance_porte_toutes_ses_operations(instance_service: ApiService) -> None:
    """74 opérations mesurées sur le contrat versionné, pas un nombre supposé."""
    assert len(instance_service.operations) == 74


def test_aucune_operation_nest_laissee_sans_classification(instance_plan: ProductPlan) -> None:
    """La règle de sécurité du projet : rien ne disparaît en silence."""
    assert instance_plan.unknown == ()
    assert len(instance_plan.operations) == len(instance_plan.service.operations)


def test_get_et_list_du_serveur_partagent_un_seul_module_info(instance_plan: ProductPlan) -> None:
    modules = instance_plan.modules()
    assert "instance_server_info" in modules
    assert {plan.operation.id for plan in modules["instance_server_info"]} == {
        "GetServer",
        "ListServers",
    }


def test_le_module_daction_du_serveur_existe(instance_plan: ProductPlan) -> None:
    modules = instance_plan.modules()
    assert {plan.operation.id for plan in modules["instance_server_action"]} == {"ServerAction"}


def test_aucun_module_ne_porte_un_verbe_http(instance_plan: ProductPlan) -> None:
    interdits = {"get", "list", "post", "patch", "put", "delete"}
    for nom in instance_plan.modules():
        assert not interdits & set(nom.split("_")), nom


def test_les_actions_du_serveur_viennent_du_contrat(instance_service: ApiService) -> None:
    """Les valeurs ne sont pas une liste écrite à la main dans le générateur."""
    operation = instance_service.operation("ServerAction")
    assert operation is not None
    action = operation.parameter("action")
    assert action is not None
    assert action.type is ApiType.ENUM
    assert {"poweron", "poweroff", "reboot"} <= set(action.enum_values)


def test_les_operations_de_liste_sont_paginees(instance_service: ApiService) -> None:
    liste = instance_service.operation("ListServers")
    assert liste is not None
    assert liste.pagination is not None


def test_la_zone_est_un_enum_ferme(instance_service: ApiService) -> None:
    operation = instance_service.operation("GetServer")
    assert operation is not None
    zone = operation.parameter("zone")
    assert zone is not None
    assert zone.required is True
    assert "fr-par-1" in zone.enum_values


def test_le_cycle_de_vie_nest_pas_expose(instance_plan: ProductPlan) -> None:
    """Créer et supprimer un serveur reste le travail de Terraform."""
    par_operation = {plan.operation.id: plan for plan in instance_plan.operations}
    for operation_id in ("CreateServer", "DeleteServer"):
        assert par_operation[operation_id].kind is OperationKind.LIFECYCLE
        assert par_operation[operation_id].module is None


def test_la_couverture_ne_compte_que_les_operations_day2(instance_plan: ProductPlan) -> None:
    day2 = len(instance_plan.day2)
    exclues = sum(
        1
        for plan in instance_plan.operations
        if plan.kind in (OperationKind.LIFECYCLE, OperationKind.IGNORE)
    )
    assert day2 + exclues == len(instance_plan.operations)
    couverture = instance_plan.coverage()
    assert couverture is not None and 0.0 < couverture <= 1.0


def test_lir_est_identique_au_golden(instance_service: ApiService) -> None:
    """Un changement du contrat ou du parser doit produire un diff lisible.

    Régénérer après un changement voulu : `mise run golden:update`.
    """
    if not GOLDEN.is_file():
        pytest.fail(f"golden absent : {GOLDEN}. Lancer `mise run golden:update`.")
    assert instance_service.to_json() == GOLDEN.read_text(encoding="utf-8")


def test_le_rapport_json_est_deterministe(instance_plan: ProductPlan) -> None:
    assert render.to_json(instance_plan) == render.to_json(instance_plan)
    charge = json.loads(render.to_json(instance_plan))
    assert charge["totals"]["operations"] == 74
    assert charge["unknown_operations"] == []


def test_le_rapport_expose_les_limites_du_contrat(instance_plan: ProductPlan) -> None:
    """Ce que le contrat ne dit pas doit rester visible, pas être absorbé."""
    charge = json.loads(render.to_json(instance_plan))
    assert charge["parser_warnings"], "les tableaux sans `items` doivent être signalés"


def test_le_compte_rendu_de_generation_dit_ce_qui_est_ecarte(instance_plan) -> None:
    """Un module absent sans explication est indiscernable d'un module oublié.

    Ces trois listes ne vivaient que sur la sortie standard de `generate` :
    elles mouraient avec le terminal, alors qu'elles disent exactement ce qu'un
    lecteur veut savoir de la collection.
    """
    rendu = render.to_generation_markdown(
        instance_plan,
        written=["instance_server_info"],
        skipped=[
            ("instance_volume", "classe non rendable"),
            ("instance_image", "classe non rendable"),
        ],
        limits=["tags : tableau sans items"],
    )

    assert "Modules écrits : **1**, écartés : **2**" in rendu
    assert "`instance_server_info`" in rendu
    # La raison est portée une fois, avec les deux modules qu'elle écarte.
    assert "classe non rendable (2)" in rendu
    assert "`instance_image`, `instance_volume`" in rendu
    assert "tags : tableau sans items" in rendu


def test_un_compte_rendu_sans_ecart_ne_fabrique_pas_de_section_vide(instance_plan) -> None:
    """Une section « ce qui est écarté » vide se lirait comme « rien n'a été
    écarté », ce qui est vrai ici, mais elle n'a pas à être écrite pour le dire."""
    rendu = render.to_generation_markdown(
        instance_plan, written=["instance_server_info"], skipped=[], limits=[]
    )

    assert "Ce qui est écarté" not in rendu
    assert "Ce que le contrat ne dit pas" not in rendu
