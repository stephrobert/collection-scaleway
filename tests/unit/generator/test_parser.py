"""Le parser traduit le contrat sans rien perdre ni rien inventer."""

from __future__ import annotations

import pytest

from generator.ir.enums import ApiType, ParameterLocation, Scope
from generator.ir.models import ApiService
from generator.parser.openapi import ParseError, parse_document
from generator.source.base import SpecDocument, VendoredSpecSource

from .conftest import WIDGET_SPECS


def test_toutes_les_operations_du_contrat_sont_dans_lir(widget_service: ApiService) -> None:
    assert {operation.id for operation in widget_service.operations} == {
        "ListWidgets",
        "CreateWidget",
        "GetWidget",
        "UpdateWidget",
        "DeleteWidget",
        "WidgetAction",
        "ListWidgetGizmos",
    }


def test_la_portee_se_lit_dans_le_chemin(widget_service: ApiService) -> None:
    for operation in widget_service.operations:
        assert operation.scope is Scope.ZONE
        assert operation.scope_parameter == "zone"


def test_les_parametres_de_chemin_sont_requis(widget_service: ApiService) -> None:
    operation = widget_service.operation("GetWidget")
    assert operation is not None
    zone = operation.parameter("zone")
    assert zone is not None
    assert zone.required is True
    assert zone.location is ParameterLocation.PATH
    assert zone.type is ApiType.ENUM
    assert zone.enum_values == ("fr-par-1", "nl-ams-1")


def test_un_enum_reference_est_enregistre_une_fois(widget_service: ApiService) -> None:
    names = [enum.name for enum in widget_service.enums]
    assert names == sorted(names), "les enums doivent sortir triés, pour un IR déterministe"
    assert "scaleway.widget.v1.Widget.Action" in names

    action = widget_service.operation("WidgetAction")
    assert action is not None
    parameter = action.parameter("action")
    assert parameter is not None
    assert parameter.type is ApiType.ENUM
    assert parameter.enum_name == "scaleway.widget.v1.Widget.Action"
    assert parameter.enum_values == ("poweron", "poweroff", "reboot")
    assert parameter.location is ParameterLocation.BODY


def test_un_champ_de_corps_devient_un_parametre(widget_service: ApiService) -> None:
    operation = widget_service.operation("UpdateWidget")
    assert operation is not None
    noms = {parameter.name for parameter in operation.parameters}
    assert {"zone", "widget_id", "tags", "protected", "secret_token"} <= noms


def test_un_type_nullable_openapi_31_garde_son_type_utile(widget_service: ApiService) -> None:
    """`["boolean", "null"]` est un booléen optionnel, pas un type inconnu."""
    operation = widget_service.operation("UpdateWidget")
    assert operation is not None
    protege = operation.parameter("protected")
    assert protege is not None
    assert protege.type is ApiType.BOOLEAN


def test_un_tableau_sans_items_est_signale_et_non_devine(widget_service: ApiService) -> None:
    operation = widget_service.operation("UpdateWidget")
    assert operation is not None
    tags = operation.parameter("tags")
    assert tags is not None
    assert tags.type is ApiType.ARRAY
    assert tags.item_type is None, "le contrat ne dit pas le type des éléments"
    assert any("tags" in warning and "items" in warning for warning in widget_service.warnings)


def test_la_pagination_se_deduit_des_parametres(widget_service: ApiService) -> None:
    liste = widget_service.operation("ListWidgets")
    unite = widget_service.operation("GetWidget")
    assert liste is not None and unite is not None
    assert liste.pagination is not None
    assert liste.pagination.page_param == "page"
    assert unite.pagination is None


def test_un_oneof_avec_null_est_un_champ_optionnel(widget_service: ApiService) -> None:
    """`oneOf: [X, null]` veut dire « un X, ou rien », pas une union de formes.

    C'est la façon dont Scaleway écrit un champ optionnel, et les 24 occurrences
    du contrat du Load Balancer ont toutes exactement cette forme. Les traiter
    comme un type non traité laissait `UpdateSubscriber` sans type et écartait
    un module Day-2 entier.
    """
    operation = widget_service.operation("UpdateWidget")
    assert operation is not None
    champ = operation.parameter("email_config")
    assert champ is not None
    assert champ.type is ApiType.OBJECT
    assert champ.ref == "scaleway.widget.v1.Widget.EmailConfig"
    assert not [w for w in widget_service.warnings if "email_config" in w]


