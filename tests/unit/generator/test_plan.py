"""Le plan compte ce qu'il compte, et ne maquille pas la mesure."""

from __future__ import annotations

from generator.ir.enums import GenerationMode, OperationKind, Scope
from generator.ir.models import ApiService
from generator.overrides.loader import OverrideSet
from generator.plan import ProductPlan, plan_service


def test_une_couverture_sans_operation_day2_est_indefinie() -> None:
    """Un ratio sans dénominateur n'est pas zéro : il n'existe pas."""
    vide = plan_service(ApiService(name="vide", version="v1"), OverrideSet(source=None))
    assert vide.coverage() is None


def test_le_denominateur_exclut_le_cycle_de_vie_et_lecarte(widget_plan: ProductPlan) -> None:
    day2 = {plan.kind for plan in widget_plan.day2}
    assert OperationKind.LIFECYCLE not in day2
    assert OperationKind.IGNORE not in day2


def test_chaque_classe_est_comptee_meme_a_zero(widget_plan: ProductPlan) -> None:
    """Une classe absente vaut zéro affiché, pas une ligne manquante."""
    comptes = widget_plan.count_by_kind()
    assert set(comptes) == set(OperationKind)
    assert comptes[OperationKind.UNKNOWN] == 0


def test_un_module_regroupe_ses_operations(widget_plan: ProductPlan) -> None:
    modules = widget_plan.modules()
    assert {plan.operation.id for plan in modules["widget_widget_info"]} == {
        "GetWidget",
        "ListWidgets",
    }


def test_les_operations_sans_module_ne_sont_pas_regroupees(widget_plan: ProductPlan) -> None:
    """Le cycle de vie n'a pas de module, et n'apparaît donc dans aucun."""
    identifiants = {plan.operation.id for plans in widget_plan.modules().values() for plan in plans}
    assert "CreateWidget" not in identifiants
    assert "DeleteWidget" not in identifiants


def test_le_mode_par_defaut_est_automatique(widget_plan: ProductPlan) -> None:
    assert all(plan.mode is GenerationMode.AUTO for plan in widget_plan.operations)


def test_la_portee_traverse_le_plan(widget_plan: ProductPlan) -> None:
    assert all(plan.operation.scope is Scope.ZONE for plan in widget_plan.operations)
