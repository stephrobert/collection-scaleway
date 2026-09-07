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

from generator.ansible.comparison import (
    PAR_DECISION_HUMAINE,
    ComparisonStrategy,
    depuis_le_nom,
)
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
        "description",
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
_PARAMETER_FIELDS: frozenset[str] = frozenset(
    {
        "choices",
        "required",
        "expose",
        "csv",
        "reason",
        "description",
        "example",
        "comparison",
    }
)

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
    #: Vrai expose un paramètre `string` du contrat comme une **liste**, jointe
    #: par des virgules à l'envoi.
    #:
    #: Ce n'est pas le générateur qui devine : c'est la description du contrat
    #: qui le dit, et l'override ne fait que la lire. Le cas mesuré est `tags`
    #: de `ListServers`, dont la description est « use commas to separate
    #: them ». Sans lui, `tags: [a, b]` en YAML n'échoue pas : Ansible produit
    #: la chaîne `"['a', 'b']"`, l'API ne trouve rien, et le playbook lit zéro
    #: machine sur un parc qui en porte cinq.
    csv: bool | None = None
    #: Description à publier **quand le contrat n'en porte aucune**, et
    #: seulement là. Le contrat gagne toujours : un override qui recouvrirait
    #: une phrase de Scaleway ferait diverger la page de l'API sans que rien ne
    #: le dise. Devenu inutile, il est signalé comme orphelin.
    description: str | None = None
    #: Valeur que l'exemple publiera, quand ni le contrat ni une convention de
    #: nom ne peuvent la donner. Le cas mesuré est `MigrateLb.type` : le contrat
    #: renvoie à un point d'API pour connaître les valeurs, il n'en déclare
    #: aucune, et un exemple qui en inventerait une serait copiable et faux.
    example: Any = None
    #: Comment ce champ se compare à ce que l'API rend, quand le type ne le dit
    #: pas.
    #:
    #: Le contrat ne déclare ni `uniqueItems` ni le moindre mot sur l'ordre :
    #: mesuré, aucun tableau des deux documents n'en porte. Poser `set` sur un
    #: champ est donc une **décision**, prise parce que quelqu'un a observé
    #: l'API réordonner, et elle porte sa raison comme les autres.
    comparison: ComparisonStrategy | None = None
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
    #: Description à publier quand l'opération n'en porte ni description ni
    #: résumé. `GetDashboard` est ce cas : le module sortait avec un
    #: `description: []`, qu'`ansible-test sanity` accepte sans rien dire.
    description: str | None = None
    parameters: dict[str, ParameterOverride] = field(default_factory=dict)
    wait: WaitOverride | None = None
    extra: dict[str, Any] = field(default_factory=dict)


#: Champs qu'un override de champ rendu peut porter.
_RETURN_FIELDS: frozenset[str] = frozenset({"description", "reason"})


@dataclass(frozen=True)
class ReturnOverride:
    """Ce qu'on publie d'un champ rendu que le contrat ne décrit nulle part.

    Le dernier recours, après la description du champ, ce que le contrat en dit
    ailleurs quand il ne le dit qu'une fois, et la reformulation du nom. Ce qui
    s'écrit ici est une décision : la `reason` dit d'où elle vient, et le texte
    sortira sur Galaxy sous le nom de la collection.
    """

    schema: str
    field: str
    description: str
    reason: str


