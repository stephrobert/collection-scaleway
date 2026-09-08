"""Traduction d'un document OpenAPI Scaleway vers l'IR canonique.

Le parser ne décide rien : il traduit. Toute décision (est-ce un module, sous
quel nom, exposé ou non) appartient au classifieur et aux overrides. Ce qu'il
ne comprend pas, il le signale dans `ApiService.warnings` plutôt que de le
laisser disparaître.

Ce que le document publié ne porte pas est documenté dans
`docs/architecture/contrats-scaleway.md` et mesuré ici :

* les tableaux d'un corps de requête n'ont pas de `items`, donc le type des
  éléments est inconnu ;
* aucun champ de corps n'est déclaré `required`, y compris ceux que l'API
  refuse d'omettre ;
* les réponses de liste ne portent pas `total_count`, que le SDK expose.
"""

from __future__ import annotations

from typing import Any

from generator.ir.enums import ApiType, HTTPMethod, ParameterLocation, Scope
from generator.ir.models import (
    ApiEnum,
    ApiField,
    ApiObject,
    ApiOperation,
    ApiParameter,
    ApiResponse,
    ApiService,
    Pagination,
)
from generator.parser.naming import singularize_phrase, snake_case
from generator.source.base import SpecDocument

#: Méthodes HTTP qu'un document Scaleway peut porter sur un chemin.
_METHODS: dict[str, HTTPMethod] = {
    "get": HTTPMethod.GET,
    "post": HTTPMethod.POST,
    "put": HTTPMethod.PUT,
    "patch": HTTPMethod.PATCH,
    "delete": HTTPMethod.DELETE,
}

_SCALAR_TYPES: dict[str, ApiType] = {
    "string": ApiType.STRING,
    "integer": ApiType.INTEGER,
    "number": ApiType.NUMBER,
    "boolean": ApiType.BOOLEAN,
    "array": ApiType.ARRAY,
    "object": ApiType.OBJECT,
}

#: Segments de chemin qui nomment une action et non une ressource. Le rapport
#: affiche la ressource déduite pour chaque opération, de sorte qu'un oubli se
#: voit et se corrige par un override plutôt que par une règle implicite.
_ACTION_SEGMENTS: frozenset[str] = frozenset(
    {
        "action",
        "availability",
        "compatible-types",
        "export",
        "attach-volume",
        "detach-volume",
        "attach-filesystem",
        "detach-filesystem",
        "release-to-ipam",
        "check-organization-quotas",
    }
)

#: Segments qui portent une valeur et non un nom de ressource :
#: `/security_groups/default/rules` désigne les règles d'un groupe de sécurité.
_VALUE_SEGMENTS: frozenset[str] = frozenset({"default"})


class ParseError(ValueError):
    """Le document n'a pas la forme qu'un contrat Scaleway doit avoir."""


#: Les mots-clés de contrainte cherchés dans le document, traduits ou non.
#:
#: La liste est celle qu'OpenAPI définit, plus l'extension `x-one-of` que
#: Scaleway ajoute. Elle est **fermée par décision** : un mot-clé qui n'y est
#: pas n'est pas cherché, et le rapport ne prétend donc rien à son sujet.
CONTRAINTES_CHERCHEES: tuple[str, ...] = (
    "x-one-of",
    "nullable",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
    "maxItems",
    "uniqueItems",
    "readOnly",
    "writeOnly",
    "multipleOf",
)

#: Ce que le générateur sait faire d'une contrainte trouvée.
#:
#: `x-one-of` devient un `mutually_exclusive`. La nullabilité est portée par
#: l'IR et comptée, sans être traduite en effacement : un module de gestion
#: refuse le `null` explicite au lieu de l'ignorer (ADR-012), et effacer
#: demande une sémantique que le contrat ne décrit pas (#114).
CONTRAINTES_TRADUITES: frozenset[str] = frozenset({"x-one-of"})


def _compter_les_contraintes(noeud: Any, comptes: dict[str, int]) -> None:
    """Compte les mots-clés de contrainte dans tout le document.

    Le parcours est brut et volontairement : une contrainte peut vivre sur un
    paramètre, sur une propriété de schéma, sous un `items` ou dans une branche
    de `oneOf`, et un parcours qui ne regarderait que les endroits attendus
    manquerait précisément ceux auxquels personne n'a pensé.
    """
    if isinstance(noeud, dict):
        for cle, valeur in noeud.items():
            if cle in comptes:
                comptes[cle] += 1
            _compter_les_contraintes(valeur, comptes)
    elif isinstance(noeud, list):
        for valeur in noeud:
            _compter_les_contraintes(valeur, comptes)


