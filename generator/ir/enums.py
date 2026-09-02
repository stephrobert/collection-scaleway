"""Concepts fermés de la représentation intermédiaire.

Chaque enum décrit un ensemble de valeurs que la chaîne de génération peut
traiter exhaustivement. Une valeur inconnue doit être représentée
explicitement (UNKNOWN) plutôt que provoquer une perte d'information : le
rapport doit pouvoir signaler ce que le générateur n'a pas su interpréter.
"""

from __future__ import annotations

from enum import StrEnum


class Scope(StrEnum):
    """Portée géographique d'une opération, déduite du chemin HTTP."""

    GLOBAL = "global"
    REGION = "region"
    ZONE = "zone"


class HTTPMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ParameterLocation(StrEnum):
    PATH = "path"
    QUERY = "query"
    BODY = "body"
    HEADER = "header"


class ApiType(StrEnum):
    """Type d'un paramètre, indépendant d'Ansible et du SDK."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"
    ARRAY = "array"
    MAP = "map"
    OBJECT = "object"
    UNKNOWN = "unknown"


class OperationKind(StrEnum):
    """Classification Ansible d'une opération de l'API."""

    INFO = "info"
    ACTION = "action"
    MANAGE = "manage"
    WORKFLOW = "workflow"
    LIFECYCLE = "lifecycle"
    IGNORE = "ignore"
    UNKNOWN = "unknown"


class GenerationMode(StrEnum):
    """Origine de la décision de classification, pour le rapport de couverture."""

    AUTO = "auto"
    OVERRIDE = "override"
    MANUAL = "manual"


#: Classifications qui participent au dénominateur de la couverture Day-2.
DAY2_KINDS: frozenset[OperationKind] = frozenset(
    {
        OperationKind.INFO,
        OperationKind.ACTION,
        OperationKind.MANAGE,
        OperationKind.WORKFLOW,
    }
)
