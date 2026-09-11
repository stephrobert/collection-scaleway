"""Un nom se résout en identifiant, ou le refus dit pourquoi.

Les cas mécaniques se jouent sur un contrat de laboratoire construit ici : ils
ne doivent pas rougir le jour où Scaleway ajoute un champ. Les garanties sur les
contrats réels vivent dans `test_instance_contract.py` et dans le test de
propriété de fin de fichier, qui lui regarde les deux produits livrés.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.resolution import (
    build_resolutions,
    merge_resolutions,
)
from generator.ir.enums import ApiType, HTTPMethod, ParameterLocation, Scope
from generator.ir.models import (
    ApiField,
    ApiObject,
    ApiOperation,
    ApiParameter,
    ApiResponse,
    ApiService,
)
from generator.parser.openapi import parse_document
from generator.source.base import VendoredSpecSource


def _zone() -> ApiParameter:
    return ApiParameter(
        name="zone", type=ApiType.STRING, required=True, location=ParameterLocation.PATH
    )


def _chemin(nom: str) -> ApiParameter:
    return ApiParameter(
        name=nom, type=ApiType.STRING, required=True, location=ParameterLocation.PATH
    )


def _filtre(nom: str) -> ApiParameter:
    return ApiParameter(
        name=nom, type=ApiType.STRING, required=False, location=ParameterLocation.QUERY
    )


def _liste(
    identifiant: str,
    *,
    ressource: str,
    schema: str,
    champ: str,
    parametres: tuple[ApiParameter, ...] = (),
) -> ApiOperation:
    return ApiOperation(
        id=identifiant,
        service="labo",
        version="v1",
        resource=ressource,
        http_method=HTTPMethod.GET,
        path=f"/labo/v1/zones/{{zone}}/{champ}",
        scope=Scope.ZONE,
        parameters=(_zone(), *parametres),
        response=ApiResponse(payload_field=champ, payload_schema=schema, is_list=True),
    )


def _service(
    operations: tuple[ApiOperation, ...],
    objets: tuple[ApiObject, ...],
    *,
    nom: str = "labo",
) -> ApiService:
    return ApiService(name=nom, version="v1", operations=operations, objects=objets)


def _objet(nom: str, champs: tuple[str, ...]) -> ApiObject:
    return ApiObject(
        name=nom,
        fields=tuple(ApiField(name=c, type=ApiType.STRING) for c in champs),
    )


# --- ce qui se résout ------------------------------------------------------


def test_un_objet_portant_id_et_name_se_resout() -> None:
    service = _service(
        (_liste("ListWidgets", ressource="widget", schema="labo.v1.Widget", champ="widgets"),),
        (_objet("labo.v1.Widget", ("id", "name", "state")),),
    )

    resolutions, refus = build_resolutions(service, {"widget_id"})

    assert refus == ()
    assert len(resolutions) == 1
    assert resolutions[0].parameter == "widget_id"
    assert resolutions[0].list_operation == "ListWidgets"
    assert resolutions[0].payload_field == "widgets"


def test_la_portee_retient_les_parametres_de_chemin_sauf_la_zone() -> None:
    """`zone` et `region` sont la portée d'appel, pas celle d'une ressource."""
    service = _service(
        (
            _liste(
                "ListGadgets",
                ressource="gadget",
                schema="labo.v1.Gadget",
                champ="gadgets",
                parametres=(_chemin("widget_id"),),
            ),
        ),
        (_objet("labo.v1.Gadget", ("id", "name")),),
    )

    resolutions, _ = build_resolutions(service, {"gadget_id"})

    assert resolutions[0].scope == ("widget_id",)


def test_la_jointure_ignore_la_casse_du_contrat() -> None:
    """Mesuré sur le contrat réel : `PrivateNIC` et `Ip` cohabitent.

    Une jointure sensible à la casse ne rate pas seulement le rattachement,
    elle publie « aucun schéma nommé PrivateNic » là où le contrat en porte un.
    """
    service = _service(
        (_liste("ListNICs", ressource="nic", schema="labo.v1.PrivateNIC", champ="nics"),),
        (_objet("labo.v1.PrivateNIC", ("id", "name")),),
    )

    resolutions, refus = build_resolutions(service, {"private_nic_id"})

    assert refus == ()
    assert resolutions[0].schema == "labo.v1.PrivateNIC"


def test_la_jointure_passe_par_le_schema_pas_par_la_ressource_derivee() -> None:
    """Mesuré sur `lb` : un objet, deux familles de chemins, deux ressources.

    `/frontends/{frontend_id}/acls` porte la liste et `/acls/{acl_id}` la
    lecture ; la dérivation en fait `frontend_acl` et `acl`. Joindre sur la
    ressource déclarerait `acl_id` non résoluble.
    """
    service = _service(
        (
            _liste(
                "ListAcls",
                ressource="frontend_acl",  # la ressource dérivée n'est pas `acl`
                schema="labo.v1.Acl",
                champ="acls",
                parametres=(_chemin("frontend_id"),),
            ),
        ),
        (_objet("labo.v1.Acl", ("id", "name")),),
    )

    resolutions, refus = build_resolutions(service, {"acl_id"})

    assert refus == ()
    assert resolutions[0].list_operation == "ListAcls"
    assert resolutions[0].scope == ("frontend_id",)


def test_le_filtre_de_l_api_est_releve_quand_il_existe() -> None:
    service = _service(
        (
            _liste(
                "ListWidgets",
                ressource="widget",
                schema="labo.v1.Widget",
                champ="widgets",
                parametres=(_filtre("name"),),
            ),
        ),
        (_objet("labo.v1.Widget", ("id", "name")),),
    )

    resolutions, _ = build_resolutions(service, {"widget_id"})

    assert resolutions[0].filters_by_name is True


def test_un_contrat_sans_filtre_de_nom_se_resout_quand_meme() -> None:
    """Le filtre de l'API n'est qu'un raccourci : la comparaison est locale."""
    service = _service(
        (_liste("ListWidgets", ressource="widget", schema="labo.v1.Widget", champ="widgets"),),
        (_objet("labo.v1.Widget", ("id", "name")),),
    )

    resolutions, refus = build_resolutions(service, {"widget_id"})

    assert refus == ()
    assert resolutions[0].filters_by_name is False