def parse_document(spec: SpecDocument) -> ApiService:
    """Construit l'IR d'un produit à partir de son document OpenAPI."""
    document = spec.document
    if "paths" not in document:
        raise ParseError(f"{spec.path} ne déclare aucun chemin")

    schemas: dict[str, Any] = _mapping(_mapping(document).get("components")).get("schemas", {})
    warnings: list[str] = []

    contraintes = dict.fromkeys(CONTRAINTES_CHERCHEES, 0)
    _compter_les_contraintes(document, contraintes)
    for mot, compte in sorted(contraintes.items()):
        if compte and mot not in CONTRAINTES_TRADUITES:
            warnings.append(
                f"contrainte `{mot}` déclarée {compte} fois dans le contrat et "
                "non traduite en contrainte d'`argument_spec`"
            )
    enums: dict[str, ApiEnum] = {}
    operations: list[ApiOperation] = []

    chemins = _mapping(document.get("paths"))
    for path, path_item in chemins.items():
        # Un chemin dont l'entrée n'est pas un mapping ne porte aucune opération.
        # Le signaler plutôt que de le laisser planter deux lignes plus bas :
        # l'opération n'y est pas, et c'est tout ce qu'il y a à en dire.
        if not isinstance(path_item, dict):
            warnings.append(f"{path} : entrée de chemin qui n'est pas un mapping, ignorée")
            continue
        for method_name, method in _METHODS.items():
            operation = path_item.get(method_name)
            if not isinstance(operation, dict):
                if operation is not None:
                    warnings.append(
                        f"{method.value} {path} : opération qui n'est pas un mapping, ignorée"
                    )
                continue
            operations.append(
                _parse_operation(
                    spec=spec,
                    path=path,
                    method=method,
                    operation=operation,
                    partages=path_item.get("parameters"),
                    schemas=schemas,
                    enums=enums,
                    warnings=warnings,
                )
            )

    # **Les champs des ressources rendues, une fois par schéma.** Ils viennent
    # après les opérations parce qu'ils se déduisent d'elles : seuls les
    # schémas qu'une réponse désigne sont retenus.
    objects = _parse_objects(operations, schemas, enums, warnings)
    glossary = _parse_glossary(
        schemas,
        tuple(
            tuple(
                (parametre.name, parametre.description)
                for parametre in operation.parameters
                if parametre.description
            )
            for operation in operations
        ),
    )

    info = _mapping(document.get("info"))
    return ApiService(
        name=spec.product,
        version=spec.version,
        title=info.get("title"),
        description=_first_paragraph(info.get("description")),
        source=str(spec.path.name),
        operations=tuple(sorted(operations, key=lambda op: op.id)),
        enums=tuple(sorted(enums.values(), key=lambda enum: enum.name)),
        objects=objects,
        glossary=glossary,
        constraint_keywords=tuple(sorted(contraintes.items())),
        warnings=tuple(sorted(set(warnings))),
    )


def _parse_glossary(
    schemas: dict[str, Any],
    _parametres_documentes: tuple[tuple[tuple[str, str], ...], ...] = (),
) -> tuple[tuple[str, str], ...]:
    """Les champs que le contrat ne décrit qu'une seule fois, avec cette phrase.

    **Un constat, pas une décision.** Ce que la couche Ansible en fera est son
    affaire ; ici on relève seulement que le document est sans ambiguïté sur ce
    nom de champ.

    L'unicité est la condition, et elle est stricte. `name` apparaît treize fois
    dans instance.v1 avec treize phrases différentes, « Instance name. »,
    « Volume name. », « Snapshot name. » : aucune ne vaut pour les autres, et le
    glossaire n'en retient aucune. `protocol` n'apparaît qu'une fois, « Protocol
    family this rule applies to. », et il n'y a rien à trancher.
    """
    vues: dict[str, set[str]] = {}
    for schema in schemas.values():
        if not isinstance(schema, dict):
            continue
        for champ, declaration in _mapping(schema.get("properties")).items():
            if not isinstance(declaration, dict):
                continue
            phrase = _first_paragraph(declaration.get("description"))
            if phrase:
                vues.setdefault(champ, set()).add(phrase)
    # **Les paramètres décrivent aussi des champs, mais ils passent après.**
    # Ne lire que `components.schemas` laissait dehors « Reverse domain name. »,
    # que le contrat écrit sur le paramètre `reverse` d'`UpdateIp` et nulle part
    # ailleurs.
    #
    # Ils ne se mélangent pas aux schémas pour autant, et la première tentative
    # a montré pourquoi : un paramètre décrit souvent un **filtre**, « List
    # images with these exact tags », là où le champ rendu porte les tags. Versés
    # dans le même sac, ces deux phrases faisaient perdre l'unicité de douze
    # champs que les schémas décrivaient pourtant sans ambiguïté, et le compte
    # des champs muets est passé de 28 à 40.
    #
    # Ils ne servent donc que là où **aucun schéma** ne décrit le nom.
    de_parametres: dict[str, set[str]] = {}
    for parametres in _parametres_documentes:
        for champ, phrase in parametres:
            if champ not in vues:
                de_parametres.setdefault(champ, set()).add(phrase)
    for champ, phrases in de_parametres.items():
        vues[champ] = phrases
    return tuple(
        (champ, next(iter(phrases))) for champ, phrases in sorted(vues.items()) if len(phrases) == 1
    )


