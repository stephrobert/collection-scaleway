"""Modèle intermédiaire d'un module Ansible, construit depuis le plan.

C'est **la seule source** de l'`argument_spec`, de la `DOCUMENTATION`, des
`EXAMPLES` et du `RETURN` d'un module. Deux sources pour une même chose
divergent toujours, et `ansible-test sanity` le dirait tard.

Ce fichier porte les décisions ; le renderer ne fait que les écrire. La règle
qui tranche les cas limites : **si un template a besoin d'un `if` sur autre
chose qu'une présence de valeur, la décision manque ici.**

Trois décisions valent d'être lues avant le code :

* **le sélecteur.** Un module d'information fusionne le GET et le LIST.
  L'identifiant fourni bascule sur le GET, absent bascule sur le LIST. Le
  sélecteur est calculé (le paramètre de chemin que le GET exige et que le LIST
  ne connaît pas), il n'est jamais écrit à la main ;
* **les paramètres de pagination ne sont pas des options.** `page` et `per_page`
  restent au runtime, qui parcourt toutes les pages. Les exposer permettrait de
  rendre une première page en silence, présentée comme une liste complète ;
* **les paramètres communs ne deviennent pas des options**, mais restent
  envoyés. Ils viennent du `module_utils` et du fragment de documentation ; si
  le contrat nomme un paramètre `project_id`, le runtime enverra la valeur du
  paramètre commun du même nom.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from generator.ansible.collection import Collection
from generator.ansible.mapping import COMMON_PARAMETERS, argument_spec_entry, no_log_de
from generator.ir.enums import ApiType, HTTPMethod, OperationKind, ParameterLocation
from generator.ir.models import ApiOperation, ApiParameter, ApiService
from generator.overrides.loader import OperationOverride, OverrideSet
from generator.parser.naming import pluralize_phrase
from generator.plan import OperationPlan, ProductPlan

#: Classes que le renderer sait produire aujourd'hui. Une classe absente n'est
#: pas ignorée : elle est rendue dans le rapport de génération avec sa raison.
RENDERABLE_KINDS: frozenset[OperationKind] = frozenset({OperationKind.INFO, OperationKind.ACTION})

#: Ce qu'on écrit quand le contrat ne décrit pas un paramètre. C'est une phrase
#: vraie, et elle vaut mieux qu'une description inventée ou qu'un nom de
#: paramètre recopié en guise de description, comme le fait la collection
#: officielle (`description: snapshot_id`).
UNDOCUMENTED = "Not documented by the Scaleway API contract."

#: Ajouté à la description d'un paramètre que le contrat déclare déprécié.
DEPRECATED_NOTICE = "Deprecated by the Scaleway API contract."

#: Identifiant d'exemple. Un exemple montre une forme, pas une ressource.
EXAMPLE_ID = "11111111-2222-3333-4444-555555555555"


class ModuleModelError(ValueError):
    """Le plan ne permet pas de construire un module cohérent."""


class UnsupportedKind(ModuleModelError):
    """La classe d'opération n'a pas encore de renderer."""


class AmbiguousModule(ModuleModelError):
    """Les opérations d'un module ne composent pas une forme connue."""


class ConflictingOption(ModuleModelError):
    """Deux opérations déclarent le même paramètre avec des types différents."""


class UnknownChoice(ModuleModelError):
    """Un override restreint un enum à une valeur que le contrat ne déclare pas."""


class UnreachableState(ModuleModelError):
    """Un override promet d'attendre un état qu'aucune lecture ne peut observer."""


@dataclass(frozen=True)
class AnsibleOption:
    """Une option du module, dans le vocabulaire d'Ansible.

    `to_argument_spec()` et `to_documentation()` lisent le même objet : c'est
    ce qui garantit que la documentation ne peut pas décrire autre chose que
    ce que le module accepte.
    """

    name: str
    type: str
    required: bool
    description: tuple[str, ...]
    choices: tuple[str, ...] = ()
    elements: str | None = None
    no_log: bool | None = None
    default: object | None = None

    def to_argument_spec(self) -> dict[str, Any]:
        entry: dict[str, Any] = {"type": self.type}
        if self.required:
            entry["required"] = True
        if self.default is not None:
            entry["default"] = self.default
        if self.choices:
            entry["choices"] = list(self.choices)
        if self.elements:
            entry["elements"] = self.elements
        if self.no_log is not None:
            entry["no_log"] = self.no_log
        return entry

    def to_documentation(self) -> dict[str, Any]:
        entry: dict[str, Any] = {"description": list(self.description), "type": self.type}
        if self.required:
            entry["required"] = True
        if self.default is not None:
            entry["default"] = self.default
        if self.choices:
            entry["choices"] = list(self.choices)
        if self.elements:
            entry["elements"] = self.elements
        return entry


