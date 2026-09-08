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
* **l'exécution se fait sur la méthode et le chemin du contrat**, par une
  requête que ce fichier compose lui-même. Le SDK fournit le profil et les
  identifiants ; il n'est jamais la source de la génération, et le générateur ne
  devine aucun nom de méthode SDK à partir d'un `operationId`. Le transport a
  d'abord passé par `scaleway_core.api.API._request`, et ADR-014 dit pourquoi il
  n'y passe plus ;
* **la pagination va jusqu'au bout**, et elle s'arrête sur une condition
  observable, pas sur une supposition.

`SCW_API_URL` est honoré de bout en bout : c'est ce qui permet de faire tourner
un playbook contre un émulateur local, sans credentials Scaleway.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from collections.abc import Iterable, Mapping
from typing import Any, Callable
from urllib.parse import quote

from ansible.module_utils.basic import AnsibleModule, env_fallback, missing_required_lib
from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

try:
    import requests
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
DEFAULT_USER_AGENT = "ansible-stephrobert.scaleway"

#: L'ordre de priorité des sources d'identifiants, du plus fort au plus faible.
#:
#: **Il n'existe qu'ici.** Trois documents publiés le décrivent, chacun dans ses
#: mots : le README de la collection, le fragment de documentation et la page
#: d'architecture du runtime. Le README l'a annoncé **à l'envers** jusqu'à la
#: 0.4.0, et rien ne l'a vu, parce qu'une phrase ne se compare à rien. Une
#: personne qui gère plusieurs projets comprenait donc l'inverse de ce que le
#: code fait, sur une décision où l'API ne dira rien : les identifiants de
#: l'autre compte sont valides, juste pas ceux qu'on croyait.
#:
#: Chaque rang porte les formulations acceptables, parce qu'Ansible dit
#: « options » là où le README dit « parameters ». Un test exige que les trois
#: documents nomment les trois rangs **dans cet ordre**, et un autre exige que
#: le runtime les applique dans le même.
PRECEDENCE: tuple[tuple[str, ...], ...] = (
    ("module parameters", "module options"),
    ("environment variables", "the environment"),
    ("configuration file",),
)

#: Taille de page demandée aux opérations de liste. 100 est le maximum accepté
#: par l'API Instance, mesuré dans la description de `per_page` du contrat.
DEFAULT_PAGE_SIZE = 100

#: Garde-fou de la boucle de pagination. Une API qui ignorerait `per_page`
#: rendrait indéfiniment la même page ; mieux vaut échouer bruyamment que
#: boucler en silence.
MAX_PAGES = 1000

#: Secondes accordées à un appel d'API, connexion et lecture. Sans limite, une
#: connexion muette fige un playbook indéfiniment : mesuré, le SDK appelle
#: `requests.request()` sans `timeout`, donc rien ne borne l'attente.
#:
#: 60 s est large pour une liste d'une page entière et court devant les 300 s
#: de `wait_timeout`, qui borne une attente entière et non un appel.
DEFAULT_REQUEST_TIMEOUT = 60