def _parse_objects(
    operations: list[ApiOperation],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
) -> tuple[ApiObject, ...]:
    """Les champs des ressources que les opérations rendent réellement.

    **Un seul niveau, et c'est une décision.** Le `contains` d'un `RETURN` sert
    à dire ce qu'on peut lire dans le résultat ; recopier l'arbre entier des
    schémas ferait une page que personne ne parcourt et un IR que personne ne
    relit. Un champ objet reste donc `dict`, un tableau d'objets reste `list`.

    Les enums rencontrés ici rejoignent ceux des paramètres : une valeur
    d'énumération renommée dans une réponse est une évolution de la surface, et
    le golden doit la voir passer.
    """
    voulus = sorted(
        {
            operation.response.payload_schema
            for operation in operations
            if operation.response and operation.response.payload_schema
        }
    )
    objets: list[ApiObject] = []
    for nom in voulus:
        schema = schemas.get(nom)
        if not isinstance(schema, dict):
            warnings.append(f"{nom} : schéma de réponse absent des composants du contrat")
            continue
        champs: list[ApiField] = []
        for champ, declaration in _mapping(schema.get("properties")).items():
            if not isinstance(declaration, dict):
                continue
            resolu = _resolve_type(
                schema=declaration,
                schemas=schemas,
                enums=enums,
                warnings=warnings,
                context=f"{nom}.{champ}",
            )
            champs.append(
                ApiField(
                    name=champ,
                    type=resolu.type,
                    item_type=resolu.item_type,
                    deprecated=bool(declaration.get("deprecated")),
                    description=_first_paragraph(declaration.get("description")),
                )
            )
        objets.append(ApiObject(name=nom, fields=tuple(champs)))
    return tuple(objets)


def _parametres_declares(
    operation: dict[str, Any], partages: Any, operation_id: str, warnings: list[str]
) -> list[Any]:
    """Les paramètres qui s'appliquent à l'opération, partagés compris.

    **OpenAPI autorise un `parameters` au niveau du chemin**, et §4.7.9.1 dit
    qu'il s'applique à toutes les opérations qui s'y trouvent. Le parser ne
    lisait que celui de l'opération : un contrat qui déclare `{zone}` et
    `{id}` une fois pour tout le chemin produisait une opération **sans aucun
    paramètre**, donc un module dont le chemin gardait ses accolades, et rien
    ne le signalait.

    Aucun contrat versionné ne s'en sert aujourd'hui, et
    `test_aucun_contrat_versionne_ne_declare_de_parametre_partage` le mesure :
    le défaut est latent, ce qui est la raison de le corriger maintenant plutôt
    que le jour où un contrat s'en servira.

    **L'opération gagne, le chemin comble.** C'est ce que dit la même section :
    un paramètre de l'opération remplace celui du chemin quand tous deux
    portent le même `name` et le même `in`. L'inverse écraserait une
    précision locale par une valeur générale.
    """
    propres = [p for p in (operation.get("parameters") or []) if isinstance(p, dict)]
    if not isinstance(partages, list):
        if partages is not None:
            warnings.append(
                f"{operation_id} : `parameters` du chemin qui n'est pas une liste, ignoré"
            )
        return list(operation.get("parameters") or [])

    identite = {(p.get("name"), p.get("in")) for p in propres}
    herites = [
        p for p in partages if isinstance(p, dict) and (p.get("name"), p.get("in")) not in identite
    ]
    return [*herites, *(operation.get("parameters") or [])]


def _parse_operation(
    *,
    spec: SpecDocument,
    path: str,
    method: HTTPMethod,
    operation: dict[str, Any],
    partages: Any,
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
) -> ApiOperation:
    # **L'identifiant sert de clé de tri sur toutes les opérations du produit.**
    # Un `operationId` qui n'est pas une chaîne traversait le parsing entier et
    # sortait en `TypeError: '<' not supported` au moment du `sorted`, à la
    # toute fin, sur un message qui ne nomme ni l'opération ni le fichier.
    operation_id = operation.get("operationId")
    if not isinstance(operation_id, str) or not operation_id:
        raise ParseError(
            f"{method.value} {path} : `operationId` absent ou invalide ({operation_id!r})"
        )

    scope = _scope_of(path)
    parameters: list[ApiParameter] = []
    for declared in _parametres_declares(operation, partages, operation_id, warnings):
        if not isinstance(declared, dict):
            warnings.append(f"{operation_id} : un paramètre qui n'est pas un mapping, ignoré")
            continue
        parameters.append(
            _parse_parameter(
                declared=_deref(declared, schemas),
                schemas=schemas,
                enums=enums,
                warnings=warnings,
                operation_id=operation_id,
            )
        )
    parameters.extend(
        _parse_body(
            operation=operation,
            schemas=schemas,
            enums=enums,
            warnings=warnings,
            operation_id=operation_id,
        )
    )

    response = _parse_response(operation, schemas, warnings, operation_id)
    pagination = _parse_pagination(parameters, response, schemas)

    return ApiOperation(
        id=operation_id,
        service=spec.product,
        version=spec.version,
        resource=_derive_resource(path, scope),
        http_method=method,
        path=path,
        scope=scope,
        parameters=tuple(parameters),
        response=response,
        pagination=pagination,
        summary=operation.get("summary"),
        description=_first_paragraph(operation.get("description")),
        deprecated=bool(operation.get("deprecated")),
        tags=tuple(operation.get("tags") or ()),
    )