@dataclass(frozen=True)
class OperationBinding:
    """Une opération telle que le runtime devra l'exécuter.

    Le vocabulaire est celui de `plugins/module_utils/scaleway.py::Operation` :
    ce modèle décrit exactement ce que le module généré déclarera.
    """

    id: str
    method: str
    path: str
    path_params: tuple[str, ...]
    query_params: tuple[str, ...]
    body_params: tuple[str, ...]
    payload_field: str | None
    is_list: bool
    page_param: str | None
    per_page_param: str | None
    #: Filtres que le contrat déclare `string` en décrivant la virgule comme
    #: séparateur, et qu'un override expose donc en liste. Le runtime les joint
    #: à l'envoi ; sans cette liste il n'aurait aucun moyen de les distinguer
    #: d'une valeur qui contient une virgule.
    summary: str | None
    description: str | None
    csv_params: tuple[str, ...] = ()

    @property
    def documentation_line(self) -> str | None:
        """La phrase du contrat qui décrit l'opération, description d'abord."""
        return self.description or self.summary


@dataclass(frozen=True)
class ReturnValue:
    """Une clé du `RETURN` d'un module."""

    name: str
    description: tuple[str, ...]
    returned: str
    type: str
    elements: str | None = None

    def to_documentation(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "description": list(self.description),
            "returned": self.returned,
            "type": self.type,
        }
        if self.elements:
            entry["elements"] = self.elements
        return entry


@dataclass(frozen=True)
class ExampleTask:
    """Une tâche d'exemple, construite depuis le contrat et le modèle."""

    name: str
    module: str
    parameters: dict[str, Any]
    register: str

    def to_documentation(self) -> dict[str, Any]:
        return {
            "name": self.name,
            self.module: dict(self.parameters),
            "register": self.register,
        }


@dataclass(frozen=True)
class AnsibleModuleSpec:
    """Tout ce qu'il faut pour écrire un module, et rien de plus."""

    name: str
    kind: OperationKind
    collection: Collection
    short_description: str
    description: tuple[str, ...]
    options: tuple[AnsibleOption, ...]
    returns: tuple[ReturnValue, ...]
    examples: tuple[ExampleTask, ...]
    get_operation: OperationBinding | None
    list_operation: OperationBinding | None
    selector: str | None
    #: L'opération déclenchée par un module d'action.
    action_operation: OperationBinding | None = None
    #: La lecture unitaire de la même ressource, pour attendre l'état visé.
    read_operation: OperationBinding | None = None
    #: Le paramètre qui porte l'action demandée.
    action_parameter: str | None = None
    #: Champ de la ressource qui porte son état, déclaré par un override.
    state_field: str = "state"
    #: Action -> état attendu, déclaré par un override. Vide : pas d'attente.
    wait_states: tuple[tuple[str, str], ...] = ()
    #: Ce que le contrat ne dit pas, remonté par le rapport de génération.
    limits: tuple[str, ...] = ()

    @property
    def waitable(self) -> bool:
        """Vrai quand le module accepte `wait` et `wait_timeout`."""
        return bool(self.wait_states)

    @property
    def fqcn(self) -> str:
        return self.collection.module_fqcn(self.name)

    def argument_spec(self) -> dict[str, dict[str, Any]]:
        """Les options propres au module. Les communes viennent du runtime."""
        return {option.name: option.to_argument_spec() for option in self.options}

    def documentation(self) -> dict[str, Any]:
        """Le bloc `DOCUMENTATION`, construit depuis les mêmes options."""
        return {
            "module": self.name,
            "short_description": self.short_description,
            "version_added": self.collection.version,
            "description": list(self.description),
            "author": list(self.collection.authors),
            "options": {option.name: option.to_documentation() for option in self.options},
            "extends_documentation_fragment": self.doc_fragments(),
        }

    def doc_fragments(self) -> list[str]:
        """Les fragments dont ce module hérite ses paramètres communs."""
        fragments = [self.collection.doc_fragment]
        if self.waitable:
            fragments.append(f"{self.collection.fqcn}.waitable")
        return fragments

    def return_documentation(self) -> dict[str, Any]:
        return {value.name: value.to_documentation() for value in self.returns}

    def examples_documentation(self) -> list[dict[str, Any]]:
        return [example.to_documentation() for example in self.examples]