#: La valeur qu'une option effaçable porte quand le playbook l'omet.
#:
#: Ansible ne distingue pas une clé absente d'une clé à `null` : `module.params`
#: porte `None` dans les deux cas, et un `description: null` disparaissait
#: avant toute la mécanique de preuve, en rendant `ok`. Le générateur pose ce
#: marqueur en défaut d'une option `raw` sur chaque champ que le contrat déclare
#: effaçable (ADR-012) : omise, l'option vaut le marqueur ; à `null`, elle vaut
#: `None`, et le runtime refuse. Le générateur en porte une copie, et un test
#: exige que les deux concordent.
UNCHANGED = "__unchanged__"

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
            "fallback": (env_fallback, ["SCW_API_URL"]),
        },
        # Ni `api_url` ni `api_allow_insecure` ne portent de défaut ici, et
        # c'est la correction d'un vrai défaut : une valeur par défaut n'est
        # jamais `None`, donc elle écrasait **toujours** ce que le profil
        # déclarait. Un utilisateur qui pointait son profil vers un émulateur
        # voyait son playbook partir en production. Le défaut est appliqué
        # après la lecture du profil, dans `build_client_from_values`.
        "api_allow_insecure": {"type": "bool"},
        "api_timeout": {"type": "int", "default": DEFAULT_REQUEST_TIMEOUT},
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
    #: Filtres que l'API attend en une seule valeur séparée par des virgules.
    #: Le contrat les déclare `string` en le disant dans leur description, et un
    #: override les expose en liste : c'est ici qu'on referme la boucle.
    csv_params: tuple[str, ...] = ()
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
class ManageModule:
    """Ce qu'un module de gestion lit, compare, et écrit.

    **Il n'écrit que la différence, et c'est toute sa raison d'être.** Un module
    qui enverrait tous ses paramètres à chaque exécution rendrait `changed` à
    chaque fois, et écraserait des champs que personne n'a demandé de changer.

    Ne participent à la comparaison que les paramètres **fournis** par le
    playbook. Un paramètre absent n'est pas géré : c'est la convention d'Ansible
    et c'est ce qui permet à deux playbooks de gérer deux facettes d'une même
    ressource sans se marcher dessus.
    """

    read_operation: Operation
    update_operation: Operation
    #: Champs du corps de l'écriture, dans l'ordre du contrat. Ce sont les seuls
    #: que le module gère : le reste de la ressource ne le concerne pas.
    managed_params: tuple[str, ...] = ()
    #: Comment chaque champ géré se compare à ce que l'API rend.
    #:
    #: Le générateur la calcule : le type décide ce qu'il peut, un override
    #: décide le reste. Un champ absent de la table se compare strictement,
    #: parce que c'est le comportement le plus prudent et parce qu'un module
    #: d'une version antérieure n'en porte pas.
    comparisons: tuple[tuple[str, str], ...] = ()
    #: Champs que la vérification d'après écriture ne regarde pas.
    #:
    #: Ils viennent d'un override, avec sa raison, et le cas prévu est une API
    #: qui applique un champ de façon différée. Vérifier un tel champ
    #: échouerait sur un délai plutôt que sur une erreur, ce qui ferait
    #: échouer un playbook correct. La liste est vide aujourd'hui : rien de tel
    #: n'a été observé, et le mécanisme existe pour le jour où ça arrivera.
    unverified_params: tuple[str, ...] = ()
    #: Ceux de ces champs qui portent un secret. **Ils ne se comparent pas** :
    #: l'API ne les rend jamais, donc les comparer reviendrait à comparer une
    #: valeur à `None` et à conclure « différent » à chaque exécution, ce qui
    #: ressemble à une mesure et n'en est pas une.
    secret_params: tuple[str, ...] = ()
    #: Champs que le contrat déclare effaçables, avec l'entrée d'`argument_spec`
    #: de leur type réel. Le module les expose en `raw` avec `UNCHANGED` pour
    #: défaut, seul mécanisme public qui rende un `null` explicite visible
    #: (ADR-012). Le runtime le refuse, parce qu'il ne sait pas encore effacer
    #: (#114), puis revalide la valeur fournie contre l'entrée réelle : `raw` ne
    #: doit rien coûter au playbook, ni conversion ni contrôle de type.
    nullable_params: tuple[tuple[str, dict[str, Any]], ...] = ()