def _parse_parameter(
    *,
    declared: dict[str, Any],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
    operation_id: str,
) -> ApiParameter:
    # Le nom sert de clé partout en aval, jusqu'à un `set` construit trois
    # fonctions plus loin dans la pagination : un nom qui n'est pas une chaîne
    # y sortait en `TypeError: unhashable type`, loin de l'endroit où il a été
    # lu. Le refus est ici.
    name = declared.get("name")
    if not isinstance(name, str) or not name:
        raise ParseError(f"{operation_id} : un paramètre déclare un `name` invalide ({name!r})")
    # **Un emplacement que l'enum ne connaît pas est un refus, pas un plantage.**
    # `ParameterLocation(...)` lève un `ValueError` nu, dont le message parle de
    # l'enum et pas du contrat. Le fuzzer l'a produit avec un `in:` portant un
    # objet ; l'amont le produirait avec un emplacement qu'OpenAPI ajoute et que
    # ce parser ne connaît pas encore, ce qui est le cas qui compte.
    brut = declared.get("in", "query")
    try:
        location = ParameterLocation(brut)
    except ValueError as erreur:
        raise ParseError(
            f"{operation_id}.{name} : emplacement de paramètre non reconnu ({brut!r}). "
            f"Attendus : {[membre.value for membre in ParameterLocation]}"
        ) from erreur
    schema = _mapping(declared.get("schema"))
    resolved = _resolve_type(
        schema=schema,
        schemas=schemas,
        enums=enums,
        warnings=warnings,
        context=f"{operation_id}.{name}",
    )
    return ApiParameter(
        name=name,
        type=resolved.type,
        required=bool(declared.get("required", False)),
        location=location,
        description=_first_paragraph(declared.get("description")),
        enum_name=resolved.enum_name,
        enum_values=resolved.enum_values,
        item_type=resolved.item_type,
        default=resolved.default,
        deprecated=bool(schema.get("deprecated") or declared.get("deprecated")),
        format=schema.get("format"),
        ref=resolved.ref,
        nullable=resolved.nullable,
        one_of_group=_groupe_dexclusion(schema) or _groupe_dexclusion(declared),
    )


def _parse_body(
    *,
    operation: dict[str, Any],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
    operation_id: str,
) -> list[ApiParameter]:
    body = operation.get("requestBody")
    if not body:
        return []
    schema = _mapping(_mapping(_mapping(body).get("content")).get("application/json")).get("schema")
    if not schema:
        warnings.append(f"{operation_id} : corps de requête sans schéma JSON")
        return []
    schema = _deref(schema, schemas)
    properties: dict[str, Any] = _mapping(schema.get("properties"))
    # `required` est une liste de noms. Un élément qui n'est pas une chaîne
    # rend l'ensemble inconstructible ; ceux qui le sont suffisent à dire ce
    # qui est obligatoire, et le reste ne désignait aucun paramètre.
    required = {nom for nom in (schema.get("required") or ()) if isinstance(nom, str)}

    parameters: list[ApiParameter] = []
    for name, property_schema in properties.items():
        # Une propriété déclarée sans valeur n'est pas un schéma : elle vaut
        # `None`, et rien n'en sortira. Le rapport le dira par l'absence du
        # paramètre plutôt que par un plantage.
        if not isinstance(property_schema, dict):
            warnings.append(f"{operation_id}.{name} : propriété sans schéma, paramètre ignoré")
            continue
        resolved = _resolve_type(
            schema=property_schema,
            schemas=schemas,
            enums=enums,
            warnings=warnings,
            context=f"{operation_id}.{name}",
        )
        parameters.append(
            ApiParameter(
                name=name,
                type=resolved.type,
                required=name in required,
                location=ParameterLocation.BODY,
                description=_first_paragraph(property_schema.get("description")),
                enum_name=resolved.enum_name,
                enum_values=resolved.enum_values,
                item_type=resolved.item_type,
                default=resolved.default,
                deprecated=bool(property_schema.get("deprecated")),
                format=property_schema.get("format"),
                ref=resolved.ref,
                nullable=resolved.nullable,
                one_of_group=_groupe_dexclusion(property_schema),
            )
        )
    return parameters


