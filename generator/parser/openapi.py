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


def parse_document(spec: SpecDocument) -> ApiService:
    """Construit l'IR d'un produit à partir de son document OpenAPI."""
    document = spec.document
    if "paths" not in document:
        raise ParseError(f"{spec.path} ne déclare aucun chemin")

    schemas: dict[str, Any] = document.get("components", {}).get("schemas", {})
    warnings: list[str] = []
    enums: dict[str, ApiEnum] = {}
    operations: list[ApiOperation] = []

    for path, path_item in document["paths"].items():
        for method_name, method in _METHODS.items():
            operation = path_item.get(method_name)
            if operation is None:
                continue
            operations.append(
                _parse_operation(
                    spec=spec,
                    path=path,
                    method=method,
                    operation=operation,
                    schemas=schemas,
                    enums=enums,
                    warnings=warnings,
                )
            )

    info = document.get("info", {})
    return ApiService(
        name=spec.product,
        version=spec.version,
        title=info.get("title"),
        description=_first_paragraph(info.get("description")),
        source=str(spec.path.name),
        operations=tuple(sorted(operations, key=lambda op: op.id)),
        enums=tuple(sorted(enums.values(), key=lambda enum: enum.name)),
        warnings=tuple(sorted(set(warnings))),
    )


def _parse_operation(
    *,
    spec: SpecDocument,
    path: str,
    method: HTTPMethod,
    operation: dict[str, Any],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
) -> ApiOperation:
    operation_id = operation.get("operationId")
    if not operation_id:
        raise ParseError(f"{method.value} {path} n'a pas d'operationId")

    scope = _scope_of(path)
    parameters: list[ApiParameter] = []
    for declared in operation.get("parameters", []):
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

    response = _parse_response(operation, schemas)
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
    name = declared["name"]
    location = ParameterLocation(declared.get("in", "query"))
    schema = declared.get("schema", {})
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
    schema = body.get("content", {}).get("application/json", {}).get("schema")
    if not schema:
        warnings.append(f"{operation_id} : corps de requête sans schéma JSON")
        return []
    schema = _deref(schema, schemas)
    properties: dict[str, Any] = schema.get("properties", {})
    required = set(schema.get("required", ()))

    parameters: list[ApiParameter] = []
    for name, property_schema in properties.items():
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
            )
        )
    return parameters


class _ResolvedType:
    """Résultat de la lecture d'un schéma de paramètre."""

    __slots__ = ("default", "enum_name", "enum_values", "item_type", "ref", "type")

    def __init__(
        self,
        type: ApiType,
        enum_name: str | None = None,
        enum_values: tuple[str, ...] = (),
        item_type: ApiType | None = None,
        default: object | None = None,
        ref: str | None = None,
    ) -> None:
        self.type = type
        self.enum_name = enum_name
        self.enum_values = enum_values
        self.item_type = item_type
        self.default = default
        self.ref = ref


