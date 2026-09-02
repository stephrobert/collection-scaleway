"""Représentation intermédiaire canonique d'une API Scaleway.

Ce modèle est volontairement indépendant :

* de la source (OpenAPI aujourd'hui, autre chose demain) ;
* du SDK Scaleway utilisé au runtime ;
* d'Ansible.

Il conserve assez d'information pour détecter la dérive d'API (`sync-api`) :
descriptions, dépréciations, valeurs d'enum et formes de réponse sont portées
par l'IR même quand la génération ne s'en sert pas encore.

Les dataclasses sont gelées et les collections sont des tuples : une IR
immuable se compare, se hache et se sérialise sans surprise, ce qui est la
condition d'une génération déterministe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from generator.ir.enums import ApiType, HTTPMethod, ParameterLocation, Scope


@dataclass(frozen=True)
class ApiEnum:
    """Enum nommé du contrat, référencé par un ou plusieurs paramètres."""

    name: str
    values: tuple[str, ...]
    default: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "name": self.name,
                "values": list(self.values),
                "default": self.default,
                "description": self.description,
            }
        )


@dataclass(frozen=True)
class ApiParameter:
    """Paramètre d'entrée d'une opération, quelle que soit sa position."""

    name: str
    type: ApiType
    required: bool
    location: ParameterLocation
    description: str | None = None
    enum_name: str | None = None
    enum_values: tuple[str, ...] = ()
    item_type: ApiType | None = None
    default: object | None = None
    deprecated: bool = False
    format: str | None = None
    #: Nom du schéma référencé quand le paramètre porte une structure imbriquée.
    ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "name": self.name,
                "type": self.type.value,
                "required": self.required,
                "location": self.location.value,
                "description": self.description,
                "enum_name": self.enum_name,
                "enum_values": list(self.enum_values) or None,
                "item_type": self.item_type.value if self.item_type else None,
                "default": self.default,
                "deprecated": self.deprecated or None,
                "format": self.format,
                "ref": self.ref,
            }
        )


@dataclass(frozen=True)
class ApiResponse:
    """Forme de la réponse 200 d'une opération."""

    #: Nom du schéma de réponse tel que déclaré par le contrat.
    schema: str | None = None
    #: Champ portant la ressource utile (`server`, `servers`, ...).
    payload_field: str | None = None
    #: Nom du schéma de la ressource portée par `payload_field`.
    payload_schema: str | None = None
    #: Vrai quand `payload_field` porte une liste.
    is_list: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "schema": self.schema,
                "payload_field": self.payload_field,
                "payload_schema": self.payload_schema,
                "is_list": self.is_list or None,
            }
        )


@dataclass(frozen=True)
class Pagination:
    """Description de la pagination d'une opération de liste."""

    page_param: str = "page"
    per_page_param: str = "per_page"
    #: Champ de la réponse portant le nombre total d'éléments, s'il est déclaré.
    total_count_field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "page_param": self.page_param,
                "per_page_param": self.per_page_param,
                "total_count_field": self.total_count_field,
            }
        )


@dataclass(frozen=True)
class ApiOperation:
    """Une opération du contrat, dans le vocabulaire de l'API et non d'Ansible."""

    #: Identifiant du contrat, ex. `ServerAction`.
    id: str
    service: str
    version: str
    #: Ressource déduite du chemin, en snake_case singulier, ex. `server`.
    resource: str
    http_method: HTTPMethod
    path: str
    scope: Scope
    parameters: tuple[ApiParameter, ...] = ()
    response: ApiResponse | None = None
    pagination: Pagination | None = None
    summary: str | None = None
    description: str | None = None
    deprecated: bool = False
    tags: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        """Clé stable d'une opération, utilisée par les overrides et le rapport.

        Format : `<service>.<version>.<Resource>.<OperationId>`, ex.
        `instance.v1.Server.ServerAction`.
        """
        resource = "".join(part.capitalize() for part in self.resource.split("_"))
        return f"{self.service}.{self.version}.{resource}.{self.id}"

    def parameter(self, name: str) -> ApiParameter | None:
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter
        return None

    @property
    def scope_parameter(self) -> str | None:
        """Nom du paramètre portant la zone ou la région, s'il y en a un."""
        if self.scope is Scope.GLOBAL:
            return None
        return self.scope.value

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "key": self.key,
                "id": self.id,
                "service": self.service,
                "version": self.version,
                "resource": self.resource,
                "http_method": self.http_method.value,
                "path": self.path,
                "scope": self.scope.value,
                "summary": self.summary,
                "description": self.description,
                "deprecated": self.deprecated or None,
                "tags": list(self.tags) or None,
                "parameters": [p.to_dict() for p in self.parameters] or None,
                "response": self.response.to_dict() if self.response else None,
                "pagination": self.pagination.to_dict() if self.pagination else None,
            }
        )


@dataclass(frozen=True)
class ApiService:
    """Un produit Scaleway dans une version donnée, ex. `instance` v1."""

    name: str
    version: str
    title: str | None = None
    description: str | None = None
    source: str | None = None
    operations: tuple[ApiOperation, ...] = ()
    enums: tuple[ApiEnum, ...] = ()
    #: Anomalies rencontrées au parsing, remontées telles quelles dans le rapport.
    warnings: tuple[str, ...] = field(default=(), compare=False)

    @property
    def slug(self) -> str:
        return f"{self.name}.{self.version}"

    def operation(self, operation_id: str) -> ApiOperation | None:
        for operation in self.operations:
            if operation.id == operation_id:
                return operation
        return None

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "service": self.name,
                "version": self.version,
                "title": self.title,
                "description": self.description,
                "source": self.source,
                "enums": [e.to_dict() for e in self.enums] or None,
                "operations": [o.to_dict() for o in self.operations] or None,
                "warnings": list(self.warnings) or None,
            }
        )

    def to_json(self) -> str:
        """Sérialisation déterministe, utilisée par les golden tests."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def _compact(data: dict[str, Any]) -> dict[str, Any]:
    """Retire les clés nulles pour que l'IR sérialisée reste lisible en diff."""
    return {key: value for key, value in data.items() if value is not None}
