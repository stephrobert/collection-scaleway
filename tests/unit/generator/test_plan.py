"""Le plan compte ce qu'il compte, et ne maquille pas la mesure."""

from __future__ import annotations

import pytest

from generator.ir.enums import GenerationMode, HTTPMethod, OperationKind, Scope
from generator.ir.models import ApiOperation, ApiService
from generator.overrides.loader import OverrideSet
from generator.plan import ModulesEnCollision, ProductPlan, plan_service


def _lecture(resource: str, operation_id: str) -> ApiOperation:
    """Une lecture minimale, juste de quoi que le plan la classe en INFO."""
    return ApiOperation(
        id=operation_id,
        service="vpc",
        version="v2",
        resource=resource,
        http_method=HTTPMethod.GET,
        path=f"/vpc/v2/{resource}s",
        scope=Scope.REGION,
    )


def test_deux_ressources_sous_un_meme_nom_de_module_sont_refusees() -> None:
    """La déduplication du préfixe rend `X` et `<produit>_X` atteignables.

    Tant que le nom valait `<produit>_<ressource>`, deux ressources distinctes ne
    pouvaient pas se rencontrer. Depuis qu'il se déduplique, elles le peuvent, et
    le générateur écrirait deux fois le même fichier, le second effaçant le
    premier sans un mot. Le cas n'est pas théorique : `lb` porte déjà `backend`
    et `lb_backend`, aujourd'hui sans module l'une comme l'autre.
    """
    service = ApiService(
        name="vpc",
        version="v2",
        operations=(_lecture("connector", "ListConnectors"), _lecture("vpc_connector", "GetVPC")),
    )
    with pytest.raises(ModulesEnCollision) as capture:
        plan_service(service, OverrideSet(source=None))

    assert capture.value.module == "vpc_connector_info"
    assert capture.value.resources == ("connector", "vpc_connector")


def test_plusieurs_operations_sur_une_meme_ressource_partagent_leur_module() -> None:
    """Le cas voisin, et c'est le cas normal : `GetVPC` et `ListVPCs` sont un module.

    La garde porte sur deux **ressources** sous un nom, jamais sur deux
    opérations : la confondre avec celle-ci ferait échouer tout produit réel.
    """
    service = ApiService(
        name="vpc",
        version="v2",
        operations=(_lecture("vpc", "ListVPCs"), _lecture("vpc", "GetVPC")),
    )
    plan = plan_service(service, OverrideSet(source=None))
    assert sorted(plan.modules()) == ["vpc_info"]


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
    """Le contrat de laboratoire nomme sa ressource comme son produit.

    Il portait donc le défaut du préfixe répété avant `vpc`, et cette attente
    disait `widget_widget_info` sans que personne y voie autre chose qu'un nom.
    """
    modules = widget_plan.modules()
    assert {plan.operation.id for plan in modules["widget_info"]} == {
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
