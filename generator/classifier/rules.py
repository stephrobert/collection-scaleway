"""Classification d'une opération d'API en intention Ansible.

Le classifieur répond à une seule question : *qu'est-ce que cette opération est
pour un utilisateur Ansible ?* Il ne décide ni du nom du module, ni de son
contenu.

Deux principes gouvernent ce fichier :

* **aucune opération ne disparaît.** Ce que les règles ne savent pas trancher
  est classé `UNKNOWN`, apparaît dans le rapport, et fait échouer la CI tant
  que personne ne l'a tranché par un override ;
* **les règles sont mécaniques et peu nombreuses.** Une règle qui aurait besoin
  de connaître une opération en particulier n'est pas une règle : c'est un
  override, et il se déclare dans `generator/overrides/`.
"""

from __future__ import annotations

from dataclasses import dataclass

from generator.ir.enums import GenerationMode, HTTPMethod, OperationKind
from generator.ir.models import ApiOperation
from generator.parser.naming import split_words

#: Verbes de lecture. Scaleway préfixe systématiquement ses `operationId`.
_READ_VERBS: frozenset[str] = frozenset({"get", "list", "describe"})

#: Verbes de création et de suppression : la responsabilité de Terraform.
_CREATE_VERBS: frozenset[str] = frozenset({"create"})
_DELETE_VERBS: frozenset[str] = frozenset({"delete", "destroy"})

#: Verbes d'écriture d'un état durable.
_UPDATE_VERBS: frozenset[str] = frozenset({"update", "set", "patch"})


@dataclass(frozen=True)
class Classification:
    """Décision de classification d'une opération, avec sa justification."""

    key: str
    kind: OperationKind
    mode: GenerationMode
    #: Règle ou override qui a produit la décision, affiché dans le rapport.
    reason: str

    @property
    def is_day2(self) -> bool:
        from generator.ir.enums import DAY2_KINDS

        return self.kind in DAY2_KINDS


def verb_of(operation: ApiOperation) -> str:
    """Premier mot de l'`operationId`, en minuscules : `ListServers` -> `list`."""
    words = split_words(operation.id)
    return words[0] if words else ""


def classify(operation: ApiOperation) -> Classification:
    """Classe une opération à partir de son verbe et de sa méthode HTTP."""
    verb = verb_of(operation)
    method = operation.http_method

    if verb in _READ_VERBS and method is HTTPMethod.GET:
        return _decision(operation, OperationKind.INFO, "verbe de lecture sur GET")

    if verb in _CREATE_VERBS and method is HTTPMethod.POST:
        return _decision(
            operation, OperationKind.LIFECYCLE, "création de ressource, périmètre Terraform"
        )

    if verb in _DELETE_VERBS and method is HTTPMethod.DELETE:
        return _decision(
            operation, OperationKind.LIFECYCLE, "suppression de ressource, périmètre Terraform"
        )

    if verb in _UPDATE_VERBS and method in (HTTPMethod.PATCH, HTTPMethod.PUT):
        return _decision(operation, OperationKind.MANAGE, "écriture d'un état durable")

    if method is HTTPMethod.POST:
        return _decision(
            operation, OperationKind.ACTION, "POST hors création : opération ponctuelle"
        )

    if method is HTTPMethod.GET:
        return _decision(operation, OperationKind.INFO, "GET sans verbe de lecture reconnu")

    return _decision(
        operation,
        OperationKind.UNKNOWN,
        f"aucune règle pour {method.value} avec le verbe {verb!r}",
    )


def _decision(operation: ApiOperation, kind: OperationKind, reason: str) -> Classification:
    return Classification(key=operation.key, kind=kind, mode=GenerationMode.AUTO, reason=reason)
