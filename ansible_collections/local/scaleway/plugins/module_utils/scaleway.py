# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Runtime commun des modules générés.

Ce fichier n'est pas généré : c'est le socle sur lequel les modules générés
s'appuient. Tout ce qui demande une décision d'exécution vit ici, et nulle part
ailleurs. Un module généré porte sa documentation, son `argument_spec` et
l'opération qu'il exécute ; il ne porte ni client, ni gestion d'erreur, ni
pagination.

Trois choix structurent ce fichier, et chacun corrige un défaut mesuré sur la
collection officielle `scaleway/ansible` :

* **une seule construction de client**, qui lit les paramètres du module puis
  l'environnement. La collection officielle en a deux qui divergent, et la
  seconde ignore silencieusement `access_key` ;
* **l'exécution se fait sur la méthode et le chemin du contrat**, via
  `scaleway_core.api.API._request`. Le SDK reste le client d'exécution, mais il
  n'est jamais la source de la génération : le générateur ne devine aucun nom de
  méthode SDK à partir d'un `operationId` ;
* **la pagination va jusqu'au bout**, et elle s'arrête sur une condition
  observable, pas sur une supposition.

`SCW_API_URL` est honoré de bout en bout : c'est ce qui permet de faire tourner
un playbook contre un émulateur local, sans credentials Scaleway.
"""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import quote

from ansible.module_utils.basic import AnsibleModule, env_fallback, missing_required_lib

try:
    from scaleway_core.api import API
    from scaleway_core.client import Client
    from scaleway_core.profile import Profile
except ImportError:
    SDK_IMPORT_ERROR = traceback.format_exc()
    HAS_SDK = False
else:
    SDK_IMPORT_ERROR = None
    HAS_SDK = True

#: URL de l'API de production. Toute autre valeur désigne un autre backend,
#: typiquement un émulateur local, et le runtime le traite différemment (voir
#: `_validate_client`).
PRODUCTION_API_URL = "https://api.scaleway.com"

#: Identifie la collection auprès de l'API, comme le SDK le fait pour lui-même.
DEFAULT_USER_AGENT = "ansible-local.scaleway"

#: Taille de page demandée aux opérations de liste. 100 est le maximum accepté
#: par l'API Instance, mesuré dans la description de `per_page` du contrat.
DEFAULT_PAGE_SIZE = 100

#: Garde-fou de la boucle de pagination. Une API qui ignorerait `per_page`
#: rendrait indéfiniment la même page ; mieux vaut échouer bruyamment que
#: boucler en silence.
MAX_PAGES = 1000

#: Correspondance des paramètres du module vers les champs du profil SDK.
#: Elle est explicite : un paramètre commun ajouté ici sans être ajouté à
#: `scaleway_argument_spec()` ne serait jamais lu.
_PARAMETER_TO_PROFILE: dict[str, str] = {
    "access_key": "access_key",
    "secret_key": "secret_key",
    "api_url": "api_url",
    "api_allow_insecure": "api_allow_insecure",
    "user_agent": "user_agent",
    "organization_id": "default_organization_id",
    "project_id": "default_project_id",
}


def scaleway_argument_spec() -> dict[str, dict[str, Any]]:
    """Paramètres communs à tous les modules de la collection.

    Les noms, les variables d'environnement et les valeurs par défaut sont ceux
    de `scaleway_argument_spec()` de la collection officielle : un utilisateur
    qui passe d'une collection à l'autre ne doit pas réapprendre.
    """
    return {
        "profile": {"type": "str", "fallback": (env_fallback, ["SCW_PROFILE"])},
        "config_file": {"type": "path", "fallback": (env_fallback, ["SCW_CONFIG_PATH"])},
        "access_key": {
            "type": "str",
            "no_log": True,
            "fallback": (env_fallback, ["SCW_ACCESS_KEY"]),
        },
        "secret_key": {
            "type": "str",
            "no_log": True,
            "fallback": (env_fallback, ["SCW_SECRET_KEY"]),
        },
        "api_url": {
            "type": "str",
            "default": PRODUCTION_API_URL,
            "fallback": (env_fallback, ["SCW_API_URL"]),
        },
        "api_allow_insecure": {"type": "bool", "default": False},
        "user_agent": {"type": "str"},
        "organization_id": {
            "type": "str",
            "fallback": (env_fallback, ["SCW_DEFAULT_ORGANIZATION_ID"]),
        },
        "project_id": {"type": "str", "fallback": (env_fallback, ["SCW_DEFAULT_PROJECT_ID"])},
    }


def scaleway_waitable_argument_spec() -> dict[str, dict[str, Any]]:
    """Paramètres d'attente, pour les classes qui déclenchent un traitement.

    Valeurs reprises telles quelles de la collection officielle. Un module
    d'information ne les utilise pas : il ne déclenche rien.
    """
    return {
        "wait": {"type": "bool", "default": True},
        "wait_timeout": {"type": "int", "default": 300},
    }


class ScalewayApiError(Exception):
    """Un appel d'API a échoué, décrit par ce qui sert à le diagnostiquer.

    Jamais de clé, de jeton ni de corps de requête dans le message : ce qui est
    porté ici finit dans un journal Ansible, et un journal se partage.
    """

    def __init__(
        self,
        *,
        operation: str,
        message: str,
        status_code: int | None = None,
        request_id: str | None = None,
        api_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.api_type = api_type

    def details(self) -> dict[str, Any]:
        """Ce que le module remonte à côté du message, sans rien inventer."""
        detail: dict[str, Any] = {"operation": self.operation}
        if self.status_code is not None:
            detail["status_code"] = self.status_code
        if self.request_id:
            detail["request_id"] = self.request_id
        if self.api_type:
            detail["api_type"] = self.api_type
        return detail


@dataclass(frozen=True)
class Operation:
    """Une opération du contrat, telle que le générateur l'a lue.

    C'est la seule chose qu'un module généré sait de l'API : une méthode, un
    chemin, et le nom des paramètres selon leur emplacement.
    """

    id: str
    method: str
    path: str
    path_params: tuple[str, ...] = ()
    query_params: tuple[str, ...] = ()
    body_params: tuple[str, ...] = ()
    #: Champ de la réponse qui porte la ressource utile (`server`, `servers`).
    payload_field: str | None = None
    is_list: bool = False
    page_param: str | None = None
    per_page_param: str | None = None


@dataclass(frozen=True)
class InfoModule:
    """Ce qu'un module d'information exécute, et comment il choisit.

    `selector` porte la décision, calculée par le générateur : l'identifiant
    fourni bascule sur le GET unitaire, absent bascule sur la liste paginée. Le
    module généré ne décide rien, il déclare.
    """

    get_operation: Operation | None = None
    list_operation: Operation | None = None
    selector: str | None = None
    #: Documenté pour mémoire : les paramètres communs ne sont jamais envoyés.
    common_parameters: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ActionModule:
    """Ce qu'un module d'action déclenche, et ce qu'il attend ensuite.

    `wait_states` vient d'un override, jamais du contrat : le document dit ce
    qu'une action *fait*, pas dans quel état elle laisse la ressource. Deviner
    cette correspondance serait inventer une promesse que rien ne vérifie.
    """

    operation: Operation
    #: Le paramètre qui porte l'action demandée, `action` chez Scaleway.
    action_parameter: str = "action"
    #: La lecture unitaire de la même ressource, pour attendre l'état visé.
    read_operation: Operation | None = None
    #: Champ de la ressource qui porte son état, déclaré par l'override.
    state_field: str = "state"
    #: Action -> état attendu. Une action absente ne fait pas attendre.
    wait_states: dict[str, str] = field(default_factory=dict)


def poll_until(
    read: Callable[[], Any],
    *,
    expected: str,
    field_name: str,
    timeout: float,
    interval: float = 2.0,
    leave_first: str | None = None,
) -> str:
    """Lit la ressource jusqu'à l'état attendu, ou échoue en le disant.

    Rendre la main avant d'avoir vu l'état ferait passer une attente pour une
    confirmation : le playbook suivant agirait sur une machine qui n'a pas fini
    de basculer.

    `leave_first` traite le cas où **l'état visé est déjà celui de départ**.
    C'est celui de `reboot` : la machine est `running` avant, et `running`
    après. Sans cette garde, la première lecture satisfait l'attente en zéro
    seconde, et la tâche suivante s'exécute pendant que la machine redémarre.
    Une attente qui ne fait rien est pire que pas d'attente : elle promet.

    Le contrat ne dit pas sous quel délai l'état bascule. Cette fonction ne
    suppose donc rien : elle exige d'**observer** une valeur différente, et si
    elle n'en voit aucune dans le temps imparti, elle le dit au lieu de
    conclure que tout va bien.
    """
    limite = time.monotonic() + timeout
    observe = "inconnu"
    quitte = leave_first is None
    while True:
        ressource = read()
        if isinstance(ressource, dict):
            observe = str(ressource.get(field_name, "inconnu"))
        if not quitte and observe != leave_first:
            quitte = True
        if quitte and observe == expected:
            return observe
        if time.monotonic() >= limite:
            if not quitte:
                raise ScalewayApiError(
                    operation=field_name,
                    message=(
                        f"l'état n'a jamais quitté '{leave_first}' en {timeout:.0f} s : "
                        "l'action a été acceptée, et rien ne permet de confirmer "
                        "qu'elle a eu lieu"
                    ),
                )
            raise ScalewayApiError(
                operation=field_name,
                message=(
                    f"état '{observe}' après {timeout:.0f} s, '{expected}' attendu : "
                    "l'action a été acceptée mais la ressource n'a pas suivi"
                ),
            )
        time.sleep(interval)


def render_path(path: str, parameters: dict[str, Any]) -> str:
    """Remplace les `{segments}` d'un chemin par les valeurs du module.

    Les valeurs sont encodées : un identifiant fourni par l'utilisateur ne doit
    pas pouvoir sortir de son segment de chemin.
    """
    rendered = path
    for name, value in parameters.items():
        marker = "{" + name + "}"
        if marker in rendered:
            if value is None:
                raise ScalewayApiError(
                    operation=path,
                    message=f"le paramètre de chemin '{name}' est absent",
                )
            rendered = rendered.replace(marker, quote(str(value), safe=""))
    if "{" in rendered:
        missing = rendered[rendered.index("{") : rendered.index("}") + 1]
        raise ScalewayApiError(
            operation=path,
            message=f"le chemin garde un segment non résolu : {missing}",
        )
    return rendered


def query_value(value: Any) -> Any:
    """Traduit une valeur Python en valeur de query string.

    Seuls les booléens demandent un traitement : `requests` écrirait `True`, et
    l'API attend la forme JSON. Le reste passe tel quel, sans conversion
    silencieuse.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def build_query(operation: Operation, parameters: dict[str, Any]) -> dict[str, Any]:
    """Ne retient que les filtres que l'utilisateur a réellement fournis.

    Un paramètre absent n'est pas envoyé : le module ne doit jamais restreindre
    un résultat que personne n'a demandé de restreindre.
    """
    query: dict[str, Any] = {}
    for name in operation.query_params:
        value = parameters.get(name)
        if value is not None:
            query[name] = query_value(value)
    return query