def build_module_specs(
    plan: ProductPlan,
    collection: Collection,
    *,
    only: tuple[str, ...] = (),
) -> tuple[tuple[AnsibleModuleSpec, ...], tuple[tuple[str, str], ...]]:
    """Construit les modèles des modules d'un plan.

    Rend deux choses, et jamais une seule : les modules construits, et ceux qui
    ne l'ont pas été **avec leur raison**. Un module qui disparaît en silence
    d'une génération est exactement ce que ce projet refuse.

    `only` restreint la production à des modules nommés. Ce n'est pas un filtre
    de confort : l'étape 2 du projet ne produit qu'un module, et la liste est
    déclarée dans le Makefile plutôt que devinée ici.

    Un module que le modèle ne sait pas construire est écarté **avec le message
    de l'erreur**, sauf s'il a été demandé nommément : ce qu'on a demandé doit
    sortir, ou faire échouer la commande. Ce qu'on n'a pas demandé se lit dans
    le rapport, jamais dans le silence.
    """
    specs: list[AnsibleModuleSpec] = []
    skipped: list[tuple[str, str]] = []

    for name, plans in plan.modules().items():
        if only and name not in only:
            skipped.append((name, "hors du périmètre demandé"))
            continue
        try:
            specs.append(build_module_spec(name, plans, plan.service, collection, plan.overrides))
        except ModuleModelError as error:
            if only:
                raise
            skipped.append((name, str(error)))

    unknown = tuple(
        sorted(set(only) - {spec.name for spec in specs} - {name for name, _ in skipped})
    )
    if unknown:
        raise ModuleModelError(f"module(s) demandé(s) inconnu(s) du plan : {list(unknown)}")

    return tuple(specs), tuple(skipped)


def build_module_spec(
    name: str,
    plans: tuple[OperationPlan, ...],
    service: ApiService,
    collection: Collection,
    overrides: OverrideSet | None = None,
) -> AnsibleModuleSpec:
    """Construit le modèle d'un module à partir de ses opérations."""
    kinds = {item.kind for item in plans}
    if len(kinds) != 1:
        raise AmbiguousModule(f"{name} : classes mélangées {sorted(k.value for k in kinds)}")
    kind = kinds.pop()
    if kind not in RENDERABLE_KINDS:
        raise UnsupportedKind(f"classe {kind.value.upper()} : aucun renderer à ce stade")

    if kind is OperationKind.ACTION:
        return _build_action_module(name, plans, service, collection, overrides)

    getters = [item for item in plans if not _is_list(item.operation)]
    listers = [item for item in plans if _is_list(item.operation)]
    if len(getters) > 1 or len(listers) > 1:
        raise AmbiguousModule(
            f"{name} : {len(getters)} lecture(s) unitaire(s) et {len(listers)} liste(s), "
            "le modèle n'en attend au plus qu'une de chaque"
        )
    if not getters and not listers:
        raise AmbiguousModule(f"{name} : aucune opération à exécuter")

    # Un module d'information porte au plus deux opérations, chacune avec sa
    # propre clé d'override. On les cherche séparément plutôt que de supposer
    # qu'un seul override vaut pour les deux.
    override_get = overrides.get(getters[0].operation.key) if overrides and getters else None
    override_list = overrides.get(listers[0].operation.key) if overrides and listers else None

    get_operation = _bind(getters[0].operation, override=override_get) if getters else None
    list_operation = _bind(listers[0].operation, override=override_list) if listers else None
    selector = _selector(get_operation, list_operation, name)

    operations = [item.operation for item in plans]
    options, limits = _build_options(
        operations, ("zone", "region", selector or ""), override_list or override_get
    )
    resource = plans[0].resource

    return AnsibleModuleSpec(
        name=name,
        kind=kind,
        collection=collection,
        short_description=_short_description(service, resource),
        description=_description(get_operation, list_operation),
        options=options,
        returns=_returns(get_operation, list_operation, selector),
        examples=_examples(name, collection, options, selector, get_operation, list_operation),
        get_operation=get_operation,
        list_operation=list_operation,
        selector=selector,
        limits=limits,
    )


