"""Chargement des décisions humaines qui corrigent la classification.

La classification automatique ne sera jamais parfaite : elle lit un contrat,
pas une intention. Les overrides sont l'endroit où l'intention s'écrit, une
opération à la fois, avec sa raison.

Deux garde-fous, parce qu'un override est une affirmation :

* **les clés inconnues sont refusées.** Une faute de frappe dans un nom de
  champ produirait un override silencieusement inerte ;
* **les overrides orphelins sont signalés.** Un override qui ne désigne aucune
  opération existante décrit une API qui n'existe plus, et le rapport le dit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from generator.ir.enums import GenerationMode, OperationKind
from generator.ir.models import ApiService

DEFAULT_OVERRIDES_ROOT = Path(__file__).resolve().parent

#: Champs qu'un override peut porter. Tout autre nom est une erreur.
KNOWN_FIELDS: frozenset[str] = frozenset(
    {
        "generation",
        "module",
        "resource",
        "reason",
        "expose",
        "parameters",
        "aliases",
        "no_log",
        "wait",
        "check_mode",
        "idempotency",
        "related",
    }
)

#: Valeurs acceptées pour `generation`, et ce qu'elles décident.
#: `manual` n'est pas une classe : c'est une classe WORKFLOW dont
#: l'implémentation reste écrite à la main, donc exclue de la couverture
#: automatique.
_GENERATION_VALUES: dict[str, tuple[OperationKind, GenerationMode]] = {
    "info": (OperationKind.INFO, GenerationMode.OVERRIDE),
    "action": (OperationKind.ACTION, GenerationMode.OVERRIDE),
    "manage": (OperationKind.MANAGE, GenerationMode.OVERRIDE),
    "workflow": (OperationKind.WORKFLOW, GenerationMode.MANUAL),
    "manual": (OperationKind.WORKFLOW, GenerationMode.MANUAL),
    "lifecycle": (OperationKind.LIFECYCLE, GenerationMode.OVERRIDE),
    "ignore": (OperationKind.IGNORE, GenerationMode.OVERRIDE),
}


class OverrideError(ValueError):
    """Le fichier d'overrides contient une déclaration que le générateur refuse."""


#: Champs qu'un override de paramètre peut porter.
_PARAMETER_FIELDS: frozenset[str] = frozenset({"choices", "required", "expose", "reason"})

#: Champs qu'un bloc `wait` peut porter.
_WAIT_FIELDS: frozenset[str] = frozenset({"field", "states", "reason"})


@dataclass(frozen=True)
class ParameterOverride:
    """Restriction humaine posée sur un paramètre du contrat.

    Le seul cas aujourd'hui : réduire les `choices` d'un enum. Le contrat de
    Scaleway range dans un même enum des actions d'exploitation et des
    opérations de cycle de vie ; choisir lesquelles exposer est un arbitrage,
    et un arbitrage porte une raison.
    """

    name: str
    choices: tuple[str, ...] = ()
    #: Le contrat ne déclare aucun champ de corps `required` ; quand un module
    #: n'a pas de sens sans lui, la décision se prend ici.
    required: bool | None = None
    #: Faux retire le paramètre des options du module. Il reste dans le contrat
    #: et dans le rapport : ce qui est retiré est dit, pas effacé.
    expose: bool | None = None
    reason: str | None = None


@dataclass(frozen=True)
class WaitOverride:
    """Ce qu'une action laisse derrière elle, et comment le vérifier.

    Le contrat dit ce qu'une action *fait*, jamais dans quel état elle laisse
    la ressource. Cette correspondance est une décision : la deviner ferait
    attendre un état que rien ne promet.
    """

    field: str
    states: dict[str, str]
    reason: str | None = None


@dataclass(frozen=True)
class OperationOverride:
    """Décision humaine portant sur une opération, identifiée par sa clé."""

    key: str
    kind: OperationKind | None = None
    mode: GenerationMode | None = None
    module: str | None = None
    resource: str | None = None
    reason: str | None = None
    expose: bool | None = None
    parameters: dict[str, ParameterOverride] = field(default_factory=dict)
    wait: WaitOverride | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OverrideSet:
    """Ensemble des overrides d'un produit."""

    source: Path | None
    operations: dict[str, OperationOverride] = field(default_factory=dict)

    def get(self, key: str) -> OperationOverride | None:
        return self.operations.get(key)

    def orphans(self, service: ApiService) -> tuple[str, ...]:
        """Clés d'override qui ne désignent aucune opération du contrat."""
        known = {operation.key for operation in service.operations}
        return tuple(sorted(key for key in self.operations if key not in known))