@dataclass(frozen=True)
class ActionModule:
    """Ce qu'un module d'action déclenche, et ce qu'il attend ensuite.

    `wait_states` vient d'un override, jamais du contrat : le document dit ce
    qu'une action *fait*, pas dans quel état elle laisse la ressource. Deviner
    cette correspondance serait inventer une promesse que rien ne vérifie.
    """

    operation: Operation
    #: Le paramètre qui porte l'action demandée, `action` chez Scaleway.
    #: `None` quand l'action **est** l'opération : `MigrateLb` migre,
    #: `ExportSnapshot` exporte, et leur demander `action: migrate` reviendrait
    #: à faire nommer une seconde fois ce que le chemin dit déjà.
    action_parameter: str | None = "action"
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

    **Un filtre déclaré `csv` est joint ici, et pas plus loin.** L'API attend
    une seule valeur séparée par des virgules ; le module l'expose en liste
    parce que c'est ce que le paramètre est. Sans cette jointure, `requests`
    enverrait des paires répétées, ou pire, `str(liste)`.
    """
    query: dict[str, Any] = {}
    for name in operation.query_params:
        value = parameters.get(name)
        if value is None:
            continue
        if name in operation.csv_params and isinstance(value, (list, tuple)):
            query[name] = ",".join(str(item) for item in value)
            continue
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

    **`total_count` prime sur la longueur de la page, et l'ordre est le sujet.**
    Le contrat publié ne déclare pas ce champ, mais le SDK le reconstitue depuis
    l'en-tête `x-total-count` : on l'utilise s'il est là, on ne l'exige pas.
    Quand il est là, il sait ce qu'une page courte ne dit pas.

    S'arrêter d'abord sur « la page est plus courte que demandée » paraît sûr et
    ne l'est pas : une API qui **plafonne** `per_page` sous ce qu'on demande rend
    une page courte dès la première. Mesuré avec un plafond à 50 pour 100
    demandés et `total_count: 120`, l'ancienne version rendait 50 éléments, ne
    demandait qu'une page, et ne signalait rien. Instance plafonne à 100, donc
    le cas est latent aujourd'hui ; ce runtime est commun à tous les produits
    qui viendront.

    Les conditions d'arrêt, donc :

    1. `total_count` est présent et le compte est atteint ;
    2. `total_count` est absent et la page rendue est plus courte que demandée,
       donc c'est la dernière ;
    3. `total_count` est présent, le compte n'est pas atteint, et l'API rend une
       page vide : elle se contredit, et on le dit plutôt que de rendre une
       liste incomplète ;
    4. `max_pages` est atteint, et c'est une erreur : une API qui ignorerait
       `per_page` ferait boucler cette fonction indéfiniment.

    Rendre la première page en silence serait le pire de tous : l'utilisateur
    verrait une liste plausible et incomplète.
    """
    items: list[Any] = []
    for page in range(1, max_pages + 1):
        payload = fetch_page(page)
        batch = payload.get(payload_field) or []
        items.extend(batch)

        total = payload.get("total_count")
        if total is None:
            if len(batch) < per_page:
                return items
        else:
            annonce = int(total)
            if len(items) >= annonce:
                return items
            if not batch:
                raise ScalewayApiError(
                    operation=payload_field,
                    message=(
                        f"l'API annonce {annonce} éléments et n'en rend que "
                        f"{len(items)} avant de rendre une page vide : la liste "
                        "serait incomplète sans le dire"
                    ),
                )

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

    # Les défauts s'appliquent **après** le profil, et jamais avant. Posés dans
    # l'`argument_spec`, ils n'étaient jamais `None` et écrasaient donc toujours
    # ce que le fichier de configuration déclarait : l'ordre de priorité annoncé
    # par la documentation, paramètre puis environnement puis fichier, ne
    # pouvait pas être tenu pour ces deux-là.
    if not profile.api_url:
        profile.api_url = PRODUCTION_API_URL
    if profile.api_allow_insecure is None:
        profile.api_allow_insecure = False

    return Client.from_profile(profile)


def build_client(module: AnsibleModule) -> Client:
    """Le client d'un module, construit depuis ses paramètres."""
    return build_client_from_values(dict(module.params))


#: Les champs dont le SDK peut citer la valeur dans un message d'erreur.
_CREDENTIAL_FIELDS: tuple[str, ...] = ("secret key", "access key", "organization id", "project id")


def _safe_reason(error: Exception) -> str:
    """Ce que le SDK refuse, sans jamais recopier la valeur qu'il a refusée.

    Mesuré : `Client.validate()` lève
    `ValueError("Invalid secret key format 'SCW...', expected ...")`, valeur
    comprise. Recopier ce message publie la clé.
    """
    texte = str(error).lower()
    for champ in _CREDENTIAL_FIELDS:
        if champ in texte:
            return f"le format de {champ} est refusé par le SDK (valeur non affichée)"
    return "les identifiants ou la configuration sont refusés par le SDK"


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
            # Le message du SDK **contient la clé** : « Invalid secret key
            # format 'SCW...' ». Ansible censure les valeurs `no_log` venues
            # des paramètres du module, pas une valeur lue dans
            # ~/.config/scw/config.yaml : elle atterrissait donc en clair dans
            # le journal du playbook et dans les artefacts de CI.
            #
            # Le message est reconstruit à partir du champ fautif, jamais de sa
            # valeur. `ScalewayApiError` promet « jamais de clé dans le
            # message » : cette promesse est désormais tenue ici aussi.
            module.fail_json(msg=f"configuration Scaleway invalide : {_safe_reason(error)}")