# --- ce qui se refuse, et la raison qui est publiée ------------------------


def test_un_objet_sans_champ_name_est_refuse_avec_sa_raison() -> None:
    """`Ip`, `Route`, `PrivateNIC` et `SecurityGroupRule` sont dans ce cas."""
    service = _service(
        (_liste("ListIps", ressource="ip", schema="labo.v1.Ip", champ="ips"),),
        (_objet("labo.v1.Ip", ("id", "address")),),
    )

    resolutions, refus = build_resolutions(service, {"ip_id"})

    assert resolutions == ()
    assert len(refus) == 1
    assert refus[0].parameter == "ip_id"
    assert "ne porte pas de champ name" in refus[0].reason
    assert "Ip" in refus[0].reason


def test_un_identifiant_sans_liste_est_refuse_avec_sa_raison() -> None:
    service = _service((), ())

    _, refus = build_resolutions(service, {"widget_id"})

    assert len(refus) == 1, "le refus a disparu"
    assert "aucun schéma nommé Widget" in refus[0].reason


def test_deux_listes_du_meme_objet_nommable_sont_une_portee_ambigue() -> None:
    objets = (_objet("labo.v1.Rule", ("id", "name")),)
    service = _service(
        (
            _liste("ListRules", ressource="rule", schema="labo.v1.Rule", champ="rules"),
            _liste("ListDefaultRules", ressource="rule", schema="labo.v1.Rule", champ="rules"),
        ),
        objets,
    )

    _, refus = build_resolutions(service, {"rule_id"})

    assert len(refus) == 1, "l'ambiguïté a été tranchée en silence"
    assert "portée est ambiguë" in refus[0].reason
    # Le refus nomme les deux camps : sans ça, il n'y a rien à trancher.
    assert "ListRules" in refus[0].reason
    assert "ListDefaultRules" in refus[0].reason


def test_l_absence_de_name_prime_sur_l_ambiguite() -> None:
    """Deux raisons vraies ; on publie celle qui resterait bloquante.

    Une portée ambiguë se tranche par un override, un objet sans `name` ne se
    tranche pas. Mesuré : `security_group_rule_id` cumule les deux.
    """
    service = _service(
        (
            _liste("ListRules", ressource="rule", schema="labo.v1.Rule", champ="rules"),
            _liste("ListDefaultRules", ressource="rule", schema="labo.v1.Rule", champ="rules"),
        ),
        (_objet("labo.v1.Rule", ("id", "protocol")),),
    )

    _, refus = build_resolutions(service, {"rule_id"})

    assert len(refus) == 1, "le refus a disparu"
    assert "ne porte pas de champ name" in refus[0].reason
    assert "ambigu" not in refus[0].reason