@dataclass(frozen=True)
class OverrideSet:
    """Ensemble des overrides d'un produit."""

    source: Path | None
    operations: dict[str, OperationOverride] = field(default_factory=dict)
    #: Champs rendus, par nom de schéma puis nom de champ.
    returns: dict[str, dict[str, ReturnOverride]] = field(default_factory=dict)

    def get(self, key: str) -> OperationOverride | None:
        return self.operations.get(key)

    def orphans(self, service: ApiService) -> tuple[str, ...]:
        """Overrides qui ne portent plus sur rien, par clé ou par effet.

        Deux façons pour un override de devenir inerte, et les deux disent la
        même chose : quelque chose a bougé en amont, et le fichier ne le sait
        pas encore.

        * **la clé ne désigne aucune opération.** L'opération a disparu, ou la
          ressource déduite a changé et la clé avec elle ;
        * **la description ne comble plus rien.** Scaleway a documenté le champ,
          donc c'est sa phrase qui sort, et celle qu'on avait écrite pour
          combler le trou n'est plus lue par personne. La laisser reviendrait à
          maintenir un texte mort qu'une relecture croirait publié.

        Les deux sortent par le même canal, donc `report --strict` sort en 2
        dans les deux cas. C'est ce qui rend la dérive visible, et ça ne se
        désarme pas pour faire passer la CI.
        """
        par_cle = {operation.key: operation for operation in service.operations}
        inertes: list[str] = []

        for cle, override in self.operations.items():
            operation = par_cle.get(cle)
            if operation is None:
                inertes.append(cle)
                continue
            if override.description and (operation.description or operation.summary):
                inertes.append(
                    f"{cle} : description d'override devenue inutile, le contrat en porte une"
                )
            documentes = {
                parameter.name for parameter in operation.parameters if parameter.description
            }
            for nom, restriction in override.parameters.items():
                if restriction.description and nom in documentes:
                    inertes.append(
                        f"{cle}.parameters.{nom} : description d'override devenue "
                        "inutile, le contrat en porte une"
                    )
        # **Un champ rendu que le contrat décrit désormais lui-même.** La
        # description écrite ici ne sort plus, et personne ne la relit : elle
        # devient un texte mort qu'une relecture croirait publié.
        par_schema = {objet.name: objet for objet in service.objects}
        for schema, champs in self.returns.items():
            objet = par_schema.get(schema)
            if objet is None:
                inertes.append(f"returns.{schema} : aucune ressource de ce nom n'est rendue")
                continue
            decrits = {c.name for c in objet.fields if c.description}
            connus = {c.name for c in objet.fields}
            for champ in champs:
                if champ not in connus:
                    inertes.append(f"returns.{schema}.{champ} : la ressource ne porte pas ce champ")
                elif champ in decrits:
                    inertes.append(
                        f"returns.{schema}.{champ} : description d'override devenue "
                        "inutile, le contrat en porte une"
                    )
        return tuple(sorted(inertes))


class _SansDoublon(yaml.SafeLoader):
    """Un chargeur YAML qui refuse une clé déclarée deux fois.

    **YAML garde la dernière occurrence, sans un mot.** Un second bloc écrit
    sous une clé déjà présente n'ajoute pas ses champs : il remplace tout le
    premier. Le cas mesuré a effacé un `resource: load_balancer`, et le module
    publié a changé de nom sans qu'aucun contrôle ne rougisse.

    Le contrôle d'orphelins ne pouvait pas l'attraper : la clé désigne bien une
    opération, c'est la décision qui a disparu. Elle ne se voit qu'ici.
    """

    def construct_mapping(self, node: Any, deep: bool = False) -> dict[Any, Any]:
        vues: set[Any] = set()
        for cle_node, _ in node.value:
            cle = self.construct_object(cle_node, deep=deep)
            if cle in vues:
                raise OverrideError(
                    f"clé déclarée deux fois : {cle!r} (ligne "
                    f"{cle_node.start_mark.line + 1}). YAML garde la dernière et "
                    "efface la première en silence : réunir les deux blocs."
                )
            vues.add(cle)
        return super().construct_mapping(node, deep)


def load_overrides(product: str, root: Path = DEFAULT_OVERRIDES_ROOT) -> OverrideSet:
    """Charge `<root>/<product>.yml`, ou un ensemble vide s'il n'existe pas."""
    path = root / f"{product}.yml"
    if not path.is_file():
        return OverrideSet(source=None)

    with path.open(encoding="utf-8") as handle:
        document = yaml.load(handle, _SansDoublon) or {}
    if not isinstance(document, dict):
        raise OverrideError(f"{path} : le document doit être un mapping")

    unknown_sections = set(document) - {"operations", "returns"}
    if unknown_sections:
        raise OverrideError(f"{path} : sections inconnues {sorted(unknown_sections)}")

    operations: dict[str, OperationOverride] = {}
    for key, raw in (document.get("operations") or {}).items():
        operations[key] = _parse_override(key, raw, path)
    return OverrideSet(
        source=path,
        operations=operations,
        returns=_parse_returns(document.get("returns"), path),
    )


