"""Le modèle intermédiaire porte les décisions, et les porte une seule fois."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.collection import Collection
from generator.ansible.models import (
    DEPRECATED_NOTICE,
    UNDOCUMENTED,
    AmbiguousModule,
    ModuleModelError,
    UnknownChoice,
    UnreachableState,
    UnsupportedKind,
    _unitary_read_operation,
    build_module_spec,
    build_module_specs,
)
from generator.ir.enums import ApiType, HTTPMethod, OperationKind, ParameterLocation, Scope
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


# --- le sélecteur ----------------------------------------------------------


def test_lidentifiant_du_get_devient_le_selecteur(instance_plan: ProductPlan) -> None:
    """`server_id` distingue GetServer de ListServers : c'est lui qui bascule."""
    spec = _spec(instance_plan, "instance_server_info")
    assert spec.selector == "server_id"
    assert spec.get_operation is not None and spec.get_operation.id == "GetServer"
    assert spec.list_operation is not None and spec.list_operation.id == "ListServers"


def test_le_selecteur_nest_pas_obligatoire_mais_la_zone_lest(instance_plan: ProductPlan) -> None:
    """Sans `server_id`, le module liste ; il ne peut donc pas être requis."""
    options = {
        option.name: option for option in _spec(instance_plan, "instance_server_info").options
    }
    assert options["server_id"].required is False
    assert options["zone"].required is True


def test_un_module_sans_liste_na_pas_de_selecteur(widget_plan: ProductPlan) -> None:
    spec = _spec(widget_plan, "widget_widget_gizmo_info")
    assert spec.list_operation is not None
    assert spec.get_operation is None
    assert spec.selector is None


def test_un_identifiant_ambigu_est_refuse_plutot_que_choisi() -> None:
    """Deux identifiants candidats : le modèle ne devine pas lequel bascule."""
    zone = ApiParameter(
        name="zone", type=ApiType.STRING, required=True, location=ParameterLocation.PATH
    )
    parent = ApiParameter(
        name="parent_id", type=ApiType.STRING, required=True, location=ParameterLocation.PATH
    )
    enfant = ApiParameter(
        name="thing_id", type=ApiType.STRING, required=True, location=ParameterLocation.PATH
    )
    get = ApiOperation(
        id="GetThing",
        service="demo",
        version="v1",
        resource="thing",
        http_method=HTTPMethod.GET,
        path="/demo/v1/zones/{zone}/parents/{parent_id}/things/{thing_id}",
        scope=Scope.ZONE,
        parameters=(zone, parent, enfant),
        response=ApiResponse(payload_field="thing"),
    )
    liste = ApiOperation(
        id="ListThings",
        service="demo",
        version="v1",
        resource="thing",
        http_method=HTTPMethod.GET,
        path="/demo/v1/zones/{zone}/things",
        scope=Scope.ZONE,
        parameters=(zone,),
        response=ApiResponse(payload_field="things", is_list=True),
    )
    service = ApiService(name="demo", version="v1", operations=(get, liste))
    plan = plan_service(service, OverrideSet(source=None))

    with pytest.raises(AmbiguousModule):
        _spec(plan, "demo_thing_info")


# --- ce qui ne devient pas une option --------------------------------------


def test_la_pagination_nest_pas_exposee(instance_plan: ProductPlan) -> None:
    """Exposer `page` permettrait de rendre une première page en silence."""
    spec = _spec(instance_plan, "instance_server_info")
    noms = {option.name for option in spec.options}
    assert "page" not in noms
    assert "per_page" not in noms
    assert spec.list_operation is not None
    assert spec.list_operation.page_param == "page"
    assert "page" not in spec.list_operation.query_params