def _build_action_module(
    name: str,
    plans: tuple[OperationPlan, ...],
    service: ApiService,
    collection: Collection,
    overrides: OverrideSet | None,
) -> AnsibleModuleSpec:
    """Construit le modèle d'un module d'action.

    Un module d'action déclenche **une** opération. Deux choses ne viennent pas
    du contrat et se déclarent donc par un override, chacune avec sa raison :
    les valeurs d'enum réellement exposées, et l'état qu'une action laisse
    derrière elle.
    """
    if len(plans) != 1:
        raise AmbiguousModule(
            f"{name} : {len(plans)} opérations pour un module d'action, le modèle en attend une"
        )
    item = plans[0]
    override = overrides.get(item.operation.key) if overrides else None
    masques = frozenset(
        nom
        for nom, restriction in (override.parameters if override else {}).items()
        if restriction.expose is False
    )
    action_operation = _bind(item.operation, masques, override)

    parametre = _action_parameter(item.operation, name)
    identifiants = tuple(
        nom for nom in action_operation.path_params if nom not in ("zone", "region")
    )
    options, limits = _build_options(
        [item.operation],
        ("zone", "region", *identifiants, parametre),
        override,
    )
    choix = next((o.choices for o in options if o.name == parametre), ())

    wait_states, state_field, read_operation = _wait_contract(name, service, item, override, choix)
    resource = item.resource

    return AnsibleModuleSpec(
        name=name,
        kind=item.kind,
        collection=collection,
        short_description=_action_short_description(service, resource),
        description=_action_description(action_operation, choix),
        options=options,
        returns=_action_returns(action_operation, parametre, state_field, wait_states),
        examples=_action_examples(name, collection, options, parametre, action_operation),
        get_operation=None,
        list_operation=None,
        selector=None,
        action_operation=action_operation,
        read_operation=read_operation,
        action_parameter=parametre,
        state_field=state_field,
        wait_states=wait_states,
        limits=limits,
    )


def _action_parameter(operation: ApiOperation, name: str) -> str:
    """Le paramètre de corps qui porte l'action, déduit du contrat.

    C'est le seul paramètre de corps qui soit un enum. Plusieurs, ou aucun, et
    le modèle refuse : choisir au hasard produirait un module qui déclenche
    autre chose que ce qu'on croit.
    """
    candidats = [
        parameter.name
        for parameter in operation.parameters
        if parameter.location is ParameterLocation.BODY and parameter.type is ApiType.ENUM
    ]
    if len(candidats) != 1:
        raise AmbiguousModule(
            f"{name} : {len(candidats)} paramètre(s) d'action dans le corps de "
            f"{operation.id} ({candidats}), le modèle en attend exactement un"
        )
    return candidats[0]


def _wait_contract(
    name: str,
    service: ApiService,
    item: OperationPlan,
    override: OperationOverride | None,
    choix: tuple[str, ...],
) -> tuple[tuple[tuple[str, str], ...], str, OperationBinding | None]:
    """Ce que le module attendra après l'action, ou rien s'il ne sait pas.

    Le contrat ne dit jamais dans quel état une action laisse la ressource :
    la correspondance vient d'un override. Deux refus, parce qu'une attente
    fausse est pire qu'une absence d'attente :

    * un état promis pour une action que le module n'expose pas ;
    * une attente déclarée alors qu'aucune lecture unitaire de la ressource
      n'existe pour l'observer.
    """
    if override is None or override.wait is None:
        return (), "state", None

    inconnues = sorted(set(override.wait.states) - set(choix))
    if inconnues:
        raise UnreachableState(
            f"{name} : `wait` promet un état pour {inconnues}, "
            f"que le module n'expose pas ({list(choix)})"
        )

    lecture = _unitary_read(service, item.resource)
    if lecture is None:
        raise UnreachableState(
            f"{name} : `wait` déclare des états attendus, et aucune lecture unitaire "
            f"de la ressource '{item.resource}' n'existe pour les observer"
        )

    _check_states_exist(name, service, item.resource, override.wait.field, override.wait.states)

    etats = tuple(sorted(override.wait.states.items()))
    return etats, override.wait.field, lecture