class _ResolvedType:
    """Résultat de la lecture d'un schéma de paramètre."""

    __slots__ = ("default", "enum_name", "enum_values", "item_type", "nullable", "ref", "type")

    def __init__(
        self,
        type: ApiType,
        enum_name: str | None = None,
        enum_values: tuple[str, ...] = (),
        item_type: ApiType | None = None,
        default: object | None = None,
        ref: str | None = None,
        nullable: bool = False,
    ) -> None:
        self.type = type
        self.enum_name = enum_name
        self.enum_values = enum_values
        self.item_type = item_type
        self.default = default
        self.ref = ref
        self.nullable = nullable


def _groupe_dexclusion(schema: Any) -> str | None:
    """Le groupe `x-one-of` déclaré sur un champ, s'il y en a un.

    Scaleway marque ainsi les champs dont un seul peut être fourni :
    `email_config` et `webhook_config` d'un abonné portent tous deux
    `x-one-of: config`. Sans ce marqueur, le module généré accepte les deux et
    l'API répond 400, ce qui est invisible jusqu'au premier playbook.

    Un marqueur qui n'est pas une chaîne est ignoré plutôt que recopié : la clé
    est une extension, personne ne la valide en amont, et un objet glissé là
    produirait un `mutually_exclusive` illisible par Ansible.
    """
    if not isinstance(schema, dict):
        return None
    groupe = schema.get("x-one-of")
    return groupe if isinstance(groupe, str) and groupe else None


def _resolve_type(
    *,
    schema: dict[str, Any],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
    context: str,
) -> _ResolvedType:
    """Traduit un schéma OpenAPI en type de l'IR, en enregistrant les enums."""
    if not isinstance(schema, dict) or not schema:
        warnings.append(f"{context} : paramètre sans schéma, type inconnu")
        return _ResolvedType(ApiType.UNKNOWN)

    # **`oneOf: [X, null]` est la façon dont Scaleway écrit « optionnel ».**
    # Ce n'est pas une union de formes alternatives : c'est un X, ou rien. Sur
    # le contrat du Load Balancer, toutes les occurrences ont exactement cette
    # forme, et pas une n'est une vraie union. Les traiter comme un type non
    # traité écartait un module Day-2 entier, `lb_subscriber`.
    #
    # **La branche `null` est conservée, elle ne se réduit pas à son autre
    # moitié.** Un champ effaçable et un champ absent ne sont pas la même
    # demande, et le générateur ne sait pas encore les distinguer : le fait est
    # porté pour être compté avant d'être traité.
    #
    # La mutuelle exclusion, elle, n'est **pas** portée par le `oneOf` mais par
    # le marqueur frère `x-one-of`, lu par l'appelant : c'est une propriété du
    # champ dans son schéma, pas de son type.
    branches = schema.get("oneOf")
    if isinstance(branches, list):
        utiles = [
            branche
            for branche in branches
            if isinstance(branche, dict) and branche.get("type") != "null"
        ]
        nullable = len(utiles) < len(branches)
        if len(utiles) == 1:
            resolu = _resolve_type(
                schema=utiles[0],
                schemas=schemas,
                enums=enums,
                warnings=warnings,
                context=context,
            )
            return _ResolvedType(
                resolu.type,
                enum_name=resolu.enum_name,
                enum_values=resolu.enum_values,
                item_type=resolu.item_type,
                default=resolu.default,
                ref=resolu.ref,
                nullable=nullable,
            )
        warnings.append(
            f"{context} : `oneOf` à {len(utiles)} branches non nulles, union non traduite"
        )
        return _ResolvedType(ApiType.UNKNOWN)

    ref = schema.get("$ref")
    if ref is not None and not isinstance(ref, str):
        warnings.append(f"{context} : `$ref` qui n'est pas une chaîne ({ref!r})")
        return _ResolvedType(ApiType.UNKNOWN)
    if ref:
        target_name = ref.rsplit("/", 1)[-1]
        target = _deref(schema, schemas)
        resolved = _resolve_type(
            schema=target, schemas=schemas, enums=enums, warnings=warnings, context=context
        )
        if resolved.type is ApiType.ENUM:
            enums.setdefault(
                target_name,
                ApiEnum(
                    name=target_name,
                    values=resolved.enum_values,
                    default=target.get("default"),
                    description=_first_paragraph(target.get("description")),
                ),
            )
            return _ResolvedType(
                ApiType.ENUM,
                enum_name=target_name,
                enum_values=resolved.enum_values,
                default=target.get("default"),
                ref=target_name,
                nullable=resolved.nullable,
            )
        # **La nullabilité traverse la référence.** Scaleway écrit un champ
        # effaçable de trois façons, et la troisième est un `$ref` vers un
        # enveloppeur protobuf, `google.protobuf.BoolValue: type: [boolean,
        # "null"]`. La cible le dit ; ne pas le reporter faisait sortir le même
        # `dest_port_from` effaçable dans une opération et pas dans l'autre,
        # selon la façon dont le contrat l'écrit.
        return _ResolvedType(
            resolved.type, item_type=resolved.item_type, ref=target_name, nullable=resolved.nullable
        )

    raw_type = schema.get("type")
    nullable_par_le_type = False
    if isinstance(raw_type, list):
        # OpenAPI 3.1 écrit un champ optionnel `["string", "null"]`. C'est le
        # même fait que le `oneOf: [X, null]`, écrit dans l'autre forme
        # autorisée : il se conserve pareil.
        candidates = [entry for entry in raw_type if entry != "null"]
        nullable_par_le_type = len(candidates) < len(raw_type)
        raw_type = candidates[0] if candidates else None
    if raw_type is not None and not isinstance(raw_type, str):
        # **Un `type` qui n'est ni une chaîne ni une liste de chaînes.** Le
        # code le passait directement à `in _SCALAR_TYPES`, et un objet y
        # sortait en `TypeError: unhashable type`. Le signaler est la réponse :
        # c'est un type que le contrat déclare et que le parser ne sait pas
        # lire, ce qui est exactement ce que les limites du rapport portent.
        warnings.append(f"{context} : `type` n'est ni une chaîne ni une liste ({raw_type!r})")
        return _ResolvedType(ApiType.UNKNOWN)

    if "enum" in schema:
        valeurs = schema["enum"]
        if not isinstance(valeurs, (list, tuple)):
            # Un `enum` déclaré vide vaut `None`, et il n'énumère rien. Le
            # signaler plutôt que de le parcourir : un enum sans valeur ne
            # produirait de toute façon aucun `choices`.
            warnings.append(f"{context} : `enum` qui n'est pas une liste ({valeurs!r})")
            return _ResolvedType(ApiType.UNKNOWN)
        return _ResolvedType(
            ApiType.ENUM,
            enum_values=tuple(str(value) for value in valeurs),
            default=schema.get("default"),
            nullable=nullable_par_le_type,
        )

    # `nullable_par_le_type` est reporté par **chaque** branche, pas seulement
    # par la scalaire : `type: [array, "null"]` est la forme que le contrat
    # emploie pour les tags, et la perdre ici comptait un champ effaçable de
    # moins par tableau, sans qu'aucun avertissement le dise.
    if raw_type == "object":
        if schema.get("additionalProperties"):
            return _ResolvedType(
                ApiType.MAP, default=schema.get("default"), nullable=nullable_par_le_type
            )
        return _ResolvedType(
            ApiType.OBJECT, default=schema.get("default"), nullable=nullable_par_le_type
        )

    if raw_type == "array":
        items = schema.get("items")
        if not items:
            # Mesuré sur instance.v1 : les tableaux d'un corps de requête ne
            # déclarent pas leurs éléments. Le type est inconnu, il ne se
            # devine pas.
            warnings.append(f"{context} : tableau sans `items`, type des éléments inconnu")
            return _ResolvedType(ApiType.ARRAY, item_type=None, nullable=nullable_par_le_type)
        resolved_item = _resolve_type(
            schema=_deref(items, schemas) if "$ref" in items else items,
            schemas=schemas,
            enums=enums,
            warnings=warnings,
            context=f"{context}[]",
        )
        return _ResolvedType(
            ApiType.ARRAY, item_type=resolved_item.type, nullable=nullable_par_le_type
        )

    if raw_type in _SCALAR_TYPES:
        return _ResolvedType(
            _SCALAR_TYPES[raw_type],
            default=schema.get("default"),
            nullable=nullable_par_le_type,
        )

    warnings.append(f"{context} : type OpenAPI non traité ({raw_type!r})")
    return _ResolvedType(ApiType.UNKNOWN)