def build_body(operation: Operation, parameters: dict[str, Any]) -> dict[str, Any]:
    """Corps de requête, limité aux champs fournis."""
    body: dict[str, Any] = {}
    for name in operation.body_params:
        value = parameters.get(name)
        if value is not None:
            body[name] = value
    return body


def paginate(
    fetch_page: Callable[[int], dict[str, Any]],
    *,
    payload_field: str,
    per_page: int = DEFAULT_PAGE_SIZE,
    max_pages: int = MAX_PAGES,
) -> list[Any]:
    """Parcourt toutes les pages d'une opération de liste.

    Trois conditions d'arrêt, dans cet ordre :

    1. la page rendue contient moins d'éléments que demandé, donc c'est la
       dernière ;
    2. `total_count` est présent dans la réponse et le compte est atteint. Le
       contrat publié ne déclare pas ce champ, mais le SDK le reconstitue depuis
       l'en-tête `x-total-count` : on l'utilise s'il est là, on ne l'exige pas ;
    3. `max_pages` est atteint, et c'est une erreur : une API qui ignorerait
       `per_page` ferait boucler cette fonction indéfiniment.

    Rendre la première page en silence serait le pire des trois : l'utilisateur
    verrait une liste plausible et incomplète.
    """
    items: list[Any] = []
    for page in range(1, max_pages + 1):
        payload = fetch_page(page)
        batch = payload.get(payload_field) or []
        items.extend(batch)

        if len(batch) < per_page:
            return items

        total = payload.get("total_count")
        if total is not None and len(items) >= int(total):
            return items

    raise ScalewayApiError(
        operation=payload_field,
        message=(
            f"pagination interrompue après {max_pages} pages : "
            "l'API ne semble pas respecter la taille de page demandée"
        ),
    )