def _check_states_exist(
    name: str,
    service: ApiService,
    resource: str,
    field: str,
    states: dict[str, str],
) -> None:
    """Refuse un état attendu que le contrat ne déclare pas.

    Un override d'attente est écrit à la main : rien n'empêchait jusqu'ici d'y
    poser un état qui n'existe pas. Le module rendu attendait alors un état
    jamais atteint, et échouait après `wait_timeout` sur une ressource qui
    avait pourtant bien changé.

    Ce n'est pas une hypothèse : `stop_in_place` attendait `stopped`, alors que
    le contrat déclare `stopped in place`, un état **distinct**. La faute a
    vécu jusqu'à ce qu'on la cherche.

    L'enum se déduit mécaniquement, sans deviner : le contrat nomme l'enum d'un
    champ `<schéma de la ressource>.<Champ>`. Quand il est introuvable, ce
    n'est pas une raison de laisser passer : le générateur ne devine pas, il
    refuse et le dit.
    """
    operation = _unitary_read_operation(service, resource)
    schema = operation.response.payload_schema if operation and operation.response else None
    if not schema:
        raise UnreachableState(
            f"{name} : `wait` déclare des états attendus, et la lecture unitaire de "
            f"'{resource}' ne dit pas quel schéma elle rend : impossible de vérifier "
            "que ces états existent"
        )

    attendu = f"{schema}.{_pascal(field)}"
    declares = next((e.values for e in service.enums if e.name == attendu), None)
    if declares is None:
        raise UnreachableState(
            f"{name} : `wait` porte sur le champ '{field}', dont le contrat ne "
            f"déclare aucun enum ({attendu} introuvable) : les états attendus ne "
            "peuvent pas être vérifiés"
        )

    inconnus = sorted({etat for etat in states.values() if etat not in declares})
    if inconnus:
        raise UnreachableState(
            f"{name} : `wait` attend {inconnus}, que le contrat ne déclare pas. "
            f"Le champ '{field}' vaut {list(declares)}"
        )


def _pascal(field: str) -> str:
    """`state` -> `State`, `ping_status` -> `PingStatus`.

    C'est la convention de nommage des enums du contrat, pas une invention :
    `scaleway.instance.v1.Server.State` porte les valeurs du champ `state` de
    `scaleway.instance.v1.Server`.
    """
    return "".join(morceau.capitalize() for morceau in field.split("_"))


def _unitary_read(service: ApiService, resource: str) -> OperationBinding | None:
    """La lecture unitaire de la ressource, celle qui sert à observer un état."""
    operation = _unitary_read_operation(service, resource)
    return _bind(operation) if operation is not None else None


def _unitary_read_operation(service: ApiService, resource: str) -> ApiOperation | None:
    """La même, non aplatie : la vérification des états a besoin de sa réponse."""
    for operation in service.operations:
        if operation.resource != resource:
            continue
        if operation.http_method is not HTTPMethod.GET or _is_list(operation):
            continue
        if operation.response is None or not operation.response.payload_field:
            continue
        return operation
    return None


def _action_description(
    operation: OperationBinding,
    choices: tuple[str, ...],
) -> tuple[str, ...]:
    """La description du contrat, sans les actions que le module n'expose pas.

    Le contrat décrit ses sept actions en autant de puces. En recopier sept
    pour un module qui en accepte quatre ferait une documentation qui promet ce
    que l'`argument_spec` refuse — et `ansible-test` ne le verrait pas.

    C'est un nettoyage, pas une réécriture : les puces conservées sont celles
    du contrat, mot pour mot.
    """
    texte = operation.documentation_line
    if not texte:
        return ()

    gardees = []
    for ligne in texte.split("\n"):
        nomme = re.match(r"\* `([a-z0-9_]+)`\s*:", ligne.strip())
        if nomme and nomme.group(1) not in choices:
            continue
        gardees.append(ligne)
    return ("\n".join(gardees).strip(),)


def _action_short_description(service: ApiService, resource: str) -> str:
    product = (service.title or service.name).removesuffix(" API")
    return f"Perform an action on a Scaleway {product} {resource.replace('_', ' ')}"


def _action_returns(
    operation: OperationBinding,
    action_parameter: str,
    state_field: str,
    wait_states: tuple[tuple[str, str], ...],
) -> tuple[ReturnValue, ...]:
    valeurs = [
        ReturnValue(
            name=action_parameter,
            description=("The action that was requested.",),
            returned="always",
            type="str",
        )
    ]
    if wait_states:
        valeurs.append(
            ReturnValue(
                name=state_field,
                description=("State of the resource once the action completed.",),
                returned="when the module waited for the action to complete",
                type="str",
            )
        )
    if operation.payload_field:
        valeurs.append(
            ReturnValue(
                name=operation.payload_field,
                description=(operation.documentation_line or UNDOCUMENTED,),
                returned="when the API returns it",
                type="dict",
            )
        )
    return tuple(valeurs)