def _est_une_enveloppe(schema_name: str | None) -> bool:
    """Une enveloppe est un schéma de réponse, pas une ressource.

    Scaleway nomme ses enveloppes par le suffixe `Response`, et **seulement**
    elles. Mesuré sur le contrat vendorisé : presque toutes les réponses 200
    portant un corps sont en `...Response`, et les exceptions sont des
    ressources rendues telles quelles, `File`, `PrivateNIC` et
    `ServerCompatibleTypes`. Les nommer vaut mieux que les compter : le compte
    change au premier produit ajouté, la liste dit lesquelles regarder.

    Le nom est le seul signal fiable. On pourrait croire qu'un tableau dont les
    éléments sont une référence désigne une liste, mais une ressource porte
    couramment un tableau de sous-objets : la règle rangerait alors `Server`
    parmi les enveloppes à cause de ses volumes.
    """
    if schema_name is None:
        return False
    return schema_name.rsplit(".", 1)[-1].endswith("Response")


def _parse_response(
    operation: dict[str, Any],
    schemas: dict[str, Any],
    warnings: list[str],
    operation_id: str,
) -> ApiResponse | None:
    """Décrit la réponse 200, et le champ qui porte réellement la ressource.

    **Le premier tableau du schéma ne gagne que dans une enveloppe.** Une
    réponse qui est la ressource elle-même n'a aucun champ porteur : sa charge
    utile est son corps entier. La règle « le premier tableau gagne » décrivait
    `UpdatePrivateNIC`, qui répond par `PrivateNIC`, comme rendant **une liste
    de tags**, parce que `tags` est le premier tableau du schéma de la
    ressource. L'IR est le produit de ce dépôt : un module rendu depuis cette
    description lirait `tags` en croyant lire la ressource.
    """
    responses = _mapping(operation.get("responses"))
    success = responses.get("200") or responses.get(200)
    if not success:
        return None
    # **Une clé présente et vide vaut `None`, pas `{}`.** Le défaut d'un `.get`
    # ne s'applique qu'à une clé **absente** : un `content:` sans rien dessous
    # rend `None`, et la chaîne d'appels sortait en `AttributeError` au lieu de
    # conclure que la réponse n'a pas de schéma. Trouvé par le fuzzer du parser,
    # sur une mutation qui met un champ à `null`, ce qu'un document YAML écrit
    # à la main produit sans effort.
    schema = _mapping(_mapping(_mapping(success).get("content")).get("application/json")).get(
        "schema"
    )
    if not isinstance(schema, dict) or not schema:
        return ApiResponse()

    # **Un `$ref` qui n'est pas une chaîne n'est pas une référence.** Le nom
    # extrait ici sert plus loin de **clé de dictionnaire** : une liste y sortait
    # en `TypeError: unhashable type`, à trois fonctions de distance de l'endroit
    # où la forme était supposée. Le fuzzer l'a montré ; la garde est ici, à la
    # lecture, et pas là où le symptôme apparaissait.
    reference = schema.get("$ref")
    schema_name = reference.rsplit("/", 1)[-1] or None if isinstance(reference, str) else None
    resolved = _deref(schema, schemas)
    properties: dict[str, Any] = _mapping(resolved.get("properties"))

    if not _est_une_enveloppe(schema_name):
        if schema_name is None:
            # Un schéma de réponse sans nom ne permet pas de trancher. Le
            # contrat vendorisé n'en porte aucun ; le jour où il en portera, le
            # rapport le dira plutôt que le parser ne le devine.
            warnings.append(
                f"{operation_id} : réponse 200 au schéma anonyme, "
                "enveloppe ou ressource indécidable"
            )
        # La réponse **est** la ressource : pas de champ porteur, pas de liste.
        return ApiResponse(schema=schema_name, payload_schema=schema_name)

    payload_field: str | None = None
    payload_schema: str | None = None
    is_list = False
    for name, property_schema in properties.items():
        if not isinstance(property_schema, dict):
            continue
        property_type = property_schema.get("type")
        if isinstance(property_type, list):
            property_type = next((entry for entry in property_type if entry != "null"), None)
        if property_type == "array":
            payload_field = name
            items_ref = _mapping(property_schema.get("items")).get("$ref")
            payload_schema = (
                items_ref.rsplit("/", 1)[-1] or None if isinstance(items_ref, str) else None
            )
            is_list = True
            break
        if isinstance(property_schema.get("$ref"), str) and payload_field is None:
            payload_field = name
            payload_schema = property_schema["$ref"].rsplit("/", 1)[-1]

    return ApiResponse(
        schema=schema_name,
        payload_field=payload_field,
        payload_schema=payload_schema,
        is_list=is_list,
    )


