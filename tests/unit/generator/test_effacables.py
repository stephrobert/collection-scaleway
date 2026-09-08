"""Un champ effaçable garde son type, et la page dit comment l'effacer.

Le contrat dit `oneOf: [T, null]` ; Ansible, lui, rend `None` pour une option
absente comme pour une option à `null`. Ce qui les sépare est un **témoin
d'omission** : Ansible n'appelle un `fallback` que sur une clé absente de
l'invocation, et un fallback qui lève `AnsibleFallbackNotFound` note le nom sans
rien injecter (ADR-016).

Ces tests portent sur ce que le modèle en fait. La forme publiée ne change pas :
c'est tout l'intérêt, et c'est ce qu'ils mesurent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.collection import Collection
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


def test_un_champ_effacable_est_nomme_au_runtime(widget_plan: ProductPlan) -> None:
    """Les champs que le contrat de laboratoire déclare effaçables, et eux seuls.

    Rien que leurs noms : c'est sur l'entrée que le module publie déjà que le
    runtime pose son témoin, et une seconde description du même type n'aurait
    servi qu'à diverger de la première.
    """
    spec = _spec(widget_plan, "widget_widget")

    assert spec.nullable_params == (
        "email_config",
        "protected",
        "secret_token",
        "tags",
        "webhook_config",
    )


def test_un_champ_effacable_garde_son_type_publie(widget_plan: ProductPlan) -> None:
    """C'est ce que le changement achète, et c'est donc ce qu'il faut mesurer.

    Ces options étaient publiées en `raw` avec un défaut `__unchanged__`, que
    `validate-modules` obligeait à publier tel quel : le lecteur de la page
    voyait un type qui n'existe pas et un défaut qui n'en était pas un.
    """
    options = _options(_spec(widget_plan, "widget_widget"))

    assert options["secret_token"].type == "str"
    assert options["protected"].type == "bool"
    assert options["tags"].type == "list"
    assert options["tags"].elements == "str"
    assert options["email_config"].type == "dict"
    for nom in ("secret_token", "protected", "tags", "email_config"):
        assert options[nom].default is None, f"{nom} ne porte aucun marqueur"
    assert options["secret_token"].no_log is True, "le secret reste masqué"


def test_la_page_dit_la_valeur_vide_du_type(widget_plan: ProductPlan) -> None:
    """Le critère du dépôt est qu'un module se comprenne depuis sa seule page.

    La valeur à écrire dépend du type, et la page l'écrit littéralement plutôt
    que de parler de « la valeur vide » : un lecteur copie ce qu'il voit.
    """
    options = _options(_spec(widget_plan, "widget_widget"))

    assert 'write `secret_token: ""`' in " ".join(options["secret_token"].description)
    assert "write `tags: []`" in " ".join(options["tags"].description)
    assert "write `email_config: {}`" in " ".join(options["email_config"].description)
    assert options["secret_token"].description[0] == "Jeton de rotation.", (
        "la description du contrat reste en tête"
    )


def test_la_page_refuse_de_promettre_un_effacement_impossible(
    widget_plan: ProductPlan,
) -> None:
    """`protected` est un booléen : il n'a pas de valeur vide.

    Écrire « pour effacer, mettre `false` » serait promettre un effacement que
    l'API ne fait pas : `false` est une valeur, pas une absence.
    """
    texte = " ".join(_options(_spec(widget_plan, "widget_widget"))["protected"].description)

    assert "bool has no empty value" in texte
    assert "cannot clear it" in texte
    assert "write `protected:" not in texte


def test_la_page_dit_partout_que_null_est_refuse(widget_plan: ProductPlan) -> None:
    """Mesuré sur le compte réel : l'API accepte le `null` et ne change rien.

    Un lecteur qui écrit `null` en attendant un effacement doit le lire sur la
    page, pas le découvrir sur un module qui échoue.
    """
    options = _options(_spec(widget_plan, "widget_widget"))

    for nom in ("secret_token", "protected", "tags", "email_config", "webhook_config"):
        assert "Setting it to null is refused" in " ".join(options[nom].description), nom


def test_un_champ_non_effacable_ne_recoit_rien(widget_plan: ProductPlan) -> None:
    """Le contre-exemple, sans lequel les tests ci-dessus passeraient aussi sur
    un modèle qui traiterait toutes les options de la même façon.

    Il portait sur `protected` jusqu'à ce que le parser lise la nullabilité
    derrière un `$ref` : `google.protobuf.BoolValue` est effaçable, et le
    contrat de laboratoire a reçu `label` pour que le contre-exemple existe
    encore.
    """
    option = _options(_spec(widget_plan, "widget_widget"))["label"]

    assert option.type == "str"
    assert option.default is None
    assert "clear" not in " ".join(option.description)
    assert "null" not in " ".join(option.description)


# --- sur des formes que le laboratoire ne déclare pas -----------------------


def test_les_choix_et_les_elements_restent_sur_loption_publiee() -> None:
    """Ils avaient dû quitter la page : Ansible vérifiait le marqueur contre les
    choix et refusait chaque appel où l'option était omise. Sans marqueur, ils
    reviennent là où un lecteur les cherche."""
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

    assert options["mode"].choices == ("fast", "slow")
    assert options["tags"].elements == "str"
    assert spec.nullable_params == ("mode", "tags")


def test_un_champ_effacable_avec_un_defaut_du_contrat_est_refuse() -> None:
    """Avec un défaut, Ansible convertit un `null` explicite vers le type de
    l'option : l'effacement deviendrait indistinguable d'une valeur vide.

    Le test qui mesure ce fait sur Ansible lui-même est
    `test_un_defaut_ferait_lire_un_null_comme_une_valeur_vide`, dans les tests
    de collection. Ici, seule la conséquence est vérifiée : le générateur
    refuse plutôt que de produire un module ambigu.
    """
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