def test_un_parametre_commun_nest_pas_redeclare_mais_reste_envoye() -> None:
    """`project_id` vient du module_utils ; le runtime l'enverra quand même."""
    zone = ApiParameter(
        name="zone", type=ApiType.STRING, required=True, location=ParameterLocation.PATH
    )
    projet = ApiParameter(
        name="project_id", type=ApiType.STRING, required=False, location=ParameterLocation.QUERY
    )
    liste = ApiOperation(
        id="ListThings",
        service="demo",
        version="v1",
        resource="thing",
        http_method=HTTPMethod.GET,
        path="/demo/v1/zones/{zone}/things",
        scope=Scope.ZONE,
        parameters=(zone, projet),
        response=ApiResponse(payload_field="things", is_list=True),
    )
    service = ApiService(name="demo", version="v1", operations=(liste,))
    spec = _spec(plan_service(service, OverrideSet(source=None)), "demo_thing_info")

    assert "project_id" not in {option.name for option in spec.options}
    assert spec.list_operation is not None
    assert "project_id" in spec.list_operation.query_params


def test_un_enum_du_contrat_ne_devient_pas_un_defaut(instance_plan: ProductPlan) -> None:
    """`state` vaudrait `running` par défaut, et masquerait les autres serveurs."""
    spec = _spec(instance_plan, "instance_server_info")
    etat = next(option for option in spec.options if option.name == "state")
    assert etat.default is None
    assert "default" not in spec.argument_spec()["state"]
    assert "running" in etat.choices


# --- une seule source pour la doc et pour l'argument_spec -------------------


def test_la_documentation_decrit_exactement_les_options(instance_plan: ProductPlan) -> None:
    spec = _spec(instance_plan, "instance_server_info")
    documentees = spec.documentation()["options"]
    declarees = spec.argument_spec()

    assert set(documentees) == set(declarees)
    for nom, option in documentees.items():
        assert option["type"] == declarees[nom]["type"]
        assert option.get("required") == declarees[nom].get("required")
        assert option.get("choices") == declarees[nom].get("choices")


def test_la_zone_porte_les_dix_valeurs_du_contrat(instance_plan: ProductPlan) -> None:
    spec = _spec(instance_plan, "instance_server_info")
    zone = next(option for option in spec.options if option.name == "zone")
    assert len(zone.choices) == 10
    assert "fr-par-1" in zone.choices


def test_les_descriptions_viennent_du_contrat(instance_plan: ProductPlan) -> None:
    spec = _spec(instance_plan, "instance_server_info")
    serveur = next(option for option in spec.options if option.name == "server_id")
    assert serveur.description == ("UUID of the Instance you want to get.",)


def test_une_description_absente_est_dite_absente(widget_plan: ProductPlan) -> None:
    """Le contrat de laboratoire ne décrit pas `widget_id`, et on ne l'invente pas."""
    spec = _spec(widget_plan, "widget_widget_info")
    identifiant = next(option for option in spec.options if option.name == "widget_id")
    assert identifiant.description == (UNDOCUMENTED,)
    assert any("widget_id" in limite for limite in spec.limits)


def test_un_parametre_deprecie_le_dit(instance_plan: ProductPlan) -> None:
    spec = _spec(instance_plan, "instance_server_info")
    deprecie = next(option for option in spec.options if option.name == "private_ip")
    assert DEPRECATED_NOTICE in deprecie.description


# --- le reste du modèle ----------------------------------------------------


def test_lordre_des_options_raconte_le_module(instance_plan: ProductPlan) -> None:
    """La portée, puis l'identifiant, puis les filtres par ordre alphabétique."""
    noms = [option.name for option in _spec(instance_plan, "instance_server_info").options]
    assert noms[:3] == ["zone", "server_id", "commercial_type"]


def test_la_phrase_courte_nomme_le_produit_et_la_ressource(instance_plan: ProductPlan) -> None:
    spec = _spec(instance_plan, "instance_server_info")
    assert spec.short_description == "Gather information about Scaleway Instance servers"


def test_les_exemples_montrent_les_deux_modes(instance_plan: ProductPlan) -> None:
    spec = _spec(instance_plan, "instance_server_info")
    exemples = spec.examples_documentation()
    assert len(exemples) == 2
    assert "server_id" in exemples[0]["stephrobert.scaleway.instance_server_info"]
    assert "server_id" not in exemples[1]["stephrobert.scaleway.instance_server_info"]