def _action_examples(
    name: str,
    collection: Collection,
    options: tuple[AnsibleOption, ...],
    action_parameter: str,
    operation: OperationBinding,
) -> tuple[ExampleTask, ...]:
    """Un exemple par action exposée : c'est ce qu'un lecteur vient chercher."""
    module = collection.module_fqcn(name)
    requis = {
        option.name: _example_value(option)
        for option in options
        if option.required and option.name != action_parameter
    }
    action_option = next(option for option in options if option.name == action_parameter)

    return tuple(
        ExampleTask(
            name=f"{valeur.replace('_', ' ').capitalize()} an Instance",
            module=module,
            parameters={**requis, action_parameter: valeur},
            register="result",
        )
        for valeur in action_option.choices
    )


def _is_list(operation: ApiOperation) -> bool:
    """Une opération est une liste quand sa réponse porte un tableau."""
    return bool(operation.response and operation.response.is_list)


def _bind(
    operation: ApiOperation,
    hidden: frozenset[str] = frozenset(),
    override: OperationOverride | None = None,
) -> OperationBinding:
    """Traduit une opération de l'IR en ce que le runtime exécutera.

    `hidden` retire les paramètres qu'un override masque : le module ne peut
    pas les recevoir, donc les déclarer dans la liaison serait annoncer un
    envoi qui n'aura jamais lieu.

    `override` sert à une seule chose ici, et c'est délibérément peu : savoir
    quels filtres le contrat décrit comme séparés par des virgules. Le runtime
    ne peut pas le deviner d'une chaîne, et le générateur n'a pas à le deviner
    non plus.
    """
    pagination = operation.pagination
    paginated = {pagination.page_param, pagination.per_page_param} if pagination else set()

    path_params = tuple(
        parameter.name
        for parameter in operation.parameters
        if parameter.location is ParameterLocation.PATH
    )
    query_params = tuple(
        parameter.name
        for parameter in operation.parameters
        if parameter.location is ParameterLocation.QUERY and parameter.name not in paginated
    )
    body_params = tuple(
        parameter.name
        for parameter in operation.parameters
        if parameter.location is ParameterLocation.BODY and parameter.name not in hidden
    )

    restrictions = override.parameters if override else {}
    csv_params = tuple(
        nom
        for nom in query_params
        for restriction in (restrictions.get(nom),)
        if restriction is not None and restriction.csv
    )

    return OperationBinding(
        id=operation.id,
        method=operation.http_method.value,
        path=operation.path,
        path_params=path_params,
        query_params=query_params,
        body_params=body_params,
        csv_params=csv_params,
        payload_field=operation.response.payload_field if operation.response else None,
        is_list=_is_list(operation),
        page_param=pagination.page_param if pagination else None,
        per_page_param=pagination.per_page_param if pagination else None,
        summary=operation.summary,
        description=operation.description,
    )


def _selector(
    get_operation: OperationBinding | None,
    list_operation: OperationBinding | None,
    name: str,
) -> str | None:
    """Le paramètre qui fait basculer un module d'information vers le GET.

    C'est le paramètre de chemin que la lecture unitaire exige et que la liste
    ne connaît pas : `server_id` pour `instance_server_info`. Il se déduit, il
    ne se déclare pas, sinon il faudrait le tenir à jour à la main.

    Zéro candidat ou plusieurs, c'est une forme que le modèle ne sait pas
    décrire : il refuse plutôt que d'en choisir un.
    """
    if get_operation is None or list_operation is None:
        return None

    candidates = tuple(
        parameter
        for parameter in get_operation.path_params
        if parameter not in list_operation.path_params
    )
    if len(candidates) != 1:
        raise AmbiguousModule(
            f"{name} : {len(candidates)} identifiant(s) distinguent {get_operation.id} "
            f"de {list_operation.id} ({list(candidates)}), le modèle en attend exactement un"
        )
    return candidates[0]


