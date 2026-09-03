"""Traduction du vocabulaire de l'API vers celui d'Ansible.

Deux traductions vivent ici, et une seule fois : le **nom** d'un module et le
**type** d'une option. Les templates ne doivent contenir ni l'une ni l'autre.
"""

from __future__ import annotations

import re

from generator.ir.enums import ApiType, OperationKind
from generator.ir.models import ApiParameter

#: Suffixe de module par classification. `MANAGE` n'en porte aucun : le module
#: qui gère l'état durable d'une ressource porte le nom de la ressource.
_MODULE_SUFFIX: dict[OperationKind, str | None] = {
    OperationKind.INFO: "_info",
    OperationKind.ACTION: "_action",
    OperationKind.MANAGE: "",
    OperationKind.WORKFLOW: "",
}

#: Correspondance des types de l'IR vers les types `argument_spec`.
_ANSIBLE_TYPES: dict[ApiType, str] = {
    ApiType.STRING: "str",
    ApiType.INTEGER: "int",
    ApiType.NUMBER: "float",
    ApiType.BOOLEAN: "bool",
    ApiType.ENUM: "str",
    ApiType.ARRAY: "list",
    ApiType.MAP: "dict",
    ApiType.OBJECT: "dict",
}

#: Fragments de nom qui rendent un paramètre sensible. La liste est
#: volontairement large : un faux positif se corrige par un override, un faux
#: négatif écrit un secret dans le journal d'Ansible.
#: L'heuristique d'`ansible-test validate-modules`, recopiée pour pouvoir lui
#: répondre plutôt que la subir. Elle vit dans `validate_modules/main.py` sous
#: le nom `PASSWORD_MATCH`.
_ANSIBLE_PASSWORD_MATCH = re.compile(
    r"^(?:.+[-_\s])?(?:api[-_\s]?)?"
    r"(?:key|pass(?:[-_\s]?(?:word|phrase|wrd|wd)?)|secret|token)"
    r"(?:[-_\s].+)?$",
    re.IGNORECASE,
)

_SENSITIVE_FRAGMENTS: tuple[str, ...] = (
    "secret",
    "token",
    "password",
    "passphrase",
    "private_key",
    "credential",
    "api_key",
)

#: Paramètres portés par le module_utils commun : ils ne se redéclarent jamais
#: dans un module généré.
COMMON_PARAMETERS: frozenset[str] = frozenset(
    {
        "profile",
        "config_file",
        "access_key",
        "secret_key",
        "api_url",
        "api_allow_insecure",
        "api_timeout",
        "user_agent",
        "organization_id",
        "project_id",
        "wait",
        "wait_timeout",
    }
)


class UnmappedType(Exception):
    """Un type de l'IR n'a pas d'équivalent `argument_spec`."""

    def __init__(self, parameter: str, type: ApiType) -> None:
        super().__init__(f"{parameter} : type {type.value} sans correspondance Ansible")
        self.parameter = parameter
        self.type = type


def module_name(product: str, resource: str, kind: OperationKind) -> str | None:
    """Nom du module Ansible, ou `None` quand la classe n'en produit pas.

    Le nom suit `<produit>_<ressource>[_info|_action]` et ne contient jamais un
    verbe HTTP : `instance_server_info`, jamais `instance_get_server`.
    """
    suffix = _MODULE_SUFFIX.get(kind)
    if suffix is None:
        return None
    return f"{product}_{resource}{suffix}"


def is_sensitive(parameter: ApiParameter) -> bool:
    """Vrai quand le paramètre doit recevoir `no_log=True`."""
    name = parameter.name.lower()
    return any(fragment in name for fragment in _SENSITIVE_FRAGMENTS)


def ansible_soupconne(name: str) -> bool:
    """Vrai quand `validate-modules` va soupçonner ce nom d'être un secret.

    Sa règle est plus large que la nôtre : elle attrape `key` tout court, là où
    `_SENSITIVE_FRAGMENTS` s'en garde parce que `ssh_key_id` et `key_name` n'en
    sont pas. Mesuré : `instance_server_user_data_info` porte un paramètre `key`
    qui est le **nom** d'une entrée de user-data, et `ansible-test sanity`
    refusait le module.

    Ne rien dire n'est pas une réponse. `no_log=False` est la façon documentée
    de dire « regardé, ce n'en est pas un », et elle vaut mieux qu'un module
    qu'Ansible refuse ou qu'une exception dans une liste d'ignorés.
    """
    return bool(_ANSIBLE_PASSWORD_MATCH.match(name))


def no_log_de(parameter: ApiParameter) -> bool | None:
    """Ce que l'`argument_spec` doit déclarer : `True`, `False`, ou rien.

    Trois issues et non deux, parce que « pas de secret » et « personne n'a
    regardé » ne se disent pas pareil à `validate-modules`.
    """
    if is_sensitive(parameter):
        return True
    if ansible_soupconne(parameter.name.lower()):
        return False
    return None


def argument_spec_entry(parameter: ApiParameter) -> dict[str, object]:
    """Traduit un paramètre de l'IR en entrée d'`argument_spec`.

    Lève `UnmappedType` plutôt que de deviner : un type inconnu doit remonter
    dans le rapport, pas devenir un `str` par défaut.
    """
    ansible_type = _ANSIBLE_TYPES.get(parameter.type)
    if ansible_type is None:
        raise UnmappedType(parameter=parameter.name, type=parameter.type)

    entry: dict[str, object] = {"type": ansible_type}
    if parameter.required:
        entry["required"] = True
    if parameter.type is ApiType.ENUM and parameter.enum_values:
        entry["choices"] = list(parameter.enum_values)
    if parameter.type is ApiType.ARRAY:
        # Le contrat publié ne déclare pas toujours le type des éléments ;
        # `str` est le repli, et le rapport signale le paramètre concerné.
        element = _ANSIBLE_TYPES.get(parameter.item_type or ApiType.STRING, "str")
        entry["elements"] = element
    # Un `default` porté par un enum du contrat n'est pas un défaut de l'API :
    # c'est la valeur zéro du protobuf dont le document OpenAPI est la
    # projection. Mesuré sur instance.v1 : 18 enums sur 18 déclarent leur
    # *première* valeur en `default`, et aucun paramètre non-enum n'en porte
    # aucun. Le recopier ferait envoyer `state=running` à chaque appel de
    # `instance_server_info`, et les serveurs arrêtés disparaîtraient d'une
    # liste qui se présente comme complète.
    if parameter.default is not None and parameter.type is not ApiType.ENUM:
        entry["default"] = parameter.default
    no_log = no_log_de(parameter)
    if no_log is not None:
        entry["no_log"] = no_log
    return entry
