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


def test_une_couverture_construite_sans_operation_day2_est_indefinie() -> None:
    """Le second ratio obéit à la même règle : indéfini n'est pas nul."""
    vide = plan_service(ApiService(name="vide", version="v1"), OverrideSet(source=None))
    assert vide.built_coverage(("un_module",)) is None


def test_classee_nest_pas_portee_par_un_module(widget_plan: ProductPlan) -> None:
    """Les deux ratios ne mesurent pas la même chose, et le mot le disait mal.

    `coverage` dit ce que la classification autorise ; `built_coverage` dit ce
    qu'un module écrit porte. Publier le premier en écrivant « générables »
    laissait entendre qu'un module existe. Sans aucun module écrit, la
    couverture construite vaut zéro pendant que la classée reste entière.
    """
    assert widget_plan.coverage() is not None
    assert widget_plan.built_coverage(()) == 0.0
    assert widget_plan.built_coverage(()) != widget_plan.coverage()


def test_la_couverture_construite_ne_compte_que_les_modules_nommes(
    widget_plan: ProductPlan,
) -> None:
    """Un module hors de la liste ne compte pas, même s'il est au plan.

    `written` vient de l'appelant : c'est le modèle Ansible qui sait quels
    modules ont été construits, et le périmètre demandé peut en écarter.
    """
    modules = widget_plan.modules()
    assert modules, "le contrat de laboratoire doit produire au moins un module"

    day2_ids = {plan.operation.id for plan in widget_plan.day2}
    porteurs = [
        nom
        for nom, plans in modules.items()
        if any(item.operation.id in day2_ids for item in plans)
    ]
    assert porteurs, "au moins un module doit porter une opération Day-2"

    partielle = widget_plan.built_coverage((porteurs[0],))
    totale = widget_plan.built_coverage(tuple(porteurs))
    assert 0.0 < partielle <= totale
    assert widget_plan.built_coverage(("module_qui_nexiste_pas",)) == 0.0


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
