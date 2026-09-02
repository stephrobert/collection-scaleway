"""La classification tranche, et ce qu'elle ne tranche pas se voit."""

from __future__ import annotations

from generator.classifier.rules import classify, verb_of
from generator.ir.enums import GenerationMode, HTTPMethod, OperationKind, Scope
from generator.ir.models import ApiOperation, ApiService
from generator.plan import ProductPlan


def _operation(operation_id: str, method: HTTPMethod, path: str = "/x/v1/things") -> ApiOperation:
    return ApiOperation(
        id=operation_id,
        service="x",
        version="v1",
        resource="thing",
        http_method=method,
        path=path,
        scope=Scope.GLOBAL,
    )


def test_le_verbe_est_le_premier_mot_de_loperation_id() -> None:
    assert verb_of(_operation("ListPrivateNICs", HTTPMethod.GET)) == "list"
    assert verb_of(_operation("ServerAction", HTTPMethod.POST)) == "server"


def test_get_et_list_sont_de_linformation(widget_plan: ProductPlan) -> None:
    par_operation = {plan.operation.id: plan.kind for plan in widget_plan.operations}
    assert par_operation["GetWidget"] is OperationKind.INFO
    assert par_operation["ListWidgets"] is OperationKind.INFO


def test_create_et_delete_relevent_du_cycle_de_vie(widget_plan: ProductPlan) -> None:
    par_operation = {plan.operation.id: plan.kind for plan in widget_plan.operations}
    assert par_operation["CreateWidget"] is OperationKind.LIFECYCLE
    assert par_operation["DeleteWidget"] is OperationKind.LIFECYCLE


def test_patch_est_une_gestion_detat(widget_plan: ProductPlan) -> None:
    par_operation = {plan.operation.id: plan.kind for plan in widget_plan.operations}
    assert par_operation["UpdateWidget"] is OperationKind.MANAGE


def test_un_post_qui_nest_pas_une_creation_est_une_action(widget_plan: ProductPlan) -> None:
    par_operation = {plan.operation.id: plan.kind for plan in widget_plan.operations}
    assert par_operation["WidgetAction"] is OperationKind.ACTION


def test_une_methode_sans_regle_est_declaree_inconnue() -> None:
    """Un PUT sans verbe d'écriture reconnu ne doit pas être rangé au hasard."""
    decision = classify(_operation("ReplaceThing", HTTPMethod.PUT))
    assert decision.kind is OperationKind.UNKNOWN
    assert "replace" in decision.reason


def test_la_classification_automatique_se_declare_comme_telle() -> None:
    decision = classify(_operation("GetThing", HTTPMethod.GET))
    assert decision.mode is GenerationMode.AUTO
    assert decision.reason


def test_aucune_operation_ne_disparait_du_plan(
    widget_plan: ProductPlan, widget_service: ApiService
) -> None:
    """Le plan porte exactement autant d'entrées que le contrat d'opérations."""
    assert len(widget_plan.operations) == len(widget_service.operations)
    assert {plan.operation.id for plan in widget_plan.operations} == {
        operation.id for operation in widget_service.operations
    }