def _build_options(
    operations: list[ApiOperation],
    priorities: tuple[str, ...] = (),
    override: OperationOverride | None = None,
) -> tuple[tuple[AnsibleOption, ...], tuple[str, ...]]:
    """Fusionne les paramètres des opérations en options de module.

    Une option est `required` seulement si **toutes** les opérations du module
    la déclarent et l'exigent : `server_id` est obligatoire pour `GetServer` et
    inconnu de `ListServers`, donc optionnel pour le module, et c'est
    précisément ce qui permet au sélecteur de fonctionner.
    """
    seen: dict[str, ApiParameter] = {}
    presence: dict[str, int] = {}
    required_in: dict[str, int] = {}
    limits: list[str] = []

    for operation in operations:
        paginated = set()
        if operation.pagination:
            paginated = {operation.pagination.page_param, operation.pagination.per_page_param}

        for parameter in operation.parameters:
            if parameter.name in paginated:
                # La pagination appartient au runtime : l'exposer permettrait
                # de rendre une première page en silence.
                continue
            if parameter.name in COMMON_PARAMETERS:
                # Porté par le module_utils et le fragment de documentation.
                continue

            known = seen.get(parameter.name)
            if known is not None and known.type is not parameter.type:
                raise ConflictingOption(
                    f"{parameter.name} : {known.type.value} pour une opération, "
                    f"{parameter.type.value} pour une autre"
                )
            seen.setdefault(parameter.name, parameter)
            presence[parameter.name] = presence.get(parameter.name, 0) + 1
            if parameter.required:
                required_in[parameter.name] = required_in.get(parameter.name, 0) + 1

    total = len(operations)
    options: list[AnsibleOption] = []
    for name, parameter in seen.items():
        restriction = (override.parameters.get(name) if override else None) or None
        if restriction is not None and restriction.expose is False:
            limits.append(f"{name} : paramètre du contrat masqué par override")
            continue

        required = presence[name] == total and required_in.get(name, 0) == total
        if restriction is not None and restriction.required is not None:
            required = restriction.required
        entry = argument_spec_entry(parameter)
        description, missing = _option_description(parameter)
        if missing:
            limits.append(f"{name} : aucune description dans le contrat")
        if parameter.type is ApiType.ARRAY and parameter.item_type is None:
            limits.append(f"{name} : tableau sans type d'éléments dans le contrat, `str` par repli")

        choices = tuple(parameter.enum_values)
        if restriction is not None and restriction.choices:
            inconnues = sorted(set(restriction.choices) - set(choices))
            if inconnues:
                raise UnknownChoice(
                    f"{name} : l'override retient {inconnues}, que le contrat ne déclare pas "
                    f"({list(choices)}). L'API a bougé, ou la valeur est fautive."
                )
            ecartees = [valeur for valeur in choices if valeur not in restriction.choices]
            limits.append(
                f"{name} : {len(ecartees)} valeur(s) du contrat non exposées par override "
                f"({', '.join(ecartees)})"
            )
            choices = restriction.choices

        # **Un filtre que le contrat décrit comme séparé par des virgules.**
        # Le contrat le déclare `string`, et sa description dit « use commas to
        # separate them » : l'override lit cette phrase, il ne devine rien. Le
        # module l'expose en liste, et le runtime joint. Sans ça, `tags: [a, b]`
        # en YAML ne lève aucune erreur et n'atteint aucune machine.
        type_ansible = str(entry["type"])
        elements = str(entry["elements"]) if "elements" in entry else None
        if restriction is not None and restriction.csv:
            if parameter.type is not ApiType.STRING:
                raise ConflictingOption(
                    f"{name} : `csv` ne vaut que pour un paramètre que le contrat "
                    f"déclare `string`, et celui-ci est {parameter.type.value}."
                )
            type_ansible = "list"
            elements = "str"
            limits.append(f"{name} : exposé en liste, joint par des virgules (override)")

        options.append(
            AnsibleOption(
                name=name,
                type=type_ansible,
                required=required,
                description=description,
                choices=choices,
                elements=elements,
                no_log=no_log_de(parameter),
                default=entry.get("default"),
            )
        )

    ordre = tuple(nom for nom in priorities if nom)
    return tuple(sorted(options, key=lambda option: _option_order(option, ordre))), tuple(limits)


def _option_order(option: AnsibleOption, priorities: tuple[str, ...]) -> tuple[int, str]:
    """Ordre d'affichage : les options qui racontent le module, puis le reste.

    Cet ordre est celui de la lecture : *où*, *quoi*, *quelle action*, puis les
    filtres par ordre alphabétique. Il est total et ne dépend que du modèle,
    donc la génération reste déterministe.
    """
    if option.name in priorities:
        return (priorities.index(option.name), option.name)
    return (len(priorities), option.name)


def _option_description(parameter: ApiParameter) -> tuple[tuple[str, ...], bool]:
    """Description d'une option, prise au contrat et jamais inventée."""
    lines: list[str] = []
    missing = not parameter.description
    lines.append(parameter.description or UNDOCUMENTED)
    if parameter.deprecated:
        lines.append(DEPRECATED_NOTICE)
    return tuple(lines), missing