def load_overrides(product: str, root: Path = DEFAULT_OVERRIDES_ROOT) -> OverrideSet:
    """Charge `<root>/<product>.yml`, ou un ensemble vide s'il n'existe pas."""
    path = root / f"{product}.yml"
    if not path.is_file():
        return OverrideSet(source=None)

    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    if not isinstance(document, dict):
        raise OverrideError(f"{path} : le document doit être un mapping")

    unknown_sections = set(document) - {"operations"}
    if unknown_sections:
        raise OverrideError(f"{path} : sections inconnues {sorted(unknown_sections)}")

    operations: dict[str, OperationOverride] = {}
    for key, raw in (document.get("operations") or {}).items():
        operations[key] = _parse_override(key, raw, path)
    return OverrideSet(source=path, operations=operations)


def _parse_override(key: str, raw: Any, path: Path) -> OperationOverride:
    if not isinstance(raw, dict):
        raise OverrideError(f"{path} : {key} doit être un mapping")

    unknown = set(raw) - KNOWN_FIELDS
    if unknown:
        raise OverrideError(
            f"{path} : {key} porte des champs inconnus {sorted(unknown)}. "
            f"Champs acceptés : {sorted(KNOWN_FIELDS)}"
        )

    kind: OperationKind | None = None
    mode: GenerationMode | None = None
    generation = raw.get("generation")
    if generation is not None:
        if generation not in _GENERATION_VALUES:
            raise OverrideError(
                f"{path} : {key} déclare generation={generation!r}, "
                f"valeurs acceptées : {sorted(_GENERATION_VALUES)}"
            )
        kind, mode = _GENERATION_VALUES[generation]

    if generation is not None and not raw.get("reason"):
        raise OverrideError(
            f"{path} : {key} change la classification sans `reason`. "
            "Un override sans raison est indéfendable à la relecture."
        )

    return OperationOverride(
        key=key,
        kind=kind,
        mode=mode,
        module=raw.get("module"),
        resource=raw.get("resource"),
        reason=raw.get("reason"),
        expose=raw.get("expose"),
        parameters=_parse_parameters(key, raw.get("parameters"), path),
        wait=_parse_wait(key, raw.get("wait"), path),
        extra={
            name: value
            for name, value in raw.items()
            if name
            not in {"generation", "module", "resource", "reason", "expose", "parameters", "wait"}
        },
    )


def _parse_parameters(key: str, raw: Any, path: Path) -> dict[str, ParameterOverride]:
    """Lit et valide les restrictions posées sur des paramètres."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise OverrideError(f"{path} : {key}.parameters doit être un mapping")

    parametres: dict[str, ParameterOverride] = {}
    for nom, declaration in raw.items():
        if not isinstance(declaration, dict):
            raise OverrideError(f"{path} : {key}.parameters.{nom} doit être un mapping")

        inconnus = set(declaration) - _PARAMETER_FIELDS
        if inconnus:
            raise OverrideError(
                f"{path} : {key}.parameters.{nom} porte des champs inconnus "
                f"{sorted(inconnus)}. Champs acceptés : {sorted(_PARAMETER_FIELDS)}"
            )

        choices = declaration.get("choices")
        if choices is not None and not isinstance(choices, list):
            raise OverrideError(f"{path} : {key}.parameters.{nom}.choices doit être une liste")

        arbitrages = ("choices", "required", "expose")
        decide = any(declaration.get(champ) is not None for champ in arbitrages)
        if decide and not declaration.get("reason"):
            raise OverrideError(
                f"{path} : {key}.parameters.{nom} décide quelque chose sans `reason`. "
                "Restreindre, exiger ou masquer un paramètre du contrat est un "
                "arbitrage, pas une correction."
            )

        parametres[nom] = ParameterOverride(
            name=nom,
            choices=tuple(str(valeur) for valeur in choices or ()),
            required=declaration.get("required"),
            expose=declaration.get("expose"),
            reason=declaration.get("reason"),
        )
    return parametres


def _parse_wait(key: str, raw: Any, path: Path) -> WaitOverride | None:
    """Lit et valide la correspondance action -> état attendu."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise OverrideError(f"{path} : {key}.wait doit être un mapping")

    inconnus = set(raw) - _WAIT_FIELDS
    if inconnus:
        raise OverrideError(
            f"{path} : {key}.wait porte des champs inconnus {sorted(inconnus)}. "
            f"Champs acceptés : {sorted(_WAIT_FIELDS)}"
        )

    states = raw.get("states")
    if not isinstance(states, dict) or not states:
        raise OverrideError(f"{path} : {key}.wait.states doit être un mapping non vide")
    if not raw.get("reason"):
        raise OverrideError(
            f"{path} : {key}.wait déclare des états attendus sans `reason`. "
            "Le contrat ne les dit pas : c'est une décision, et elle se justifie."
        )

    return WaitOverride(
        field=str(raw.get("field") or "state"),
        states={str(action): str(etat) for action, etat in states.items()},
        reason=raw.get("reason"),
    )
