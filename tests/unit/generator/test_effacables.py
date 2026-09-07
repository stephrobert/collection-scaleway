"""Un champ effaçable est exposé de façon qu'un `null` explicite se voie.

Le contrat dit `oneOf: [T, null]` ; Ansible, lui, rend `None` pour une option
absente comme pour une option à `null`. Le seul mécanisme public qui les
sépare, mesuré sur chaque version d'ansible-core que la CI éprouve, est un
défaut marqueur sur une option `raw` (ADR-012). Ces tests portent sur ce que
le modèle en fait : quelles options le reçoivent, ce que la page en dit, et ce
que le runtime reçoit pour rendre à la valeur son type.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.collection import Collection
from generator.ansible.mapping import UNCHANGED
from generator.ansible.models import ConflictingOption, build_module_spec
from generator.ir.enums import ApiType, HTTPMethod, ParameterLocation, Scope
from generator.ir.models import ApiOperation, ApiParameter, ApiResponse, ApiService
from generator.overrides.loader import OverrideSet
from generator.plan import ProductPlan, plan_service

COLLECTION = Collection(
    namespace="stephrobert",
    name="scaleway",
    version="0.1.0",
    path=Path("ansible_collections/stephrobert/scaleway"),
    authors=("Quelqu'un (@quelquun)",),
)


def _spec(plan: ProductPlan, module: str):  # type: ignore[no-untyped-def]
    return build_module_spec(
        module, plan.modules()[module], plan.service, COLLECTION, plan.overrides
    )


def _plan(*corps: ApiParameter) -> ProductPlan:
    """Une ressource lue et modifiée, dont le corps d'écriture est donné."""
    zone = ApiParameter(
        name="zone", type=ApiType.STRING, required=True, location=ParameterLocation.PATH
    )
    thing_id = ApiParameter(
        name="thing_id", type=ApiType.STRING, required=True, location=ParameterLocation.PATH
    )
    lecture = ApiOperation(
        id="GetThing",
        service="demo",
        version="v1",
        resource="thing",
        http_method=HTTPMethod.GET,
        path="/demo/v1/zones/{zone}/things/{thing_id}",
        scope=Scope.ZONE,
        parameters=(zone, thing_id),
        response=ApiResponse(payload_field="thing", payload_schema="Thing"),
    )
    ecriture = ApiOperation(
        id="UpdateThing",
        service="demo",
        version="v1",
        resource="thing",
        http_method=HTTPMethod.PATCH,
        path="/demo/v1/zones/{zone}/things/{thing_id}",
        scope=Scope.ZONE,
        parameters=(zone, thing_id, *corps),
        response=ApiResponse(payload_field="thing", payload_schema="Thing"),
    )
    service = ApiService(name="demo", version="v1", operations=(lecture, ecriture))
    return plan_service(service, OverrideSet(source=None))


def _options(spec):  # type: ignore[no-untyped-def]
    return {option.name: option for option in spec.options}


# --- sur le contrat de laboratoire ------------------------------------------


def test_un_champ_effacable_gere_est_expose_en_raw_avec_le_marqueur(
    widget_plan: ProductPlan,
) -> None:
    """Les champs que le contrat de laboratoire déclare effaçables, et eux seuls."""
    spec = _spec(widget_plan, "widget_widget")
    options = _options(spec)

    for nom in ("email_config", "secret_token", "webhook_config"):
        assert options[nom].type == "raw", nom
        assert options[nom].default == UNCHANGED, nom
    assert options["secret_token"].no_log is True, "le secret reste masqué"
    assert options["protected"].type == "bool", "un champ non effaçable ne bouge pas"
    assert spec.nullable_params == (
        ("email_config", {"type": "dict"}),
        ("secret_token", {"type": "str"}),
        ("webhook_config", {"type": "dict"}),
    )


def test_la_page_dit_le_type_reel_et_ce_que_le_marqueur_veut_dire(widget_plan: ProductPlan) -> None:
    """`raw` et un défaut qui n'en est pas un : sans ces phrases, la page perd le type."""
    option = _options(_spec(widget_plan, "widget_widget"))["secret_token"]
    texte = " ".join(option.description)

    assert "API type is str" in texte
    assert "explicit null is refused" in texte
    assert texte.startswith("Jeton de rotation."), "la description du contrat reste en tête"


def test_un_champ_non_effacable_ne_recoit_pas_le_marqueur(widget_plan: ProductPlan) -> None:
    """Le contre-exemple, sans lequel le premier test passerait aussi sur un
    modèle qui marquerait tout."""
    option = _options(_spec(widget_plan, "widget_widget"))["protected"]

    assert option.default is None
    assert "explicit null" not in " ".join(option.description)


# --- sur des formes que le laboratoire ne déclare pas -----------------------


def test_les_choix_et_les_elements_quittent_loption_publiee_pour_le_runtime() -> None:
    """Ansible vérifierait le marqueur contre les choix, et refuserait chaque
    appel où l'option est omise : mesuré. Les choix vont donc au runtime, et
    la page les dit en clair."""
    plan = _plan(
        ApiParameter(
            name="mode",
            type=ApiType.ENUM,
            required=False,
            location=ParameterLocation.BODY,
            enum_values=("fast", "slow"),
            nullable=True,
        ),
        ApiParameter(
            name="tags",
            type=ApiType.ARRAY,
            required=False,
            location=ParameterLocation.BODY,
            item_type=ApiType.STRING,
            nullable=True,
        ),
    )
    spec = _spec(plan, "demo_thing")
    options = _options(spec)

    assert options["mode"].choices == ()
    assert options["tags"].elements is None
    assert "Accepted values: fast, slow." in options["mode"].description
    assert "API type is list of str" in " ".join(options["tags"].description)
    assert dict(spec.nullable_params) == {
        "mode": {"type": "str", "choices": ["fast", "slow"]},
        "tags": {"type": "list", "elements": "str"},
    }


def test_un_champ_effacable_avec_un_defaut_du_contrat_est_refuse() -> None:
    """Le marqueur écraserait le défaut du contrat : aucun cas ne l'a demandé,
    et le perdre en silence serait pire que refuser."""
    plan = _plan(
        ApiParameter(
            name="size",
            type=ApiType.INTEGER,
            required=False,
            location=ParameterLocation.BODY,
            default=10,
            nullable=True,
        )
    )

    with pytest.raises(ConflictingOption, match="size"):
        _spec(plan, "demo_thing")