#: Les noms sous lesquels Scaleway déclare une taille de page. Deux, mesurés :
#: `per_page` sur Instance, `page_size` sur le Load Balancer. Une troisième
#: orthographe s'ajoute ici, et nulle part ailleurs.
_PAGE_SIZE_PARAMS: tuple[str, ...] = ("per_page", "page_size")


def _parse_pagination(
    parameters: list[ApiParameter],
    response: ApiResponse | None,
    schemas: dict[str, Any],
) -> Pagination | None:
    """Une opération est paginée si elle accepte `page` et une taille de page.

    **Scaleway emploie deux orthographes selon le produit**, et une règle qui
    n'en connaît qu'une est pire qu'une règle absente : l'opération n'est pas
    déclarée paginée, ses paramètres de pagination deviennent des options du
    module, et une liste rend sa première page **en silence**. C'est le défaut
    que le garde-fou de pagination existe pour empêcher, et il passait par la
    porte d'à côté.

    Mesuré : Instance pagine avec `per_page`, le Load Balancer avec
    `page_size`, et les listes de `lb.v1` étaient toutes dans ce cas. L'issue
    #27 avait nommé la construction avant qu'un contrat ne la porte ; c'est le
    second produit qui l'a rendue réelle.

    L'ordre d'essai est fixe et non alphabétique : `per_page` d'abord parce
    qu'un contrat qui déclarerait les deux est plus probablement un contrat
    Instance étendu qu'un contrat Load Balancer, et parce qu'un ordre stable
    est ce qui rend la génération déterministe.
    """
    names = {parameter.name for parameter in parameters}
    if "page" not in names:
        return None
    taille = next((nom for nom in _PAGE_SIZE_PARAMS if nom in names), None)
    if taille is None:
        return None

    total_count_field = None
    if response and response.schema:
        properties = _mapping(_mapping(schemas).get(response.schema)).get("properties", {}) or {}
        if "total_count" in properties:
            total_count_field = "total_count"
    return Pagination(per_page_param=taille, total_count_field=total_count_field)