def _parse_returns(raw: Any, path: Path) -> dict[str, dict[str, ReturnOverride]]:
    """Lit et valide les descriptions posées sur des champs rendus."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise OverrideError(f"{path} : `returns` doit être un mapping de schémas")

    par_schema: dict[str, dict[str, ReturnOverride]] = {}
    for schema, champs in raw.items():
        if not isinstance(champs, dict):
            raise OverrideError(f"{path} : returns.{schema} doit être un mapping de champs")
        for champ, declaration in champs.items():
            if not isinstance(declaration, dict):
                raise OverrideError(f"{path} : returns.{schema}.{champ} doit être un mapping")
            inconnus = set(declaration) - _RETURN_FIELDS
            if inconnus:
                raise OverrideError(
                    f"{path} : returns.{schema}.{champ} porte des champs inconnus "
                    f"{sorted(inconnus)}. Champs acceptés : {sorted(_RETURN_FIELDS)}"
                )
            if not declaration.get("description"):
                raise OverrideError(f"{path} : returns.{schema}.{champ} n'écrit aucune description")
            if not declaration.get("reason"):
                raise OverrideError(
                    f"{path} : returns.{schema}.{champ} publie une description sans `reason`. "
                    "Elle sortira sur Galaxy sous le nom de la collection : la raison "
                    "doit dire d'où elle vient."
                )
            par_schema.setdefault(schema, {})[champ] = ReturnOverride(
                schema=schema,
                field=champ,
                description=str(declaration["description"]).strip(),
                reason=str(declaration["reason"]),
            )
    return par_schema


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

    if raw.get("description") is not None and not raw.get("reason"):
        raise OverrideError(
            f"{path} : {key} publie une description sans `reason`. Elle sortira sur "
            "Galaxy sous le nom de la collection : la raison doit dire d'où elle vient."
        )

    return OperationOverride(
        key=key,
        kind=kind,
        mode=mode,
        module=raw.get("module"),
        resource=raw.get("resource"),
        reason=raw.get("reason"),
        expose=raw.get("expose"),
        description=raw.get("description"),
        parameters=_parse_parameters(key, raw.get("parameters"), path),
        wait=_parse_wait(key, raw.get("wait"), path),
        extra={
            name: value
            for name, value in raw.items()
            if name
            not in {
                "generation",
                "module",
                "resource",
                "reason",
                "expose",
                "description",
                "parameters",
                "wait",
            }
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

        comparison = declaration.get("comparison")
        if comparison is not None:
            if not isinstance(comparison, str):
                raise OverrideError(
                    f"{path} : {key}.parameters.{nom}.comparison doit être une chaîne"
                )
            try:
                comparison = depuis_le_nom(comparison)
            except ValueError as erreur:
                raise OverrideError(f"{path} : {key}.parameters.{nom} : {erreur}") from None
            if comparison not in PAR_DECISION_HUMAINE:
                connues = ", ".join(sorted(strategie.value for strategie in PAR_DECISION_HUMAINE))
                raise OverrideError(
                    f"{path} : {key}.parameters.{nom}.comparison vaut "
                    f"`{comparison.value}`, que le type du paramètre décide déjà. "
                    f"Un override ne pose que ce qu'aucun type ne peut décider : {connues}."
                )

        arbitrages = ("choices", "required", "expose", "csv", "comparison")
        decide = any(declaration.get(champ) is not None for champ in arbitrages)
        if decide and not declaration.get("reason"):
            raise OverrideError(
                f"{path} : {key}.parameters.{nom} décide quelque chose sans `reason`. "
                "Restreindre, exiger ou masquer un paramètre du contrat est un "
                "arbitrage, pas une correction."
            )

        # **Écrire ce que le contrat ne dit pas est une décision, pas une
        # correction.** La phrase sera publiée sur Galaxy sous le nom de la
        # collection, et un lecteur n'a aucun moyen de la distinguer de celles
        # de Scaleway. La `reason` dit d'où elle vient.
        documente = any(declaration.get(champ) is not None for champ in ("description", "example"))
        if documente and not declaration.get("reason"):
            raise OverrideError(
                f"{path} : {key}.parameters.{nom} publie une description ou une valeur "
                "d'exemple sans `reason`. Ce texte sortira sur Galaxy sous le nom de "
                "la collection : la raison doit dire d'où il vient."
            )

        parametres[nom] = ParameterOverride(
            name=nom,
            choices=tuple(str(valeur) for valeur in choices or ()),
            required=declaration.get("required"),
            expose=declaration.get("expose"),
            csv=declaration.get("csv"),
            description=declaration.get("description"),
            example=declaration.get("example"),
            comparison=comparison,
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