def test_le_compte_et_le_projet_ne_sont_pas_des_ressources_a_chercher() -> None:
    service = _service((), ())

    resolutions, refus = build_resolutions(service, {"project_id", "organization_id"})

    assert resolutions == ()
    assert refus == ()


def test_un_parametre_qui_n_est_pas_un_identifiant_est_ignore() -> None:
    service = _service((), ())

    resolutions, refus = build_resolutions(service, {"zone", "name", "per_page"})

    assert resolutions == ()
    assert refus == ()


# --- la fusion entre produits ---------------------------------------------


def test_un_identifiant_revendique_par_deux_produits_est_refuse() -> None:
    """`ip_id` existe dans `instance` et dans `lb`, et ce n'est pas la même ip.

    Choisir en silence donnerait l'identifiant du mauvais produit, ce qui est
    pire que de ne rien donner.
    """

    def table(nom: str):  # type: ignore[no-untyped-def]
        service = _service(
            (_liste("ListIps", ressource="ip", schema=f"{nom}.v1.Ip", champ="ips"),),
            (_objet(f"{nom}.v1.Ip", ("id", "name")),),
            nom=nom,
        )
        return build_resolutions(service, {"ip_id"})[0]

    gardees, refus = merge_resolutions([table("instance"), table("lb")])

    assert gardees == ()
    assert len(refus) == 1
    assert "instance" in refus[0].reason and "lb" in refus[0].reason


def test_un_identifiant_porte_par_un_seul_produit_traverse_la_fusion() -> None:
    service = _service(
        (_liste("ListWidgets", ressource="widget", schema="labo.v1.Widget", champ="widgets"),),
        (_objet("labo.v1.Widget", ("id", "name")),),
    )
    table = build_resolutions(service, {"widget_id"})[0]

    gardees, refus = merge_resolutions([table, ()])

    assert refus == ()
    assert len(gardees) == 1


# --- la garantie sur les contrats livrés ----------------------------------


@pytest.fixture(scope="module")
def tables_livrees() -> tuple[tuple, tuple]:
    """Ce que les deux contrats versionnés permettent réellement de résoudre."""
    source = VendoredSpecSource(root=Path("specs/scaleway"))
    par_produit = []
    refus = []
    for produit in ("instance", "lb"):
        service = parse_document(source.load(produit, "v1"))
        parametres = {
            parametre.name
            for operation in service.operations
            for parametre in operation.parameters
            if parametre.location.value == "path" and parametre.name.endswith("_id")
        }
        resolutions, refuses = build_resolutions(service, parametres)
        par_produit.append(resolutions)
        refus.extend(refuses)
    gardees, conflits = merge_resolutions(par_produit)
    return gardees, tuple(refus) + conflits


def test_les_contrats_livres_resolvent_les_identifiants_attendus(tables_livrees) -> None:  # type: ignore[no-untyped-def]
    """La liste est nommée, pas comptée : un compte ne dit pas *lesquels*."""
    gardees, _ = tables_livrees

    assert {r.parameter for r in gardees} == {
        "acl_id",
        "backend_id",
        "certificate_id",
        "frontend_id",
        "image_id",
        "lb_id",
        "placement_group_id",
        "security_group_id",
        "server_id",
        "snapshot_id",
        "subscriber_id",
        "volume_id",
    }


def test_les_refus_des_contrats_livres_ont_tous_une_raison_de_contrat(tables_livrees) -> None:  # type: ignore[no-untyped-def]
    """Quatre objets ne portent pas de `name`, et rien ne comblera ça."""
    _, refus = tables_livrees

    assert {r.parameter for r in refus} == {
        "ip_id",
        "private_nic_id",
        "route_id",
        "security_group_rule_id",
    }
    for refuse in refus:
        assert "ne porte pas de champ name" in refuse.reason


def test_aucune_resolution_ne_porte_une_portee_contenant_la_zone(tables_livrees) -> None:
    gardees, _ = tables_livrees

    for resolution in gardees:
        assert "zone" not in resolution.scope
        assert "region" not in resolution.scope