def build_client_from_values(values: dict[str, Any]) -> Client:
    """Construit le client, une seule fois et d'une seule façon.

    L'ordre de priorité est celui qu'un utilisateur attend : ce qui est
    déclaré l'emporte sur l'environnement, qui l'emporte sur le fichier de
    configuration. La collection officielle a deux constructions divergentes,
    dont une qui ignore `access_key` passé en paramètre ; il n'y en a qu'une
    ici, et le plugin d'inventaire s'en sert aussi.
    """
    # Le SDK journalise un avertissement quand le fichier de configuration est
    # absent, ce qui est le cas normal en CI. Un module Ansible n'a pas à
    # écrire ça sur la sortie d'erreur à chaque exécution.
    sdk_logger = logging.getLogger("scaleway")
    sdk_logger.addHandler(logging.NullHandler())
    sdk_logger.propagate = False

    profile = Profile.from_config_file_and_env(
        values.get("config_file"),
        values.get("profile") or "default",
    )

    for parameter, attribute in _PARAMETER_TO_PROFILE.items():
        value = values.get(parameter)
        if value is not None:
            setattr(profile, attribute, value)

    if not profile.user_agent:
        profile.user_agent = DEFAULT_USER_AGENT

    return Client.from_profile(profile)


def build_client(module: AnsibleModule) -> Client:
    """Le client d'un module, construit depuis ses paramètres."""
    return build_client_from_values(dict(module.params))