def _avec_total_count(charge: dict[str, Any], entetes: Mapping[str, str]) -> dict[str, Any]:
    """Le corps lu, complété par `x-total-count` quand l'en-tête le porte.

    Le contrat ne déclare pas `total_count` dans ses réponses de liste : c'est
    l'en-tête qui le porte. La pagination s'en sert comme garde-fou, donc ne
    pas le reverser rendrait une liste tronquée sans le dire.

    **Ce n'est plus la réponse HTTP qu'on modifie, c'est le corps qu'on lit.**
    La version précédente réécrivait `requests.Response._content`, un attribut
    privé, dans un runtime réécrit précisément pour ne plus dépendre d'une API
    privée du SDK (#132). Le besoin n'a jamais été de changer la réponse : il
    était de donner à son lecteur ce que l'en-tête sait.

    Un total déjà présent dans le corps prime : c'est l'API qui parle d'
    elle-même, et l'en-tête n'est qu'un report.
    """
    total = entetes.get("x-total-count")
    if not total or "total_count" in charge:
        return charge
    return {**charge, "total_count": total}


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
        response = self._send(operation, path, params or {}, body)

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
        if isinstance(payload, dict):
            return _avec_total_count(payload, response.headers)
        # Une charge qui n'est pas un mapping n'a pas de place où loger un
        # total, et le contrat n'en décrit aucune : la nommer `result` est déjà
        # une convention, y greffer un compte en serait une seconde.
        return {"result": payload}

    def _send(
        self,
        operation: Operation,
        path: str,
        params: dict[str, Any],
        body: dict[str, Any] | None,
    ) -> Any:
        """Envoie la requête, et borne l'attente.

        Cette méthode a longtemps été `API._request` du SDK. Deux raisons de ne
        plus l'être, et la première est celle qui compte :

        * **le SDK n'y passe aucun `timeout`.** Mesuré dans son source : une
          connexion muette fige le module indéfiniment, ce qu'aucun playbook ne
          devrait risquer ;
        * `_request` commence par un souligné. Ce n'est pas un contrat public,
          et le runtime n'en utilisait que la méthode et le chemin.

        Ce qui est reproduit ici l'est **délibérément**, pas par recopie :

        * une valeur de liste devient des paires répétées, `?tags=a&tags=b`,
          comme le SDK. Ce que l'API réelle attend n'est pas tranché ;
        * `x-total-count` est reversé sous `total_count` dans ce que `request`
          rend. Sans ce report, la pagination perdrait son garde-fou, parce que
          le contrat ne déclare pas `total_count` dans les réponses de liste.
          C'était le comportement le plus discret du SDK, et il est ici
          explicite. Le report se fait sur le corps **lu**, jamais sur la
          réponse HTTP : `_avec_total_count` dit pourquoi.
        """
        client = self._client
        methode = operation.method.upper()

        entetes: dict[str, str] = {
            "accept": "application/json",
            "user-agent": client.user_agent or DEFAULT_USER_AGENT,
        }
        if methode in ("POST", "PUT", "PATCH"):
            entetes["Content-Type"] = "application/json; charset=utf-8"
        if client.secret_key is not None:
            entetes["x-auth-token"] = client.secret_key

        paires: list[tuple[str, Any]] = []
        for nom, valeur in params.items():
            if valeur is None:
                continue
            if isinstance(valeur, list):
                paires.extend((nom, item) for item in valeur)
            else:
                paires.append((nom, valeur))

        delai = int(self._module.params.get("api_timeout") or DEFAULT_REQUEST_TIMEOUT)
        try:
            response = requests.request(
                method=methode,
                url=f"{client.api_url}{path}",
                params=paires,
                headers=entetes,
                data=json.dumps(body) if body is not None else None,
                verify=not client.api_allow_insecure,
                timeout=delai,
            )
        except requests.exceptions.Timeout as erreur:
            raise ScalewayApiError(
                operation=operation.id,
                message=f"l'API n'a pas répondu en {delai} s : {erreur}",
            ) from erreur
        except requests.exceptions.RequestException as erreur:
            # Sans cette traduction, une panne réseau sort en trace Python et
            # Ansible affiche MODULE FAILURE : l'utilisateur ne sait pas si son
            # playbook est fautif ou si le réseau l'est.
            raise ScalewayApiError(
                operation=operation.id,
                message=f"l'API est injoignable : {erreur}",
            ) from erreur

        return response

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

    **Un module sans sélecteur ni opération de liste n'a qu'une façon de
    tourner, et il faut la prendre.** Les modules générés dans ce cas sont
    `instance_dashboard_info`, `instance_server_type_info`,
    `instance_server_type_availability_info`, `instance_volume_type_info` et
    `instance_server_compatible_type_info` : les nommer vaut mieux que les
    compter, le compte changeant au premier produit ajouté. Leur opération
    unique rend un objet
    ou une carte, pas un tableau, donc le générateur en fait une lecture
    unitaire ; mais il n'existe aucun identifiant à fournir, le chemin étant
    entièrement déterminé par ses paramètres de chemin. Exiger un sélecteur
    absent les rendait **inappelables** : ils sortaient sur « ce module exige
    None ».

    `ansible-test sanity` les acceptait, et ne pouvait pas faire autrement :
    ces fichiers s'importent, se documentent et construisent leur
    `argument_spec` sans rien reprocher. Il a fallu les **exécuter** contre une
    plateforme réelle pour que le défaut sorte. C'est la règle du dépôt,
    vérifiée à ses dépens : un fichier qui s'analyse n'est pas un fichier qui
    s'exécute.
    """
    api = ScalewayApi(module)
    selector = spec.selector
    wants_one = spec.get_operation is not None and (
        (selector is not None and module.params.get(selector) is not None)
        or (selector is None and spec.list_operation is None)
    )

    try:
        if wants_one and spec.get_operation is not None:
            operation = spec.get_operation
            result: Any = api.fetch_one(operation)
        elif spec.list_operation is not None:
            operation = spec.list_operation
            result = api.fetch_all(operation)
        else:
            module.fail_json(msg=f"ce module exige {selector} : aucune opération de liste n'existe")
            return
    except ScalewayApiError as error:
        module.fail_json(msg=error.message, **error.details())
        return

    field_name = operation.payload_field or "result"
    module.exit_json(changed=False, **{field_name: result})


def _valeur_courante(ressource: dict[str, Any], nom: str) -> Any:
    """La valeur à comparer, quand l'écriture et la lecture ne nomment pas pareil.

    **Une écriture prend `backend_id`, la lecture rend `backend`.** Scaleway
    écrit la référence par son identifiant et la relit par l'objet entier :
    `UpdateFrontend` accepte `backend_id`, et `GetFrontend` répond
    `backend: {"id": ..., "name": ...}`. Chercher `backend_id` dans cette
    réponse ne trouve rien, la comparaison conclut « différent », et le module
    rend `changed` **à chaque exécution**.

    Le défaut a été trouvé en exerçant `lb_frontend` sur une plateforme réelle,
    pas en relisant : c'est exactement pourquoi l'exemple joue chaque écriture
    deux fois.

    **Deux** champs sur 95 sont dans ce cas, et les deux appartiennent à
    `Frontend` : `backend_id` et `certificate_id`. Un premier compte en annonçait
    cinq, tiré des seuls paramètres de corps sans vérifier contre le schéma de
    lecture : `Ip.lb_id`, `Route.backend_id` et
    `Server.admin_password_encryption_ssh_key_id` y figurent bien sous leur
    propre nom, et la comparaison directe les traitait déjà correctement.

    Un nombre publié dans un commentaire se vérifie comme un nombre publié
    ailleurs.

    La règle ne devine pas : elle ne s'applique **que** si le champ est absent
    de la réponse, que son nom finit par `_id`, et que la réponse porte un objet
    du nom restant avec une clé `id`. Les trois conditions ensemble ne
    décrivent qu'une chose.
    """
    if nom in ressource:
        return ressource[nom]
    if not nom.endswith("_id"):
        return None
    objet = ressource.get(nom[: -len("_id")])
    if isinstance(objet, dict) and "id" in objet:
        return objet["id"]
    return None


def _sans_ordre(valeur: Any) -> Any:
    """Rend une liste comparable sans son ordre, et sans perdre les doublons.

    Un vrai `set` dirait que `[a, a, b]` et `[a, b]` sont la même chose, ce qui
    est faux d'une liste de tags : l'un en porte deux, l'autre un. Le tri
    conserve les multiplicités.

    Les éléments peuvent ne pas être triables entre eux, un tableau de
    dictionnaires par exemple : le tri porte alors sur leur représentation, qui
    est stable et suffit à comparer deux collections.
    """
    if not isinstance(valeur, (list, tuple)):
        return valeur
    return sorted(valeur, key=repr)


def _cles_demandees(attendu: Any, observe: Any) -> Any:
    """Ne garde de l'observé que les clés que la demande porte.

    L'API enrichit : une requête pose `{"uri": ...}` et la réponse rend
    `{"uri": ..., "id": ..., "created_at": ...}`. Comparer les deux entiers
    conclut « différent » à chaque exécution sur des champs que personne n'a
    demandés.
    """
    if not isinstance(attendu, dict) or not isinstance(observe, dict):
        return observe
    return {cle: valeur for cle, valeur in observe.items() if cle in attendu}


#: Comment comparer, par nom de stratégie. Le générateur pose le nom, le
#: runtime applique. La table est **fermée** : un nom absent fait échouer le
#: module, parce que retomber en silence sur l'égalité stricte reproduirait
#: exactement le défaut qu'on corrige, en le rendant invisible.
_COMPARAISONS: dict[str, Any] = {
    "scalar": lambda attendu, observe: attendu == observe,
    "ordered_list": lambda attendu, observe: list(attendu or []) == list(observe or []),
    "set": lambda attendu, observe: _sans_ordre(attendu or []) == _sans_ordre(observe or []),
    "mapping": lambda attendu, observe: attendu == observe,
    "normalized_string": lambda attendu, observe: (
        str(attendu).strip().casefold() == str(observe).strip().casefold()
        if attendu is not None and observe is not None
        else attendu == observe
    ),
    "object_id": lambda attendu, observe: attendu == observe,
    "normalized_object": lambda attendu, observe: attendu == _cles_demandees(attendu, observe),
}


def _identique(strategie: str, attendu: Any, observe: Any) -> bool:
    """Le champ est-il déjà dans l'état demandé ?

    Une stratégie inconnue lève : le générateur et le runtime évoluent
    ensemble, et un module qui demanderait une comparaison que ce runtime ne
    sait pas faire doit le dire. Le repli silencieux sur l'égalité stricte
    donnerait un module qui croit comparer autrement, ce qui est le défaut
    d'origine rendu invisible.
    """
    comparer = _COMPARAISONS.get(strategie)
    if comparer is None:
        connues = ", ".join(sorted(_COMPARAISONS))
        raise ValueError(
            f"stratégie de comparaison inconnue de ce runtime : {strategie!r}. "
            f"Connues : {connues}. Le module a probablement été produit par un "
            "générateur plus récent que `module_utils`."
        )
    return bool(comparer(attendu, observe))


def _postconditions_non_tenues(
    spec: "ManageModule",
    demande: dict[str, Any],
    observe: dict[str, Any],
    strategies: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Ce que le playbook a demandé et que la relecture ne montre pas.

    **Découvrir l'écart maintenant plutôt qu'au playbook suivant.** L'API
    normalise, complète, et parfois refuse en silence : un champ qu'elle n'a pas
    appliqué ressort à l'exécution d'après en `changed=true`, indéfiniment, et
    personne ne relie ce symptôme à sa cause.

    La comparaison est **la même qu'à l'aller**. Comparer en ensemble pour
    décider d'écrire puis strictement pour vérifier ferait échouer sur un ordre
    que la première comparaison avait justement accepté.

    Deux familles de champs sortent de la vérification, et chacune pour une
    raison qui n'est pas la même :

    * les **secrets**, que l'API ne rend jamais. Les vérifier reviendrait à
      comparer une valeur à `None`, ce qui ressemble à une mesure et n'en est
      pas une ;
    * ceux qu'un **override** écarte, avec sa raison. Le cas prévu est un champ
      que l'API applique de façon différée : échouer dessus ferait échouer un
      playbook correct sur un délai.
    """
    hors_mesure = set(spec.secret_params) | set(spec.unverified_params)
    ecarts: dict[str, dict[str, Any]] = {}
    for nom, attendu in demande.items():
        if nom in hors_mesure:
            continue
        obtenu = _valeur_courante(observe, nom)
        if not _identique(strategies.get(nom, "scalar"), attendu, obtenu):
            ecarts[nom] = {"requested": attendu, "observed": obtenu}
    return ecarts