def _resolve_type(
    *,
    schema: dict[str, Any],
    schemas: dict[str, Any],
    enums: dict[str, ApiEnum],
    warnings: list[str],
    context: str,
) -> _ResolvedType:
    """Traduit un schéma OpenAPI en type de l'IR, en enregistrant les enums."""
    if not schema:
        warnings.append(f"{context} : paramètre sans schéma, type inconnu")
        return _ResolvedType(ApiType.UNKNOWN)

    ref = schema.get("$ref")
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
            )
        return _ResolvedType(resolved.type, item_type=resolved.item_type, ref=target_name)

    raw_type = schema.get("type")
    if isinstance(raw_type, list):
        # OpenAPI 3.1 écrit un champ optionnel `["string", "null"]`.
        candidates = [entry for entry in raw_type if entry != "null"]
        raw_type = candidates[0] if candidates else None

    if "enum" in schema:
        return _ResolvedType(
            ApiType.ENUM,
            enum_values=tuple(str(value) for value in schema["enum"]),
            default=schema.get("default"),
        )

    if raw_type == "object":
        if schema.get("additionalProperties"):
            return _ResolvedType(ApiType.MAP, default=schema.get("default"))
        return _ResolvedType(ApiType.OBJECT, default=schema.get("default"))

    if raw_type == "array":
        items = schema.get("items")
        if not items:
            # Mesuré sur instance.v1 : les tableaux d'un corps de requête ne
            # déclarent pas leurs éléments. Le type est inconnu, il ne se
            # devine pas.
            warnings.append(f"{context} : tableau sans `items`, type des éléments inconnu")
            return _ResolvedType(ApiType.ARRAY, item_type=None)
        resolved_item = _resolve_type(
            schema=_deref(items, schemas) if "$ref" in items else items,
            schemas=schemas,
            enums=enums,
            warnings=warnings,
            context=f"{context}[]",
        )
        return _ResolvedType(ApiType.ARRAY, item_type=resolved_item.type)

    if raw_type in _SCALAR_TYPES:
        return _ResolvedType(_SCALAR_TYPES[raw_type], default=schema.get("default"))

    warnings.append(f"{context} : type OpenAPI non traité ({raw_type!r})")
    return _ResolvedType(ApiType.UNKNOWN)


def _parse_response(operation: dict[str, Any], schemas: dict[str, Any]) -> ApiResponse | None:
    """Décrit la réponse 200, et le champ qui porte réellement la ressource."""
    responses = operation.get("responses", {})
    success = responses.get("200") or responses.get(200)
    if not success:
        return None
    schema = success.get("content", {}).get("application/json", {}).get("schema")
    if not schema:
        return ApiResponse()

    schema_name = schema.get("$ref", "").rsplit("/", 1)[-1] or None
    resolved = _deref(schema, schemas)
    properties: dict[str, Any] = resolved.get("properties", {})

    payload_field: str | None = None
    payload_schema: str | None = None
    is_list = False
    for name, property_schema in properties.items():
        property_type = property_schema.get("type")
        if isinstance(property_type, list):
            property_type = next((entry for entry in property_type if entry != "null"), None)
        if property_type == "array":
            payload_field = name
            items_ref = property_schema.get("items", {}).get("$ref", "")
            payload_schema = items_ref.rsplit("/", 1)[-1] or None
            is_list = True
            break
        if "$ref" in property_schema and payload_field is None:
            payload_field = name
            payload_schema = property_schema["$ref"].rsplit("/", 1)[-1]

    return ApiResponse(
        schema=schema_name,
        payload_field=payload_field,
        payload_schema=payload_schema,
        is_list=is_list,
    )


def _parse_pagination(
    parameters: list[ApiParameter],
    response: ApiResponse | None,
    schemas: dict[str, Any],
) -> Pagination | None:
    """Une opération est paginée si elle accepte `page` et `per_page`."""
    names = {parameter.name for parameter in parameters}
    if not {"page", "per_page"} <= names:
        return None

    total_count_field = None
    if response and response.schema:
        properties = schemas.get(response.schema, {}).get("properties", {})
        if "total_count" in properties:
            total_count_field = "total_count"
    return Pagination(total_count_field=total_count_field)


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


def _deref(node: dict[str, Any], schemas: dict[str, Any]) -> dict[str, Any]:
    """Résout une référence locale `#/components/schemas/<nom>`."""
    ref = node.get("$ref")
    if not ref:
        return node
    name = ref.rsplit("/", 1)[-1]
    target = schemas.get(name)
    if target is None:
        raise ParseError(f"référence inconnue : {ref}")
    merged = dict(target)
    for key, value in node.items():
        if key != "$ref":
            merged.setdefault(key, value)
    return merged


def _first_paragraph(text: str | None) -> str | None:
    """Garde la première phrase utile d'une description Scaleway.

    Les descriptions du portail contiennent des blocs MDX et des tableaux
    entiers destinés au site. Le générateur ne réécrit pas ces textes, il en
    prend le premier paragraphe.
    """
    if not text:
        return None
    paragraph = text.strip().split("\n\n", 1)[0].strip()
    return paragraph or None