def _scope_of(path: str) -> Scope:
    """La portée se lit dans le chemin : `/zones/{zone}/` ou `/regions/{region}/`."""
    if "/zones/{zone}/" in path:
        return Scope.ZONE
    if "/regions/{region}/" in path:
        return Scope.REGION
    return Scope.GLOBAL


def _derive_resource(path: str, scope: Scope) -> str:
    """Déduit la ressource portée par un chemin, en snake_case singulier.

    La règle tient en une phrase : la ressource est le **premier et le dernier**
    segment porteur de ressource du chemin, une fois retirés le produit, la
    version, la portée, les identifiants, les segments d'action et les segments
    de valeur.

    Prendre les deux extrémités plutôt que le seul dernier segment est ce qui
    donne le même nom à `/security_groups/{id}/rules` et à
    `/security_groups/{id}/rules/{rule_id}` : une règle qui ne regardait que le
    dernier segment nommait la même ressource `security_group_rule` dans un cas
    et `rule` dans l'autre.

    * `/servers/{server_id}/action` -> `server`
    * `/security_groups/{id}/rules` -> `security_group_rule`
    * `/servers/{server_id}/user_data/{key}` -> `server_user_data`
    """
    segments = [segment for segment in path.strip("/").split("/") if segment]
    # Retirer le préfixe produit/version, puis la portée quand elle est portée
    # par le chemin (`zones/{zone}`, `regions/{region}`).
    segments = segments[2:]
    if scope is not Scope.GLOBAL and len(segments) >= 2:
        segments = segments[2:]

    bearing = [
        segment
        for segment in segments
        if not segment.startswith("{")
        and segment not in _ACTION_SEGMENTS
        and segment not in _VALUE_SEGMENTS
    ]
    if not bearing:
        return "unknown"

    parts = [bearing[0]] if len(bearing) == 1 else [bearing[0], bearing[-1]]
    return singularize_phrase(snake_case("_".join(parts)))


def _deref(node: Any, schemas: dict[str, Any]) -> dict[Any, Any]:
    """Résout une référence locale `#/components/schemas/<nom>`.

    Accepte n'importe quel nœud et rend un mapping : un contrat peut déclarer à
    cette place une chaîne, une liste ou rien, et ce sont les appelants qui
    lisaient un mapping sans l'avoir vérifié. Le refus se prend ici, une fois,
    plutôt qu'à chacun des dix endroits qui appellent.
    """
    noeud: dict[Any, Any] = _mapping(node)
    ref = noeud.get("$ref")
    if not ref:
        return noeud
    if not isinstance(ref, str):
        raise ParseError(f"`$ref` qui n'est pas une chaîne : {ref!r}")
    name = ref.rsplit("/", 1)[-1]
    target = schemas.get(name)
    if target is None:
        raise ParseError(f"référence inconnue : {ref}")
    if not isinstance(target, dict):
        # Une référence qui pointe sur autre chose qu'un schéma. `dict(target)`
        # y sortait en `ValueError` en parlant de « dictionary update
        # sequence », un message qui ne nomme ni la référence ni le contrat.
        raise ParseError(f"référence vers un schéma qui n'est pas un mapping : {ref}")
    merged = dict(target)
    for key, value in noeud.items():
        if key != "$ref":
            merged.setdefault(key, value)
    return merged


def _mapping(noeud: Any) -> dict[Any, Any]:
    """Le nœud s'il est un mapping, un mapping vide sinon.

    En YAML, une clé déclarée sans valeur vaut `None`. `noeud.get("x", {})` ne
    protège que de la clé **absente**, jamais de la clé vide, et la différence
    ne se voit pas tant que le document est bien formé.
    """
    return noeud if isinstance(noeud, dict) else {}


def _first_paragraph(text: Any) -> str | None:
    """Garde la première phrase utile d'une description Scaleway.

    Les descriptions du portail contiennent des blocs MDX et des tableaux
    entiers destinés au site. Le générateur ne réécrit pas ces textes, il en
    prend le premier paragraphe.

    **Une description qui n'est pas une chaîne est traitée comme absente**, et
    non comme une erreur fatale. Le type était annoté `str | None` et supposé
    tel : un fuzzer du parser a produit un document où ce champ portait un
    objet, et le parser sortait en `AttributeError` au lieu de refuser
    proprement. Une description n'est pas porteuse : le rapport compte déjà les
    paramètres qui n'en ont pas, et c'est là que le trou se voit, donc faire
    tomber le parsing d'un produit entier pour elle coûterait plus que ce que
    ça protège.
    """
    if not isinstance(text, str) or not text:
        return None
    paragraph = text.strip().split("\n\n", 1)[0].strip()
    return paragraph or None