def _validate_client(module: AnsibleModule, client: Client) -> None:
    """Refuse une configuration inutilisable, avec un message qui la nomme.

    La validation du SDK impose le format `SCWXXXXXXXXXXXXXXXXX` aux clés
    d'accès. Elle est utile contre l'API de production, et elle rendrait
    impossible le seul scénario de test sans credentials du projet : un
    émulateur local, atteint par `SCW_API_URL`. La validation complète ne
    s'applique donc que quand la cible *est* l'API de production.
    """
    if not client.access_key or not client.secret_key:
        module.fail_json(
            msg=(
                "identifiants Scaleway absents : renseigner access_key et secret_key, "
                "ou les variables SCW_ACCESS_KEY et SCW_SECRET_KEY, "
                "ou un profil dans le fichier de configuration."
            )
        )

    if client.api_url.endswith("/"):
        module.fail_json(msg=f"api_url ne doit pas se terminer par '/' : {client.api_url}")

    if client.api_url == PRODUCTION_API_URL:
        try:
            client.validate()
        except ValueError as error:
            module.fail_json(msg=f"configuration Scaleway invalide : {error}")


class ScalewayApi:
    """Le point d'exécution unique des modules de la collection."""

    def __init__(self, module: AnsibleModule) -> None:
        if not HAS_SDK:
            module.fail_json(
                msg=missing_required_lib("scaleway", url="https://pypi.org/project/scaleway/"),
                exception=SDK_IMPORT_ERROR,
            )
        self._module = module
        self._client = build_client(module)
        _validate_client(module, self._client)
        # `bypass_validation` : la validation a déjà été faite ci-dessus, et
        # elle tient compte de la cible. La refaire ici interdirait l'émulateur.
        self._api = API(self._client, bypass_validation=True)

    @property
    def client(self) -> Client:
        return self._client

    def request(
        self,
        operation: Operation,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Exécute une opération et rend la charge utile JSON de la réponse."""
        path = render_path(operation.path, self._module.params)
        response = self._api._request(
            operation.method,
            path,
            params=params or {},
            body=body,
        )

        if response.status_code >= 400:
            raise _error_from_response(operation, response)

        if not response.content:
            return {}
        try:
            payload = response.json()
        except ValueError as error:
            raise ScalewayApiError(
                operation=operation.id,
                message=f"réponse illisible : {error}",
                status_code=response.status_code,
                request_id=response.headers.get("x-request-id"),
            ) from error
        return payload if isinstance(payload, dict) else {"result": payload}

    def fetch_one(self, operation: Operation) -> Any:
        """Lit une ressource unique, et rend le champ que le contrat désigne."""
        payload = self.request(operation, params=build_query(operation, self._module.params))
        if operation.payload_field is None:
            return payload
        return payload.get(operation.payload_field)

    def fetch_all(self, operation: Operation) -> list[Any]:
        """Lit une collection entière, toutes pages parcourues."""
        if operation.payload_field is None:
            raise ScalewayApiError(
                operation=operation.id,
                message="opération de liste sans champ de charge utile déclaré",
            )
        filters = build_query(operation, self._module.params)

        def fetch_page(page: int) -> dict[str, Any]:
            params = dict(filters)
            if operation.page_param:
                params[operation.page_param] = page
            if operation.per_page_param:
                params[operation.per_page_param] = DEFAULT_PAGE_SIZE
            return self.request(operation, params=params)

        if not operation.page_param:
            # Opération de liste non paginée : une seule lecture, et le dire.
            payload = self.request(operation, params=filters)
            return list(payload.get(operation.payload_field) or [])

        return paginate(fetch_page, payload_field=operation.payload_field)


def _error_from_response(operation: Operation, response: Any) -> ScalewayApiError:
    """Construit l'erreur à partir des seuls champs prévus pour ça.

    Le corps d'erreur n'est jamais repris en entier : il peut contenir ce que
    l'appelant a envoyé, et un module ne recopie pas une requête dans un journal.
    """
    message = f"HTTP {response.status_code}"
    api_type = None
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        message = str(payload.get("message") or message)
        api_type = payload.get("type")
    return ScalewayApiError(
        operation=operation.id,
        message=message,
        status_code=response.status_code,
        request_id=response.headers.get("x-request-id"),
        api_type=api_type,
    )


def run_info_module(module: AnsibleModule, spec: InfoModule) -> None:
    """Exécute un module d'information : lecture unitaire ou liste complète.

    La règle est portée par `spec.selector`, calculée par le générateur :
    identifiant fourni, on lit la ressource ; identifiant absent, on liste. Un
    module d'information ne modifie rien, donc `changed` est toujours faux et le
    check mode ne change pas son comportement.
    """
    api = ScalewayApi(module)
    selector = spec.selector
    wants_one = (
        spec.get_operation is not None
        and selector is not None
        and module.params.get(selector) is not None
    )

    try:
        if wants_one and spec.get_operation is not None:
            operation = spec.get_operation
            result: Any = api.fetch_one(operation)
        elif spec.list_operation is not None:
            operation = spec.list_operation
            result = api.fetch_all(operation)
        else:
            module.fail_json(
                msg=f"ce module exige {selector} : aucune opération de liste n'existe"
            )
            return
    except ScalewayApiError as error:
        module.fail_json(msg=error.message, **error.details())
        return

    field_name = operation.payload_field or "result"
    module.exit_json(changed=False, **{field_name: result})


def run_action_module(module: AnsibleModule, spec: ActionModule) -> None:
    """Déclenche une action ponctuelle, et rend compte de ce qu'elle a produit.

    Trois choses qu'un module d'action doit tenir, et que celui-ci tient :

    * **en check mode, ne rien déclencher.** Il annonce le changement attendu
      et sort. Un module qui agit en check mode rend le mode inutile, et
      personne ne s'en aperçoit avant le jour où ça compte ;
    * **`changed` est vrai quand l'API a accepté**, pas quand on a envoyé ;
    * **attendre, si on sait quoi attendre.** L'état visé vient d'un override ;
      sans lui le module rend la main tout de suite, et le dit.
    """
    action = module.params.get(spec.action_parameter)
    attendu = spec.wait_states.get(str(action))

    if module.check_mode:
        module.exit_json(
            changed=True,
            action=action,
            expected_state=attendu,
            msg=f"{action} serait déclenché ; rien n'a été envoyé (check mode)",
        )

    api = ScalewayApi(module)
    attente = bool(attendu and spec.read_operation is not None and module.params.get("wait"))

    # L'état avant l'action, et une seule raison de le lire : savoir si l'état
    # visé est déjà celui de départ. C'est le cas de `reboot`, où une attente
    # naïve se satisfait de la première lecture sans rien avoir observé.
    depart: str | None = None
    if attente and spec.read_operation is not None:
        read_operation = spec.read_operation
        try:
            avant = api.fetch_one(read_operation)
        except ScalewayApiError as error:
            module.fail_json(msg=error.message, **error.details())
            return
        if isinstance(avant, dict):
            depart = str(avant.get(spec.state_field, "")) or None

    try:
        payload = api.request(
            spec.operation,
            params=build_query(spec.operation, module.params),
            body=build_body(spec.operation, module.params),
        )
    except ScalewayApiError as error:
        module.fail_json(msg=error.message, **error.details())
        return

    # À partir d'ici l'API a **accepté** : la ressource a changé, et tout échec
    # ultérieur doit le dire. Un `fail_json` sans `changed` ferait croire à un
    # playbook rejoué qu'il n'a rien fait, alors que la machine a bougé.
    etat: str | None = None
    if attente and spec.read_operation is not None:
        read_operation = spec.read_operation
        try:
            etat = poll_until(
                lambda: api.fetch_one(read_operation),
                expected=str(attendu),
                field_name=spec.state_field,
                timeout=float(module.params.get("wait_timeout") or 300),
                leave_first=depart if depart == attendu else None,
            )
        except ScalewayApiError as error:
            module.fail_json(changed=True, msg=error.message, **error.details())
            return

    resultat: dict[str, Any] = {"changed": True, "action": action}
    if etat is not None:
        resultat[spec.state_field] = etat
    if spec.operation.payload_field and spec.operation.payload_field in payload:
        resultat[spec.operation.payload_field] = payload[spec.operation.payload_field]
    module.exit_json(**resultat)