def test_le_retour_distingue_la_lecture_de_la_liste(instance_plan: ProductPlan) -> None:
    retours = _spec(instance_plan, "instance_server_info").return_documentation()
    assert retours["server"]["type"] == "dict"
    assert retours["servers"]["type"] == "list"
    assert "server_id" in retours["server"]["returned"]


# --- ce qui n'est pas rendu est dit, pas effacé ----------------------------


def test_une_classe_sans_renderer_est_ecartee_avec_sa_raison(instance_plan: ProductPlan) -> None:
    specs, ecartes = build_module_specs(instance_plan, COLLECTION)
    raisons = dict(ecartes)
    assert "instance_server" in raisons
    assert "MANAGE" in raisons["instance_server"]
    assert all(spec.kind in (OperationKind.INFO, OperationKind.ACTION) for spec in specs)


def test_un_module_hors_perimetre_est_ecarte_pas_oublie(instance_plan: ProductPlan) -> None:
    specs, ecartes = build_module_specs(instance_plan, COLLECTION, only=("instance_server_info",))
    assert [spec.name for spec in specs] == ["instance_server_info"]
    assert "instance_image_info" in dict(ecartes)
    assert len(specs) + len(ecartes) == len(instance_plan.modules())


def test_un_module_demande_mais_inconnu_leve(instance_plan: ProductPlan) -> None:
    """Une faute de frappe dans le Makefile ne doit pas produire zéro module."""
    with pytest.raises(ModuleModelError):
        build_module_specs(instance_plan, COLLECTION, only=("instance_serveur_info",))


def test_une_classe_non_rendable_leve_quand_on_la_demande(instance_plan: ProductPlan) -> None:
    """MANAGE attend l'étape 4 : le modèle le dit plutôt que de produire à moitié."""
    with pytest.raises(UnsupportedKind):
        _spec(instance_plan, "instance_server")


def test_un_module_de_forme_inconnue_est_ecarte_avec_son_message(
    instance_plan: ProductPlan,
) -> None:
    """Deux listes pour une ressource : le modèle refuse, et le rapport le dit.

    `instance_security_group_rule_info` réunit `ListSecurityGroupRules` et
    `ListDefaultSecurityGroupRules`. Ce n'est pas une erreur du générateur,
    c'est un arbitrage qui n'a pas encore été rendu ; il se lit dans la sortie
    de `generate` plutôt que de faire tomber toute la génération.
    """
    _, ecartes = build_module_specs(instance_plan, COLLECTION)
    raison = dict(ecartes)["instance_security_group_rule_info"]
    assert "2 liste(s)" in raison


def test_un_module_demande_et_impossible_fait_echouer(instance_plan: ProductPlan) -> None:
    """Ce qu'on a demandé sort, ou la commande échoue. Jamais un silence."""
    with pytest.raises(AmbiguousModule):
        build_module_specs(instance_plan, COLLECTION, only=("instance_security_group_rule_info",))


# --- ce qu'un module d'action expose, et ce qu'il refuse -------------------


def test_les_actions_exposees_viennent_de_loverride(instance_plan: ProductPlan) -> None:
    """Le contrat range une suppression et une création dans le même enum.

    `terminate` supprime l'Instance et ses volumes, `backup` crée une image :
    recopier l'enum ferait entrer le cycle de vie par la porte d'une action.
    """
    spec = _spec(instance_plan, "instance_server_action")
    action = next(option for option in spec.options if option.name == "action")
    assert action.choices == ("poweron", "poweroff", "reboot", "stop_in_place")
    assert "terminate" not in action.choices
    assert "backup" not in action.choices