def explicit_nulls(
    spec: ManageModule, params: dict[str, Any], clearable: frozenset[str] = frozenset()
) -> list[str]:
    """Les champs effaçables que le playbook a explicitement mis à `null`.

    Une option omise porte `UNCHANGED`, jamais `None` : un `None` est donc un
    `null` écrit dans le playbook. `clearable` nomme ce que le runtime sait
    effacer, et c'est vide aujourd'hui : le jour où un champ s'y trouvera
    (#114), son `null` sera une demande à exécuter, pas une demande à refuser.
    """
    return [
        nom
        for nom, _entree in spec.nullable_params
        if nom not in clearable and nom in params and params[nom] is None
    ]


def _refus_du_null(noms: list[str]) -> str:
    """Le message qui nomme le champ, et dit quoi faire à la place."""
    if len(noms) == 1:
        return (
            f"{noms[0]} est explicitement à null, mais ce module ne sait pas encore "
            "effacer ce champ. Omettre l'option laisse la valeur actuelle inchangée."
        )
    return (
        f"{', '.join(noms)} sont explicitement à null, mais ce module ne sait pas encore "
        "effacer ces champs. Omettre les options laisse les valeurs actuelles inchangées."
    )


def _resolve_nullable(module: AnsibleModule, spec: ManageModule) -> None:
    """Retire le marqueur des options omises, et revalide les valeurs fournies.

    L'option est `raw` pour qu'Ansible laisse passer le marqueur ; il laisse
    donc aussi passer `stateful: "no"` sous forme de chaîne, là où `bool` l'aurait
    convertie. La valeur fournie repasse par le validateur d'Ansible, avec
    l'entrée de son type réel : mêmes conversions, mêmes messages, et le
    playbook ne voit aucune différence avec une option typée.

    Le marqueur est remplacé par `None` dans `module.params` plutôt que
    supprimé : c'est ce qu'Ansible publie dans `invocation`, et une option
    omise doit s'y lire comme avant.
    """
    for nom, entree in spec.nullable_params:
        valeur = module.params.get(nom)
        if isinstance(valeur, str) and valeur == UNCHANGED:
            module.params[nom] = None
            continue
        if valeur is None:
            continue
        resultat = ArgumentSpecValidator({nom: entree}).validate({nom: valeur})
        if resultat.error_messages:
            module.fail_json(msg="; ".join(resultat.error_messages))
            return
        module.params[nom] = resultat.validated_parameters[nom]


