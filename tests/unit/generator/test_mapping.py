"""Nommage des modules, types d'`argument_spec` et champs sensibles."""

from __future__ import annotations

import pytest

from generator.ansible.mapping import (
    COMMON_PARAMETERS,
    UnmappedType,
    argument_spec_entry,
    is_sensitive,
    module_name,
)
from generator.ir.enums import ApiType, OperationKind, ParameterLocation
from generator.ir.models import ApiParameter
from generator.parser.naming import singularize, singularize_phrase, snake_case, split_words


def _parameter(name: str, type: ApiType = ApiType.STRING, **kwargs) -> ApiParameter:
    return ApiParameter(
        name=name,
        type=type,
        required=kwargs.pop("required", False),
        location=kwargs.pop("location", ParameterLocation.BODY),
        **kwargs,
    )


# --- nommage ---------------------------------------------------------------


def test_le_decoupage_respecte_les_sigles() -> None:
    assert split_words("ListPrivateNICs") == ["list", "private", "nics"]
    assert split_words("GetServerUserData") == ["get", "server", "user", "data"]
    assert snake_case("ServerAction") == "server_action"


def test_la_singularisation_couvre_les_formes_de_scaleway() -> None:
    assert singularize("servers") == "server"
    assert singularize("policies") == "policy"
    assert singularize("addresses") == "address"
    assert singularize("data") == "data"
    assert singularize("status") == "status"
    assert singularize_phrase("servers_types") == "server_type"


def test_un_sigle_qui_finit_par_s_nest_pas_un_pluriel() -> None:
    """`dns-zones` donnait `dn_zone`, et `k8s` donnait `k8`.

    Le nom de ressource décide du nom de module **et** de la clé d'override :
    un `dn_zone` produirait un module `domain_dn_zone_info`, et l'override
    correspondant serait écrit sur un nom faux. Ce sont les chemins réels des
    produits `domain` et `kubernetes`, dont les contrats ne sont pas encore
    versionnés ici : le défaut serait sorti au premier `new-product`.
    """
    assert singularize("dns") == "dns"
    assert singularize("k8s") == "k8s"
    assert singularize_phrase("dns_zones") == "dns_zone"


def test_le_pluriel_dun_sigle_perd_bien_son_s() -> None:
    """Le cas voisin qui ne doit pas bouger, et que la règle doit distinguer.

    `IPs`, `NICs`, `IDs` et `ACLs` sont déclarés avec un `s` minuscule parce que
    ce sont des pluriels. `DNS` et `K8S` sont déclarés tout en capitales parce
    qu'ils n'en sont pas. La casse de la déclaration porte la différence.
    """
    assert singularize("ips") == "ip"
    assert singularize("nics") == "nic"
    assert singularize("ids") == "id"
    assert singularize("acls") == "acl"
    assert singularize("vpcs") == "vpc"


@pytest.mark.parametrize(
    ("kind", "attendu"),
    [
        (OperationKind.INFO, "instance_server_info"),
        (OperationKind.ACTION, "instance_server_action"),
        (OperationKind.MANAGE, "instance_server"),
        (OperationKind.LIFECYCLE, None),
        (OperationKind.IGNORE, None),
    ],
)
def test_le_nom_du_module_depend_de_la_classe(kind: OperationKind, attendu: str | None) -> None:
    assert module_name("instance", "server", kind) == attendu


def test_aucun_verbe_http_dans_un_nom_de_module() -> None:
    """`instance_get_server` est exactement ce que le projet refuse de produire."""
    for kind in (OperationKind.INFO, OperationKind.ACTION, OperationKind.MANAGE):
        nom = module_name("instance", "server", kind)
        assert nom is not None
        assert not any(
            verbe in nom.split("_") for verbe in ("get", "list", "post", "patch", "delete", "put")
        )


# --- types -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("type_ir", "type_ansible"),
    [
        (ApiType.STRING, "str"),
        (ApiType.INTEGER, "int"),
        (ApiType.NUMBER, "float"),
        (ApiType.BOOLEAN, "bool"),
        (ApiType.ENUM, "str"),
        (ApiType.ARRAY, "list"),
        (ApiType.MAP, "dict"),
        (ApiType.OBJECT, "dict"),
    ],
)
def test_chaque_type_de_lir_a_un_type_ansible(type_ir: ApiType, type_ansible: str) -> None:
    assert argument_spec_entry(_parameter("champ", type_ir))["type"] == type_ansible


def test_un_enum_devient_des_choices() -> None:
    entree = argument_spec_entry(
        _parameter("action", ApiType.ENUM, enum_values=("poweron", "poweroff"))
    )
    assert entree["choices"] == ["poweron", "poweroff"]


def test_une_liste_declare_le_type_de_ses_elements() -> None:
    entree = argument_spec_entry(_parameter("tags", ApiType.ARRAY, item_type=ApiType.STRING))
    assert entree["elements"] == "str"


def test_une_liste_sans_type_delement_retombe_sur_str() -> None:
    """Le contrat publié ne déclare pas `items` ; le repli est explicite."""
    entree = argument_spec_entry(_parameter("tags", ApiType.ARRAY, item_type=None))
    assert entree["elements"] == "str"


def test_un_type_inconnu_leve_plutot_que_de_deviner() -> None:
    with pytest.raises(UnmappedType):
        argument_spec_entry(_parameter("mystere", ApiType.UNKNOWN))


def test_un_parametre_requis_le_reste() -> None:
    assert argument_spec_entry(_parameter("server_id", required=True))["required"] is True


def test_un_default_denum_du_contrat_nest_pas_un_default_ansible() -> None:
    """Mesuré : 18 enums sur 18 déclarent leur première valeur en `default`.

    C'est la valeur zéro du protobuf dont le document OpenAPI est la
    projection, pas un choix de l'API. La recopier ferait envoyer
    `state=running` à chaque liste, et les serveurs arrêtés disparaîtraient.
    """
    entree = argument_spec_entry(
        _parameter("state", ApiType.ENUM, enum_values=("running", "stopped"), default="running")
    )
    assert "default" not in entree
    assert entree["choices"] == ["running", "stopped"]


def test_un_default_hors_enum_est_conserve() -> None:
    """La règle vise les enums, pas la notion de valeur par défaut."""
    entree = argument_spec_entry(_parameter("per_page", ApiType.INTEGER, default=50))
    assert entree["default"] == 50


# --- champs sensibles ------------------------------------------------------


@pytest.mark.parametrize(
    "nom",
    ["secret_key", "api_token", "password", "ssh_private_key", "passphrase", "credential_id"],
)
def test_un_champ_sensible_recoit_no_log(nom: str) -> None:
    assert is_sensitive(_parameter(nom)) is True
    assert argument_spec_entry(_parameter(nom))["no_log"] is True


@pytest.mark.parametrize("nom", ["name", "zone", "server_id", "tags", "commercial_type"])
def test_un_champ_ordinaire_ne_recoit_pas_no_log(nom: str) -> None:
    assert is_sensitive(_parameter(nom)) is False
    assert "no_log" not in argument_spec_entry(_parameter(nom))


def test_les_parametres_communs_sont_declares_une_seule_fois() -> None:
    """Ils viennent du module_utils, un module généré ne les redéclare pas."""
    assert {"access_key", "secret_key", "api_url", "wait", "wait_timeout"} <= COMMON_PARAMETERS