def _short_description(service: ApiService, resource: str) -> str:
    """Phrase courte du module : ce qu'il fait, sur quelle ressource.

    Elle se construit mécaniquement à partir du titre du contrat et de la
    ressource déduite. Ce n'est pas une description empruntée à une opération :
    un module qui sert le GET et le LIST n'est décrit correctement par aucune
    des deux.
    """
    product = (service.title or service.name).removesuffix(" API")
    return f"Gather information about Scaleway {product} {pluralize_phrase(resource)}"


def _description(
    get_operation: OperationBinding | None,
    list_operation: OperationBinding | None,
) -> tuple[str, ...]:
    """Description longue : les phrases du contrat, dans l'ordre d'usage."""
    lines: list[str] = []
    for operation in (get_operation, list_operation):
        if operation is None:
            continue
        line = operation.documentation_line
        if line and line not in lines:
            lines.append(line)
    return tuple(lines)


def _returns(
    get_operation: OperationBinding | None,
    list_operation: OperationBinding | None,
    selector: str | None,
) -> tuple[ReturnValue, ...]:
    """Les clés que le module rend, décrites par le contrat qui les produit."""
    values: list[ReturnValue] = []

    if get_operation is not None and get_operation.payload_field:
        values.append(
            ReturnValue(
                name=get_operation.payload_field,
                description=(get_operation.documentation_line or UNDOCUMENTED,),
                returned=f"when I({selector}) is provided" if selector else "success",
                type="dict",
            )
        )
    if list_operation is not None and list_operation.payload_field:
        values.append(
            ReturnValue(
                name=list_operation.payload_field,
                description=(list_operation.documentation_line or UNDOCUMENTED,),
                returned=f"when I({selector}) is omitted" if selector else "success",
                type="list",
                elements="dict",
            )
        )

    # **Un module rend toujours quelque chose, donc il le documente toujours.**
    # Quand le contrat ne nomme aucun champ porteur, le runtime rend le corps
    # entier sous `result`, et le `RETURN` restait vide : quatre modules
    # publiaient `{}` en documentant leur retour, alors qu'ils rendaient bien
    # une valeur. Un lecteur ne pouvait pas savoir quoi enregistrer, et
    # `ansible-test sanity` ne dit rien d'un `RETURN` vide.
    #
    # `result` n'est pas un choix arbitraire : c'est le nom que
    # `run_info_module` emploie déjà, `operation.payload_field or "result"`.
    # Le documenter ici ne fait que dire ce que le code fait.
    if not values:
        source = get_operation or list_operation
        if source is not None:
            values.append(
                ReturnValue(
                    name="result",
                    description=(
                        source.documentation_line or UNDOCUMENTED,
                        # En anglais comme le reste de la documentation d'un
                        # module : c'est la langue du contrat et celle
                        # d'`UNDOCUMENTED`. Le français reste au code.
                        "The API contract names no payload field for this "
                        "operation: the response body is returned as is.",
                    ),
                    returned="success",
                    type="dict",
                )
            )
    return tuple(values)


def _examples(
    name: str,
    collection: Collection,
    options: tuple[AnsibleOption, ...],
    selector: str | None,
    get_operation: OperationBinding | None,
    list_operation: OperationBinding | None,
) -> tuple[ExampleTask, ...]:
    """Un exemple par mode du module : lire une ressource, lister les autres."""
    module = collection.module_fqcn(name)
    required = {option.name: _example_value(option) for option in options if option.required}
    examples: list[ExampleTask] = []

    if get_operation is not None and selector is not None:
        parameters = dict(required)
        parameters[selector] = EXAMPLE_ID
        examples.append(
            ExampleTask(
                name=get_operation.summary or f"Run {get_operation.id}",
                module=module,
                parameters=parameters,
                register="result",
            )
        )
    if list_operation is not None:
        examples.append(
            ExampleTask(
                name=list_operation.summary or f"Run {list_operation.id}",
                module=module,
                parameters=dict(required),
                register="result",
            )
        )
    if not examples and get_operation is not None:
        examples.append(
            ExampleTask(
                name=get_operation.summary or f"Run {get_operation.id}",
                module=module,
                parameters=dict(required),
                register="result",
            )
        )
    return tuple(examples)


def _example_value(option: AnsibleOption) -> Any:
    """Valeur d'exemple d'une option, déterministe et jamais aléatoire."""
    if option.choices:
        return option.choices[0]
    if option.name.endswith("_id"):
        return EXAMPLE_ID
    return {
        "int": 1,
        "float": 1.0,
        "bool": True,
        "list": [],
        "dict": {},
    }.get(option.type, f"<{option.name}>")
