"""Rapports de couverture, lisibles par un humain et par une machine.

Le rapport est le premier livrable du projet, avant toute génération : il dit
ce que le générateur a vu, ce qu'il a décidé, et ce qu'il ne sait pas faire.

Règle qui prime sur la présentation : **aucune opération ne disparaît**. Une
opération non classée apparaît en `UNKNOWN`, et la couverture ne se calcule
jamais sur un dénominateur choisi pour flatter le résultat.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from generator.ir.enums import GenerationMode, OperationKind
from generator.plan import ProductPlan

#: Ordre d'affichage des classes, du plus exposé au moins exposé.
_KIND_ORDER: tuple[OperationKind, ...] = (
    OperationKind.INFO,
    OperationKind.ACTION,
    OperationKind.MANAGE,
    OperationKind.WORKFLOW,
    OperationKind.LIFECYCLE,
    OperationKind.IGNORE,
    OperationKind.UNKNOWN,
)


def to_json(plan: ProductPlan) -> str:
    """Rapport machine-readable, stable d'une exécution à l'autre."""
    counts = plan.count_by_kind()
    modes = plan.count_by_mode()
    coverage = plan.coverage()

    payload: dict[str, Any] = {
        "service": plan.service.name,
        "version": plan.service.version,
        "source": plan.service.source,
        "totals": {
            "operations": len(plan.operations),
            "day2_candidates": len(plan.day2),
            "by_kind": {kind.value: counts[kind] for kind in _KIND_ORDER},
            "by_mode": {mode.value: modes[mode] for mode in GenerationMode},
        },
        # `null` et non `0.0` : sans opération Day-2, le ratio n'existe pas.
        "day2_automation_coverage": round(coverage, 4) if coverage is not None else None,
        "modules": {
            name: [operation.operation.id for operation in operations]
            for name, operations in plan.modules().items()
        },
        "operations": [
            {
                "key": item.operation.key,
                "id": item.operation.id,
                "http_method": item.operation.http_method.value,
                "path": item.operation.path,
                "resource": item.resource,
                "kind": item.kind.value,
                "mode": item.mode.value,
                "module": item.module,
                "reason": item.classification.reason,
                "deprecated": item.operation.deprecated,
            }
            for item in plan.operations
        ],
        "unknown_operations": [item.operation.key for item in plan.unknown],
        "orphan_overrides": list(plan.orphan_overrides),
        "parser_warnings": list(plan.service.warnings),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def to_markdown(plan: ProductPlan) -> str:
    """Rapport lisible, destiné à la revue et à la documentation."""
    counts = plan.count_by_kind()
    modes = plan.count_by_mode()
    coverage = plan.coverage()
    service = plan.service

    lines: list[str] = [
        f"# Couverture Day-2 : {service.name} {service.version}",
        "",
        f"Contrat : `{service.source}`  ",
        f"Opérations découvertes : **{len(plan.operations)}**",
        "",
        "## Classification",
        "",
        "| classe | opérations |",
        "|---|---:|",
    ]
    for kind in _KIND_ORDER:
        lines.append(f"| {kind.value.upper()} | {counts[kind]} |")

    lines += [
        "",
        "## Couverture",
        "",
        "| mesure | valeur |",
        "|---|---:|",
        f"| candidates Day-2 | {len(plan.day2)} |",
        f"| AUTO | {modes[GenerationMode.AUTO]} |",
        f"| OVERRIDE | {modes[GenerationMode.OVERRIDE]} |",
        f"| MANUAL | {modes[GenerationMode.MANUAL]} |",
        f"| couverture Day-2 | {_percent(coverage)} |",
        "",
        "La couverture rapporte `(AUTO + OVERRIDE)` aux seules opérations Day-2.",
        "Les classes LIFECYCLE et IGNORE ne sont pas au dénominateur : elles ne",
        "sont pas du travail à automatiser, elles sont du travail écarté, et le",
        "tableau ci-dessus les compte à part pour que l'écart reste visible.",
        "",
        "## Modules cibles",
        "",
        "| module | opérations |",
        "|---|---|",
    ]
    for name, operations in plan.modules().items():
        ids = ", ".join(item.operation.id for item in operations)
        lines.append(f"| `{name}` | {ids} |")

    lines += [
        "",
        "## Opérations",
        "",
        "| opération | méthode | classe | mode | module | raison |",
        "|---|---|---|---|---|---|",
    ]
    for item in plan.operations:
        module = f"`{item.module}`" if item.module else "-"
        lines.append(
            f"| `{item.operation.id}` | {item.operation.http_method.value} | "
            f"{item.kind.value.upper()} | {item.mode.value.upper()} | {module} | "
            f"{item.classification.reason} |"
        )

    if plan.unknown:
        lines += ["", "## Opérations non classées", ""]
        lines += [f"- `{item.operation.key}`" for item in plan.unknown]

    if plan.orphan_overrides:
        lines += [
            "",
            "## Overrides orphelins",
            "",
            "Ces overrides ne désignent aucune opération du contrat : l'API a",
            "changé, ou la clé est fautive.",
            "",
        ]
        lines += [f"- `{key}`" for key in plan.orphan_overrides]

    if service.warnings:
        lines += ["", "## Limites relevées à la lecture du contrat", ""]
        lines += [f"- {warning}" for warning in service.warnings]

    return "\n".join(lines) + "\n"


def to_text(plan: ProductPlan) -> str:
    """Rapport console, celui que `python -m generator report` imprime."""
    counts = plan.count_by_kind()
    modes = plan.count_by_mode()
    service = plan.service

    lines = [
        f"{service.name} {service.version}",
        "",
        f"Operations discovered: {len(plan.operations)}",
        "",
    ]
    for kind in _KIND_ORDER:
        if counts[kind]:
            lines.append(f"  {kind.value.upper():<10} {counts[kind]:>3}")

    lines += [
        "",
        f"  {'Day-2':<10} {len(plan.day2):>3}",
        f"  {'AUTO':<10} {modes[GenerationMode.AUTO]:>3}",
        f"  {'OVERRIDE':<10} {modes[GenerationMode.OVERRIDE]:>3}",
        f"  {'MANUAL':<10} {modes[GenerationMode.MANUAL]:>3}",
        "",
        f"  Day-2 automation coverage {_percent(plan.coverage())}",
        "",
    ]

    for item in plan.operations:
        module = item.module or "-"
        lines.append(
            f"{item.operation.id:<38} {item.kind.value.upper():<10} "
            f"{item.mode.value.upper():<9} {module}"
        )

    if plan.unknown:
        lines += ["", f"{len(plan.unknown)} opération(s) non classée(s) :"]
        lines += [f"  {item.operation.key}" for item in plan.unknown]

    if plan.orphan_overrides:
        lines += ["", f"{len(plan.orphan_overrides)} override(s) orphelin(s) :"]
        lines += [f"  {key}" for key in plan.orphan_overrides]

    if service.warnings:
        lines += ["", f"{len(service.warnings)} limite(s) du contrat :"]
        lines += [f"  {warning}" for warning in service.warnings]

    return "\n".join(lines) + "\n"


def to_generation_markdown(
    plan: ProductPlan,
    written: Sequence[str],
    skipped: Sequence[tuple[str, str]],
    limits: Sequence[str],
) -> str:
    """Ce que la génération a produit, écarté, et ce que le contrat lui a caché.

    Ces trois listes existaient déjà, mais seulement sur la sortie standard de
    `generate` : elles disparaissaient avec le terminal. Or elles disent
    exactement ce qu'un lecteur veut savoir de la collection, à savoir pourquoi
    tel module n'existe pas, et le générateur est le seul à pouvoir le dire.
    """
    service = plan.service
    day2 = len(plan.day2)
    classee = plan.coverage()
    construite = plan.built_coverage(written)
    lines: list[str] = [
        f"# Génération : {service.name} {service.version}",
        "",
        f"Contrat : `{service.source}`  ",
        f"Modules écrits : **{len(written)}**, écartés : **{len(skipped)}**",
        "",
        "## Deux couvertures, et elles ne disent pas la même chose",
        "",
        "Un seul chiffre ne suffit pas ici, et publier le plus flatteur en",
        "laissant croire qu'il désigne l'autre serait exactement le genre de",
        "maquillage que ce rapport existe pour empêcher.",
        "",
        "| ce qu'on mesure | ratio | ce que ça veut dire |",
        "|---|---|---|",
        f"| opérations Day-2 **classées** pour génération automatique | {_ratio(classee, day2)} | "
        "aucune règle ne demande de les écrire à la main |",
        f"| opérations Day-2 **portées par un module que cette génération a écrit** "
        f"| {_ratio(construite, day2)} | un module existe et les appelle |",
        "",
        "Le second dépend du périmètre demandé autant que du générateur : un",
        "module hors périmètre et un module que le modèle refuse de construire",
        "comptent pareil ici, et se distinguent dans la section suivante, où",
        "chaque écart porte sa raison. C'est là que l'écart entre les deux",
        "ratios se lit en entier, module par module.",
        "",
        "## Ce qui est écrit",
        "",
    ]
    lines += [f"- `{nom}`" for nom in sorted(written)] or ["Aucun module écrit."]

    if skipped:
        groupes: dict[str, list[str]] = {}
        for nom, raison in skipped:
            groupes.setdefault(raison, []).append(nom)
        lines += [
            "",
            "## Ce qui est écarté, et pourquoi",
            "",
            "Un module absent sans explication serait indiscernable d'un module",
            "oublié. Chaque écart porte sa raison.",
            "",
            "| raison | modules |",
            "|---|---|",
        ]
        for raison, noms in sorted(groupes.items()):
            liste = ", ".join(f"`{nom}`" for nom in sorted(noms))
            lines.append(f"| {raison} ({len(noms)}) | {liste} |")

    if limits:
        lines += [
            "",
            "## Ce que le contrat ne dit pas",
            "",
            "Rencontré au rendu, et signalé plutôt que comblé par une supposition.",
            "",
        ]
        lines += [f"- {limite}" for limite in sorted(limits)]

    return "\n".join(lines) + "\n"


def _ratio(value: float | None, denominator: int) -> str:
    """Un pourcentage **et** sa fraction, parce que le dénominateur fait le sens.

    « 97,6 % » ne dit pas sur quoi porte le calcul, et c'est précisément la
    lecture qu'on veut empêcher. `41/42` la porte avec lui.
    """
    if value is None or not denominator:
        return "n/a (aucune opération Day-2)"
    return f"{value * 100:.1f} % ({round(value * denominator)}/{denominator})".replace(".", ",", 1)


def _percent(value: float | None) -> str:
    """Formate un ratio, sans jamais présenter un indéfini comme un zéro."""
    if value is None:
        return "n/a (aucune opération Day-2)"
    # La virgule décimale : le rapport est écrit en français, et « 97.6 % »
    # au milieu d'une phrase française est une coquille, pas un format.
    return f"{value * 100:.1f} %".replace(".", ",", 1)