def test_une_taille_de_page_ecrite_autrement_reste_de_la_pagination(
    widget_service: ApiService,
) -> None:
    """Scaleway emploie deux orthographes, et n'en connaître qu'une coûte cher.

    Instance pagine avec `per_page`, le Load Balancer avec `page_size`. Une
    règle qui n'en connaît qu'une ne déclare pas l'opération paginée : ses
    paramètres de pagination deviennent des options du module, et la liste rend
    sa **première page en silence**. Onze opérations de `lb.v1` étaient dans ce
    cas.
    """
    gizmos = widget_service.operation("ListWidgetGizmos")
    assert gizmos is not None
    assert gizmos.pagination is not None
    assert gizmos.pagination.page_param == "page"
    assert gizmos.pagination.per_page_param == "page_size"


def test_lorthographe_dorigine_nest_pas_perdue(widget_service: ApiService) -> None:
    """Le cas voisin qui ne doit pas bouger : `per_page` reste `per_page`."""
    widgets = widget_service.operation("ListWidgets")
    assert widgets is not None
    assert widgets.pagination is not None
    assert widgets.pagination.per_page_param == "per_page"


def test_total_count_absent_du_contrat_nest_pas_invente(widget_service: ApiService) -> None:
    """Le SDK expose `total_count` ; le document publié ne le déclare pas."""
    liste = widget_service.operation("ListWidgets")
    assert liste is not None
    assert liste.pagination is not None
    assert liste.pagination.total_count_field is None


def test_une_reponse_qui_est_la_ressource_ne_rend_pas_une_liste(
    widget_service: ApiService,
) -> None:
    """Le premier tableau du schéma n'est pas toujours la charge utile.

    `UpdateWidget` répond par la ressource `Widget`, pas par une enveloppe. Le
    premier tableau qu'on y rencontre est `tags`, et la règle « le premier
    tableau gagne » décrivait donc l'opération comme rendant **une liste de
    tags**. L'IR est le produit de ce dépôt : un module rendu depuis cette
    description lirait `tags` en croyant lire la ressource.

    Reproduit du contrat réel, où `UpdatePrivateNIC` répond par `PrivateNIC`.
    """
    operation = widget_service.operation("UpdateWidget")
    assert operation is not None
    assert operation.response is not None
    assert operation.response.schema == "scaleway.widget.v1.Widget"
    assert operation.response.is_list is False, "la réponse est la ressource, pas une liste"
    assert operation.response.payload_field != "tags"


def test_une_enveloppe_reste_reconnue_comme_telle(widget_service: ApiService) -> None:
    """Le cas voisin qui ne doit pas bouger : une enveloppe porte bien sa liste."""
    liste = widget_service.operation("ListWidgets")
    assert liste is not None
    assert liste.response is not None
    assert liste.response.schema == "scaleway.widget.v1.ListWidgetsResponse"
    assert liste.response.payload_field == "widgets"
    assert liste.response.is_list is True


def test_la_reponse_designe_le_champ_utile(widget_service: ApiService) -> None:
    liste = widget_service.operation("ListWidgets")
    unite = widget_service.operation("GetWidget")
    assert liste is not None and unite is not None

    assert liste.response is not None
    assert liste.response.payload_field == "widgets"
    assert liste.response.is_list is True

    assert unite.response is not None
    assert unite.response.payload_field == "widget"
    assert unite.response.is_list is False


def test_la_description_garde_le_premier_paragraphe(widget_service: ApiService) -> None:
    assert widget_service.description == "Un produit de test."


def test_la_ressource_est_stable_avec_ou_sans_identifiant(widget_service: ApiService) -> None:
    par_operation = {operation.id: operation.resource for operation in widget_service.operations}
    assert par_operation["ListWidgets"] == "widget"
    assert par_operation["GetWidget"] == "widget"
    assert par_operation["WidgetAction"] == "widget"
    assert par_operation["ListWidgetGizmos"] == "widget_gizmo"


def test_un_document_sans_chemin_est_refuse(tmp_path) -> None:
    document = SpecDocument(
        product="vide", version="v1", path=tmp_path / "vide.v1.yml", document={"openapi": "3.1.0"}
    )
    with pytest.raises(ParseError):
        parse_document(document)


def test_le_parsing_est_deterministe() -> None:
    """Deux lectures du même contrat produisent le même IR, octet pour octet."""
    source = VendoredSpecSource(root=WIDGET_SPECS)
    premier = parse_document(source.load("widget", "v1")).to_json()
    second = parse_document(source.load("widget", "v1")).to_json()
    assert premier == second