def test_laction_est_obligatoire_bien_que_le_contrat_se_taise(
    instance_plan: ProductPlan,
) -> None:
    """Aucun champ de corps n'est `required` au contrat ; l'override tranche."""
    spec = _spec(instance_plan, "instance_server_action")
    action = next(option for option in spec.options if option.name == "action")
    assert action.required is True


def test_un_parametre_reserve_a_une_action_masquee_disparait(
    instance_plan: ProductPlan,
) -> None:
    """`name` ne sert qu'à `backup`, que le module n'expose pas."""
    spec = _spec(instance_plan, "instance_server_action")
    noms = {option.name for option in spec.options}
    assert {"name", "volumes", "disable_ipv6"} & noms == set()
    assert spec.action_operation is not None
    assert spec.action_operation.body_params == ("action",)
    assert any("masqué" in limite for limite in spec.limits)


def test_la_description_ne_promet_que_les_actions_exposees(
    instance_plan: ProductPlan,
) -> None:
    """Une doc qui annonce ce que l'argument_spec refuse est un mensonge."""
    texte = "\n".join(_spec(instance_plan, "instance_server_action").description)
    assert "`poweroff`" in texte
    assert "`terminate`" not in texte
    assert "`backup`" not in texte


def test_letat_attendu_vient_de_loverride(instance_plan: ProductPlan) -> None:
    """Le contrat ne dit jamais dans quel état une action laisse la ressource.

    `stop_in_place` attend `stopped in place` et non `stopped` : le contrat
    déclare les deux, et ce sont des états **distincts**. Ce test affirmait
    `stopped` jusqu'à ce qu'on joue l'action : le module échouait alors après
    `wait_timeout` sur une Instance pourtant bien arrêtée. Un test peut encoder
    un bug aussi fidèlement qu'il encode une décision.
    """
    spec = _spec(instance_plan, "instance_server_action")
    assert dict(spec.wait_states) == {
        "poweron": "running",
        "reboot": "running",
        "poweroff": "stopped",
        "stop_in_place": "stopped in place",
    }
    assert spec.read_operation is not None
    assert spec.read_operation.id == "GetServer"
    assert spec.waitable is True


def test_un_etat_attendu_hors_du_contrat_est_refuse(instance_plan: ProductPlan) -> None:
    """Une faute de frappe dans un override produit une attente jamais satisfaite.

    Le module rendu attend alors un état que l'API n'atteindra jamais, et
    échoue après `wait_timeout` sur une ressource qui a pourtant bien changé.
    L'enum se déduit du contrat sans deviner : `<schéma>.<Champ>`.
    """
    from dataclasses import replace

    plan = instance_plan
    override = plan.overrides.operations["instance.v1.Server.ServerAction"]
    faute = replace(override, wait=replace(override.wait, states={"poweroff": "stoped"}))
    casse = replace(
        plan,
        overrides=replace(
            plan.overrides,
            operations={**plan.overrides.operations, "instance.v1.Server.ServerAction": faute},
        ),
    )

    with pytest.raises(UnreachableState) as erreur:
        _spec(casse, "instance_server_action")

    assert "stoped" in str(erreur.value)
    assert "stopped in place" in str(erreur.value)


def test_un_module_daction_sans_override_expose_le_contrat(widget_plan: ProductPlan) -> None:
    """Sans arbitrage, le module prend l'enum tel quel et n'attend rien."""
    spec = _spec(widget_plan, "widget_widget_action")
    action = next(option for option in spec.options if option.name == "action")
    assert action.choices == ("poweron", "poweroff", "reboot")
    assert spec.wait_states == ()
    assert spec.read_operation is None
    assert spec.waitable is False


