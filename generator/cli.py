"""Interface en ligne de commande du générateur.

    python -m generator inspect instance      # ce que le contrat contient
    python -m generator classify instance     # la décision, opération par opération
    python -m generator report instance       # les rapports, texte, JSON et Markdown
    python -m generator generate instance     # les modules, dans plugins/modules

Codes de sortie, la CI en dépend :

* ``0`` succès ;
* ``1`` erreur d'exécution (contrat absent, override invalide, modèle
  impossible à construire) ;
* ``2`` le rapport contient une opération non classée ou un override orphelin,
  avec ``--strict``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generator.ansible.collection import CollectionError, load_collection
from generator.ansible.introductions import IntroductionsError, load_introductions
from generator.ansible.models import ModuleModelError, build_module_specs
from generator.ansible.resolution import (
    Refus,
    Resolution,
    build_resolutions,
    merge_refus,
    merge_resolutions,
)
from generator.ir.enums import OperationKind
from generator.overrides.loader import DEFAULT_OVERRIDES_ROOT, OverrideError
from generator.parser.openapi import ParseError, parse_document
from generator.plan import ProductPlan, build_plan
from generator.renderer.modules import write_modules
from generator.renderer.resolution import render_resolution
from generator.report import render
from generator.source.base import DEFAULT_SPEC_ROOT, SpecNotFoundError, VendoredSpecSource

ROOT = Path(__file__).resolve().parents[1]

#: Version par défaut de chaque produit, à défaut de `--api-version`.
DEFAULT_VERSIONS: dict[str, str] = {"instance": "v1"}

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_UNDECIDED = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m generator",
        description="Générateur de modules Ansible Day-2 pour Scaleway.",
    )
    parser.add_argument(
        "--spec-root",
        type=Path,
        default=DEFAULT_SPEC_ROOT,
        help="racine des contrats versionnés (défaut : specs/scaleway)",
    )
    parser.add_argument(
        "--overrides-root",
        type=Path,
        default=DEFAULT_OVERRIDES_ROOT,
        help="racine des décisions humaines (défaut : generator/overrides)",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("inspect", "afficher ce que le contrat déclare"),
        ("classify", "afficher la classification, opération par opération"),
        ("report", "produire les rapports de couverture"),
        ("generate", "écrire les modules Ansible dans plugins/modules"),
    ):
        subcommand = subcommands.add_parser(name, help=help_text)
        subcommand.add_argument("product", help="produit Scaleway, par exemple instance")
        subcommand.add_argument(
            "--api-version", dest="api_version", default=None, help="version de l'API (défaut : v1)"
        )

    report = subcommands.choices["report"]
    report.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/reports"),
        help="répertoire des rapports JSON et Markdown",
    )
    report.add_argument(
        "--strict",
        action="store_true",
        help="sortir en 2 si une opération n'est pas classée ou si un override est orphelin",
    )

    generate = subcommands.choices["generate"]
    generate.add_argument(
        "--report-dir",
        type=Path,
        default=Path("build/reports"),
        help="répertoire où verser le compte rendu de génération",
    )
    generate.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="répertoire des modules produits (défaut : celui de la collection)",
    )
    generate.add_argument(
        "--module",
        action="append",
        dest="modules",
        default=[],
        metavar="NOM",
        help=(
            "restreindre la production aux modules nommés ; répétable. "
            "Sans cette option, tous les modules rendables sont écrits."
        ),
    )
    generate.add_argument(
        "--collection-root",
        type=Path,
        default=None,
        help="racine de la collection (défaut : découverte sous ansible_collections/)",
    )

    # Sans produit, délibérément : la table est fondue entre tous les contrats
    # générés. En écrire une par produit laisserait passer un identifiant
    # revendiqué deux fois, et publierait celui du premier lu.
    resolve = subcommands.add_parser(
        "resolve", help="écrire la table de résolution dans module_utils"
    )
    resolve.add_argument(
        "--collection-root",
        type=Path,
        default=None,
        help="racine de la collection (défaut : découverte sous ansible_collections/)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)

    if arguments.command == "resolve":
        try:
            return _resolve(arguments)
        except (SpecNotFoundError, ParseError, OverrideError, CollectionError) as error:
            print(f"erreur : {error}", file=sys.stderr)
            return EXIT_ERROR

    version = arguments.api_version or DEFAULT_VERSIONS.get(arguments.product, "v1")

    try:
        if arguments.command == "inspect":
            return _inspect(arguments.product, version, arguments.spec_root)
        plan = build_plan(
            arguments.product,
            version,
            spec_root=arguments.spec_root,
            overrides_root=arguments.overrides_root,
        )
    except SpecNotFoundError as error:
        print(f"erreur : {error}", file=sys.stderr)
        return EXIT_ERROR
    except (ParseError, OverrideError) as error:
        print(f"erreur : {error}", file=sys.stderr)
        return EXIT_ERROR

    if arguments.command == "classify":
        print(render.to_text(plan), end="")
        return EXIT_OK

    if arguments.command == "generate":
        try:
            return _generate(plan, arguments)
        except (CollectionError, IntroductionsError, ModuleModelError) as error:
            print(f"erreur : {error}", file=sys.stderr)
            return EXIT_ERROR

    output_dir: Path = arguments.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = f"{plan.service.name}.{plan.service.version}"
    (output_dir / f"{slug}.json").write_text(render.to_json(plan), encoding="utf-8")
    (output_dir / f"{slug}.md").write_text(render.to_markdown(plan), encoding="utf-8")
    print(render.to_text(plan), end="")
    print(f"\nrapports écrits dans {output_dir}/{slug}.{{json,md}}")

    if arguments.strict and not plan.operations:
        # **Un rapport qui n'a rien découvert n'est pas un rapport vert.** Sans
        # cette garde, un contrat vide, mal lu ou pointant vers le mauvais
        # fichier sort en 0 : zéro opération non classée, zéro override
        # orphelin, donc tout va bien. C'est indiscernable d'un produit
        # parfaitement classé, et c'est le vert le plus gratuit qu'un dépôt
        # puisse produire.
        #
        # Code 1 et non 2 : la règle 9 réserve le 2 à une opération non triée ou
        # à un override orphelin. Ici il n'y a pas de décision en suspens, il y
        # a une entrée cassée.
        print(
            f"erreur : {plan.service.slug} ne déclare aucune opération. "
            "Un rapport qui ne mesure rien passerait pour un rapport vert.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    if arguments.strict and (plan.unknown or plan.orphan_overrides):
        print(
            f"\n{len(plan.unknown)} opération(s) non classée(s), "
            f"{len(plan.orphan_overrides)} override(s) orphelin(s)",
            file=sys.stderr,
        )
        return EXIT_UNDECIDED
    return EXIT_OK


def _resolve(arguments: argparse.Namespace) -> int:
    """Écrit la table de résolution, et dit ce qu'elle ne résout pas.

    Les refus sont écrits dans le même fichier que les résolutions : un
    identifiant absent parce que le contrat est muet et un identifiant absent
    parce que personne n'y a pensé se ressemblent trop pour être distingués par
    une absence.
    """
    collection = load_collection(arguments.collection_root)
    source = VendoredSpecSource(root=arguments.spec_root)

    tables: list[tuple[Resolution, ...]] = []
    refus: list[Refus] = []
    # `Classification.kind` porte l'`OperationKind` : la table de réessai se
    # calcule avec la même règle que les modules, sinon deux politiques
    # cohabiteraient pour une seule opération.
    classifications: dict[str, OperationKind] = {}
    sources: list[str] = []

    for produit, version in source.available():
        plan = build_plan(
            produit,
            version,
            spec_root=arguments.spec_root,
            overrides_root=arguments.overrides_root,
        )
        service = plan.service
        sources.append(f"specs/scaleway/{service.source}")
        for entree in plan.operations:
            classifications[entree.operation.id] = entree.classification.kind

        identifiants = {
            parametre.name
            for operation in service.operations
            for parametre in operation.parameters
            if parametre.location.value == "path" and parametre.name.endswith("_id")
        }
        resolutions, refuses = build_resolutions(service, identifiants)
        tables.append(resolutions)
        refus.extend(refuses)

    gardees, conflits = merge_resolutions(tables)
    refus.extend(conflits)
    refus = list(merge_refus(refus))

    cible = collection.path / "plugins" / "module_utils" / "resolution.py"
    cible.write_text(
        render_resolution(
            gardees,
            refus,
            classifications=classifications,
            sources=sources,
        ),
        encoding="utf-8",
    )

    affichage = cible.relative_to(ROOT) if cible.is_relative_to(ROOT) else cible
    print(f"table de résolution -> {affichage}")
    print()
    for resolution in sorted(gardees, key=lambda item: item.parameter):
        portee = ", ".join(resolution.scope) or "la zone seule"
        print(f"  résolu   {resolution.parameter:<26} {resolution.list_operation:<24} {portee}")
    if refus:
        print()
        for refuse in sorted(refus, key=lambda item: item.parameter):
            print(f"  refusé   {refuse.parameter:<26} {refuse.reason}")
    print(f"\n{len(gardees)} identifiant(s) résoluble(s), {len(refus)} refus.")
    return EXIT_OK


def _generate(plan: ProductPlan, arguments: argparse.Namespace) -> int:
    """Écrit les modules, et dit ce qu'il n'a pas écrit et pourquoi.

    Un module absent de la sortie sans explication serait indiscernable d'un
    module oublié : la liste des écartés fait donc partie du résultat, pas de
    la mise en forme.
    """
    collection = load_collection(arguments.collection_root)
    output_dir = arguments.output_dir or collection.modules_dir
    # Le journal des apparitions, et pas la version courante de la collection :
    # sans lui, chaque génération redate tous les modules du jour où elle
    # tourne, et une page Galaxy est publiée pour toujours (ADR-013).
    specs, skipped = build_module_specs(
        plan,
        collection,
        only=tuple(arguments.modules),
        introductions=load_introductions(),
    )
    written = write_modules(
        specs,
        output_dir,
        source=f"specs/scaleway/{plan.service.source}",
    )

    affichage = output_dir.relative_to(ROOT) if output_dir.is_relative_to(ROOT) else output_dir
    print(f"{plan.service.slug} -> {affichage} (collection {collection.fqcn})")
    print()
    for spec in sorted(specs, key=lambda item: item.name):
        operations = ", ".join(
            operation.id
            for operation in (spec.get_operation, spec.list_operation, spec.action_operation)
            if operation is not None
        )
        print(f"  écrit    {spec.name:<34} {operations}")

    if skipped:
        grouped: dict[str, list[str]] = {}
        for name, reason in skipped:
            grouped.setdefault(reason, []).append(name)
        print()
        for reason, names in sorted(grouped.items()):
            print(f"  écarté   {reason} ({len(names)})")
            print(f"           {', '.join(sorted(names))}")

    limits = sorted({limit for spec in specs for limit in spec.limits})
    if limits:
        print(f"\n{len(limits)} limite(s) du contrat rencontrée(s) au rendu :")
        for limit in limits:
            print(f"  {limit}")

    print(f"\n{len(written)} module(s) écrit(s).")

    # Ces trois listes ne vivaient que sur la sortie standard, donc elles
    # mouraient avec le terminal. Elles sont ce qu'un lecteur veut savoir de la
    # collection : pourquoi tel module n'existe pas.
    arguments.report_dir.mkdir(parents=True, exist_ok=True)
    compte_rendu = arguments.report_dir / f"{plan.service.slug}.generation.md"
    compte_rendu.write_text(
        render.to_generation_markdown(
            plan,
            written=[spec.name for spec in specs],
            skipped=skipped,
            limits=limits,
            comparisons=plan.comparison_strategies(specs),
        ),
        encoding="utf-8",
    )
    return EXIT_OK


def _inspect(product: str, version: str, spec_root: Path) -> int:
    """Affiche le contenu du contrat sans le classer."""
    service = parse_document(VendoredSpecSource(root=spec_root).load(product, version))
    print(f"{service.title or service.name} ({service.slug})")
    print(f"  contrat    : {service.source}")
    print(f"  opérations : {len(service.operations)}")
    print(f"  enums      : {len(service.enums)}")
    print()
    for operation in service.operations:
        pagination = "paginée" if operation.pagination else ""
        print(
            f"  {operation.http_method.value:<6} {operation.id:<38} "
            f"{operation.scope.value:<6} {len(operation.parameters):>2} param. {pagination}"
        )
    if service.warnings:
        print(f"\n{len(service.warnings)} limite(s) relevée(s) :")
        for warning in service.warnings:
            print(f"  {warning}")
    return EXIT_OK
