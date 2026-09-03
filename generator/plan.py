"""Assemblage de la chaîne : contrat -> IR -> classification -> overrides.

Le plan est ce que le rapport affiche et ce que le générateur exécutera à
l'étape suivante. Il ne produit aucun fichier : il décide, et il rend visible
ce qu'il a décidé.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from generator.ansible.mapping import module_name
from generator.classifier.rules import Classification, classify
from generator.ir.enums import DAY2_KINDS, GenerationMode, OperationKind
from generator.ir.models import ApiOperation, ApiService
from generator.overrides.loader import DEFAULT_OVERRIDES_ROOT, OverrideSet, load_overrides
from generator.parser.openapi import parse_document
from generator.source.base import DEFAULT_SPEC_ROOT, VendoredSpecSource


@dataclass(frozen=True)
class OperationPlan:
    """Ce que le générateur fera d'une opération, et pourquoi."""

    operation: ApiOperation
    classification: Classification
    resource: str
    module: str | None

    @property
    def kind(self) -> OperationKind:
        return self.classification.kind

    @property
    def mode(self) -> GenerationMode:
        return self.classification.mode

    @property
    def is_day2(self) -> bool:
        return self.kind in DAY2_KINDS


@dataclass(frozen=True)
class ProductPlan:
    """Plan complet d'un produit, prêt à être rendu en rapport."""

    service: ApiService
    operations: tuple[OperationPlan, ...]
    overrides: OverrideSet
    orphan_overrides: tuple[str, ...]

    @property
    def day2(self) -> tuple[OperationPlan, ...]:
        return tuple(plan for plan in self.operations if plan.is_day2)

    def count_by_kind(self) -> dict[OperationKind, int]:
        """Compte les opérations par classification, toutes classes présentes."""
        counts = {kind: 0 for kind in OperationKind}
        for plan in self.operations:
            counts[plan.kind] += 1
        return counts

    def count_by_mode(self) -> dict[GenerationMode, int]:
        """Compte les opérations Day-2 par mode de génération."""
        counts = {mode: 0 for mode in GenerationMode}
        for plan in self.day2:
            counts[plan.mode] += 1
        return counts

    def coverage(self) -> float | None:
        """Part des opérations Day-2 **classées** pour la génération automatique.

        Ce n'est pas la part des opérations qu'un module porte aujourd'hui, et
        la nuance a été publiée à l'envers pendant un temps : le mot
        « générables » laissait entendre qu'un module existait, alors que ce
        ratio ne regarde que la classification. Pour ce qu'un module porte
        réellement, voir `built_coverage`, qui rend 25/42 là où celui-ci rend
        41/42.

        `None` quand il n'y a aucune opération Day-2 : un ratio sans
        dénominateur n'est pas zéro, il est indéfini, et le rapport doit le
        dire plutôt qu'afficher `0.0 %`.
        """
        day2 = self.day2
        if not day2:
            return None
        automated = sum(
            1 for plan in day2 if plan.mode in (GenerationMode.AUTO, GenerationMode.OVERRIDE)
        )
        return automated / len(day2)

    def built_coverage(self, written: Sequence[str]) -> float | None:
        """Part des opérations Day-2 qu'un module réellement écrit porte.

        `coverage` dit ce que la classification autorise ; celui-ci dit ce que
        la génération produit. L'écart n'est pas du bruit : sur Instance, 41
        opérations sont classées pour la génération automatique et 25 sont
        portées par un module. Les 16 autres appartiennent à des modules que le
        renderer ne sait pas encore produire, ou que le modèle refuse de
        construire, et chacun de ces écarts est déjà publié avec sa raison dans
        le compte rendu de génération.

        `written` vient de l'appelant plutôt que d'un appel à `build_module_specs`.
        Le plan sait **nommer** un module, il ne sait pas le construire : c'est
        le modèle Ansible qui décide qu'un module est irréalisable, et lui seul.
        Recevoir la liste garde cette frontière et permet de mesurer la
        couverture d'une génération partielle, celle que `--only` produit.

        `None` sur une population Day-2 vide, pour la même raison que
        `coverage` : un ratio sans dénominateur est indéfini.
        """
        day2 = self.day2
        if not day2:
            return None
        day2_ids = {plan.operation.id for plan in day2}
        modules = self.modules()
        portees = {
            item.operation.id
            for name in written
            for item in modules.get(name, ())
            if item.operation.id in day2_ids
        }
        return len(portees) / len(day2)

    @property
    def unknown(self) -> tuple[OperationPlan, ...]:
        return tuple(plan for plan in self.operations if plan.kind is OperationKind.UNKNOWN)

    def modules(self) -> dict[str, tuple[OperationPlan, ...]]:
        """Regroupe les opérations par module cible, dans l'ordre de leur nom."""
        grouped: dict[str, list[OperationPlan]] = {}
        for plan in self.operations:
            if plan.module is None:
                continue
            grouped.setdefault(plan.module, []).append(plan)
        return {name: tuple(plans) for name, plans in sorted(grouped.items())}


def build_plan(
    product: str,
    version: str,
    *,
    spec_root: Path = DEFAULT_SPEC_ROOT,
    overrides_root: Path = DEFAULT_OVERRIDES_ROOT,
) -> ProductPlan:
    """Construit le plan d'un produit à partir de son contrat versionné."""
    service = parse_document(VendoredSpecSource(root=spec_root).load(product, version))
    overrides = load_overrides(product, root=overrides_root)
    return plan_service(service, overrides)


def plan_service(service: ApiService, overrides: OverrideSet) -> ProductPlan:
    """Applique classification et overrides à un service déjà parsé."""
    plans: list[OperationPlan] = []
    for operation in service.operations:
        classification = classify(operation)
        resource = operation.resource
        module: str | None = None

        override = overrides.get(operation.key)
        if override is not None:
            if override.resource:
                resource = override.resource
            if override.kind is not None:
                classification = Classification(
                    key=operation.key,
                    kind=override.kind,
                    mode=override.mode or GenerationMode.OVERRIDE,
                    reason=override.reason or "override sans raison",
                )

        module = module_name(service.name, resource, classification.kind)
        if override is not None and override.module:
            module = override.module
        if override is not None and override.expose is False:
            module = None

        plans.append(
            OperationPlan(
                operation=operation,
                classification=classification,
                resource=resource,
                module=module,
            )
        )

    return ProductPlan(
        service=service,
        operations=tuple(plans),
        overrides=overrides,
        orphan_overrides=overrides.orphans(service),
    )