def run_manage_module(module: AnsibleModule, spec: ManageModule) -> None:
    """Amène une ressource existante à l'état que le playbook décrit.

    **Refuser un `null` explicite avant tout.** Il disparaissait dans la
    construction de la demande, avant la lecture, la comparaison et la
    vérification : le module rendait `ok` sur une description toujours là.
    Un `null` sur un champ que le runtime ne sait pas effacer est une demande
    qu'il ne peut pas tenir, et il le dit sans rien lire ni écrire (ADR-012).

    Quatre propriétés, et chacune répond à une façon connue de se tromper.

    **Lire d'abord.** Sans lecture, un module ne peut pas savoir s'il change
    quelque chose, et `changed` devient un mensonge poli. La ressource est donc
    lue avant toute écriture, par la lecture unitaire que le générateur a
    trouvée.

    **N'écrire que la différence.** Envoyer tout le corps à chaque exécution
    écraserait les champs qu'un autre playbook gère, et rendrait `changed` à
    chaque fois. Seuls les paramètres **fournis** et **différents** partent.

    **En check mode, ne rien écrire et dire quoi.** Un check mode qui annonce
    un changement sans dire lequel n'aide personne à décider.

    **Rendre l'état observé, pas celui qu'on a envoyé.** La ressource est relue
    après l'écriture : l'API normalise, complète, et parfois refuse en silence.
    Ce que le module rend est ce que l'API dit, pas ce qu'on lui a demandé.

    **Et le vérifier.** Relire sans regarder ce qu'on a relu laissait passer un
    champ que l'API n'a pas appliqué : il ressortait au playbook suivant en
    `changed=true`, indéfiniment, et personne ne reliait ce symptôme à sa
    cause. Un écart fait échouer le module en nommant le champ, le demandé et
    l'observé, et `changed` reste vrai parce que la ressource, elle, a bougé.

    **Comparer comme le champ le demande.** L'égalité stricte rendait `changed`
    à chaque exécution sur un champ que l'API réordonne ou normalise, et un
    module qui rend `changed` à chaque fois n'est pas idempotent quoi qu'il
    affiche. La stratégie vient du générateur, qui la tient du type ou d'un
    override : rien ne se trie au hasard ici, et une stratégie inconnue de ce
    runtime le fait échouer plutôt que retomber en silence sur l'égalité
    stricte.
    """
    nuls = explicit_nulls(spec, module.params)
    if nuls:
        module.fail_json(msg=_refus_du_null(nuls))
        return
    _resolve_nullable(module, spec)

    api = ScalewayApi(module)

    try:
        courant = api.fetch_one(spec.read_operation)
    except ScalewayApiError as error:
        module.fail_json(msg=error.message, **error.details())
        return

    if not isinstance(courant, dict):
        module.fail_json(
            msg=(f"{spec.read_operation.id} n'a pas rendu un objet, donc rien ne peut être comparé")
        )
        return

    demande = {
        nom: module.params[nom] for nom in spec.managed_params if module.params.get(nom) is not None
    }

    # **Un secret ne se compare pas, et il ne s'affiche pas non plus.** L'API ne
    # le rend jamais, donc `courant` ne le porte pas et la comparaison conclut
    # « différent » à chaque exécution : le champ part, et `changed` dit qu'on a
    # écrit plutôt qu'on a constaté une différence. C'est la seule chose vraie
    # qu'on puisse dire, et le rapport la publie dans les limites du module.
    #
    # Une condition explicite « si c'est un secret, écrire » a été écrite ici
    # puis retirée : elle ne changeait le résultat dans aucun cas atteignable,
    # et une garde qu'aucune mutation ne fait mordre est un commentaire. Ce qui
    # reste, et qui compte, est que la valeur ne fuit pas dans le `diff`.
    strategies = dict(spec.comparisons)
    ecarts = {
        nom: valeur
        for nom, valeur in demande.items()
        if not _identique(strategies.get(nom, "scalar"), valeur, _valeur_courante(courant, nom))
    }

    champ = spec.read_operation.payload_field or "resource"
    masque = "VALUE_SPECIFIED_IN_NO_LOG_PARAMETER"

    def _cote_du_diff(ressource: dict[str, Any], noms: Iterable[str]) -> dict[str, Any]:
        """Un côté du `diff`, lu **exactement** comme la comparaison le lit.

        **L'invariant, plus général que le correctif qui l'a fait écrire.** Toute
        projection qui sert à *comparer* l'état doit servir à *montrer* le diff.
        Les deux côtés passent donc par la même fonction, par construction, et
        non parce que quelqu'un a pensé à recopier l'appel.

        Ce que l'asymétrie donnait : `avant` passait par `_valeur_courante`,
        `apres` faisait un `apres.get(nom)` direct. Sur `lb_frontend.backend_id`,
        que la lecture rend sous `backend: {"id": ...}`, l'utilisateur voyait

            before: {backend_id: abc}
            after:  {backend_id: null}

        alors que l'API avait parfaitement rendu `backend.id`. Le module
        marchait ; le diff mentait, ce qui est pire qu'un module qui échoue.
        """
        return {
            nom: (masque if nom in spec.secret_params else _valeur_courante(ressource, nom))
            for nom in noms
        }

    avant = _cote_du_diff(courant, ecarts)
    apres_demande = {
        nom: (masque if nom in spec.secret_params else valeur) for nom, valeur in ecarts.items()
    }

    if not ecarts:
        module.exit_json(changed=False, **{champ: courant})
        return

    if module.check_mode:
        module.exit_json(
            changed=True,
            diff={"before": avant, "after": apres_demande},
            **{champ: courant},
        )
        return

    # **Un `PUT` remplace, un `PATCH` modifie.** N'envoyer que la différence à un
    # `PUT` efface silencieusement tout ce qu'on n'a pas nommé, ce qui est
    # exactement la raison pour laquelle les `PUT` d'Instance sont écartés par
    # override. Les écritures du Load Balancer sont dans ce cas (ADR-003), et
    # le module généré portait les deux phrases contradictoires dans sa
    # documentation :
    # « You must set all parameters », du contrat, et « writes only the fields
    # that differ », de ce runtime.
    #
    # Le corps d'un `PUT` reprend donc **tous** les champs gérés : la valeur
    # demandée quand le playbook en fournit une, la valeur relue sinon. Ce que
    # la lecture ne rend pas ne peut pas être conservé, et n'est pas envoyé :
    # le contrat ne dit pas ce qu'un champ absent vaut, et l'inventer serait
    # pire que l'omettre.
    #
    # `changed` continue de se décider sur `ecarts` : le corps grossit, le
    # verdict ne bouge pas, et l'idempotence tient.
    corps = ecarts
    if spec.update_operation.method.upper() == "PUT":
        corps = {}
        for nom in spec.managed_params:
            if nom in demande:
                corps[nom] = demande[nom]
                continue
            relu = _valeur_courante(courant, nom)
            if relu is not None:
                corps[nom] = relu

    try:
        api.request(
            spec.update_operation,
            params=build_query(spec.update_operation, module.params),
            body=corps,
        )
        apres = api.fetch_one(spec.read_operation)
    except ScalewayApiError as error:
        module.fail_json(msg=error.message, **error.details())
        return

    non_tenues = _postconditions_non_tenues(spec, demande, apres, strategies)
    if non_tenues:
        # **`changed` reste vrai, et c'est le point délicat.** L'API a accepté
        # l'écriture : la ressource a bougé. Un échec qui tairait `changed`
        # ferait croire à un playbook rejoué qu'il n'a rien fait, alors que la
        # machine, elle, a changé.
        module.fail_json(
            msg=(
                f"{len(non_tenues)} champ(s) écrit(s) que la relecture ne montre pas : "
                f"{', '.join(sorted(non_tenues))}. L'API a accepté la requête et rend "
                "autre chose : la valeur a pu être normalisée, ignorée, ou refusée en "
                "silence."
            ),
            changed=True,
            failed_postconditions=non_tenues,
            diff={"before": avant, "after": _cote_du_diff(apres, ecarts)},
            **{champ: apres},
        )
        return

    module.exit_json(
        changed=True,
        diff={
            "before": avant,
            "after": _cote_du_diff(apres, ecarts),
        },
        **{champ: apres},
    )


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
    # Sous les deux formes, `action` nomme ce qui est déclenché : la valeur
    # demandée quand le module en expose une, l'identifiant de l'opération
    # sinon. Un lecteur de journal veut savoir ce qui s'est passé, et
    # « MigrateLb » le dit mieux qu'un champ vide.
    action = (
        module.params.get(spec.action_parameter)
        if spec.action_parameter is not None
        else spec.operation.id
    )
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