def test_une_valeur_hors_du_contrat_est_refusee(instance_plan: ProductPlan) -> None:
    """Une valeur retenue que le contrat ne déclare plus : l'API a bougé."""
    from generator.overrides.loader import OperationOverride, OverrideSet, ParameterOverride

    fautif = OverrideSet(
        source=None,
        operations={
            "instance.v1.Server.ServerAction": OperationOverride(
                key="instance.v1.Server.ServerAction",
                parameters={
                    "action": ParameterOverride(
                        name="action", choices=("poweron", "self_destruct"), reason="essai"
                    )
                },
            )
        },
    )
    with pytest.raises(UnknownChoice) as erreur:
        build_module_spec(
            "instance_server_action",
            instance_plan.modules()["instance_server_action"],
            instance_plan.service,
            COLLECTION,
            fautif,
        )
    assert "self_destruct" in str(erreur.value)


def test_un_etat_promis_pour_une_action_non_exposee_est_refuse(
    instance_plan: ProductPlan,
) -> None:
    """Attendre un état après une action qu'on ne déclenche pas n'a pas de sens."""
    from generator.overrides.loader import (
        OperationOverride,
        OverrideSet,
        ParameterOverride,
        WaitOverride,
    )

    fautif = OverrideSet(
        source=None,
        operations={
            "instance.v1.Server.ServerAction": OperationOverride(
                key="instance.v1.Server.ServerAction",
                parameters={
                    "action": ParameterOverride(name="action", choices=("poweron",), reason="essai")
                },
                wait=WaitOverride(field="state", states={"terminate": "gone"}, reason="essai"),
            )
        },
    )
    with pytest.raises(UnreachableState) as erreur:
        build_module_spec(
            "instance_server_action",
            instance_plan.modules()["instance_server_action"],
            instance_plan.service,
            COLLECTION,
            fautif,
        )
    assert "terminate" in str(erreur.value)


# --- la lecture unitaire, quelle que soit la forme de sa réponse ------------


def _lecture(payload_field: str | None, schema: str | None) -> ApiService:
    """Un service d'une seule opération : un GET sur une ressource."""
    return ApiService(
        name="labo",
        version="v1",
        operations=(
            ApiOperation(
                id="GetChose",
                service="labo",
                version="v1",
                resource="chose",
                http_method=HTTPMethod.GET,
                path="/labo/v1/choses/{chose_id}",
                scope=Scope.ZONE,
                parameters=(
                    ApiParameter(
                        name="chose_id",
                        type=ApiType.STRING,
                        required=True,
                        location=ParameterLocation.PATH,
                    ),
                ),
                response=ApiResponse(schema=schema, payload_field=payload_field),
            ),
        ),
    )


def test_une_lecture_qui_repond_par_le_corps_reste_une_lecture() -> None:
    """`payload_field` vaut `None` quand la réponse **est** la ressource.

    Le parser distingue une enveloppe `GetXxxResponse` d'une ressource rendue
    telle quelle, et pose `payload_field=None` sur la seconde : c'est correct,
    le corps entier est la ressource et `fetch_one` le rend déjà ainsi.

    Exiger un `payload_field` privait ces ressources de toute lecture unitaire,
    donc de toute attente d'état et de toute comparaison avant écriture.
    Mesuré : 5 lectures sur Instance et 9 sur le Load Balancer sont dans ce cas,
    `GetBackend` rend un `Backend` et `GetLb` rend un `Lb`.
    """
    service = _lecture(payload_field=None, schema="labo.v1.Chose")
    trouvee = _unitary_read_operation(service, "chose")
    assert trouvee is not None
    assert trouvee.id == "GetChose"


def test_une_lecture_par_enveloppe_reste_trouvee() -> None:
    """Le cas voisin, qui ne doit pas bouger."""
    service = _lecture(payload_field="chose", schema="labo.v1.GetChoseResponse")
    trouvee = _unitary_read_operation(service, "chose")
    assert trouvee is not None


def test_une_reponse_qui_ne_decrit_rien_nest_pas_une_lecture() -> None:
    """Ce qui reste exigé : qu'il y ait quelque chose à lire.

    Sans schéma ni champ porteur, la réponse ne décrit rien, et un module qui
    l'attendrait comparerait le vide au vide.
    """
    service = _lecture(payload_field=None, schema=None)
    assert _unitary_read_operation(service, "chose") is None
