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
from generator.ansible.models import ModuleModelError, build_module_specs
from generator.overrides.loader import OverrideError
from generator.parser.openapi import ParseError, parse_document
from generator.plan import ProductPlan, build_plan
from generator.renderer.modules import write_modules
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
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    version = arguments.api_version or DEFAULT_VERSIONS.get(arguments.product, "v1")

    try:
        if arguments.command == "inspect":
            return _inspect(arguments.product, version, arguments.spec_root)
        plan = build_plan(arguments.product, version, spec_root=arguments.spec_root)
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
        except (CollectionError, ModuleModelError) as error:
            print(f"erreur : {error}", file=sys.stderr)
            return EXIT_ERROR

    output_dir: Path = arguments.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = f"{plan.service.name}.{plan.service.version}"
    (output_dir / f"{slug}.json").write_text(render.to_json(plan), encoding="utf-8")
    (output_dir / f"{slug}.md").write_text(render.to_markdown(plan), encoding="utf-8")
    print(render.to_text(plan), end="")
    print(f"\nrapports écrits dans {output_dir}/{slug}.{{json,md}}")

    if arguments.strict and (plan.unknown or plan.orphan_overrides):
        print(
            f"\n{len(plan.unknown)} opération(s) non classée(s), "
            f"{len(plan.orphan_overrides)} override(s) orphelin(s)",
            file=sys.stderr,
        )
        return EXIT_UNDECIDED
    return EXIT_OK


def _generate(plan: ProductPlan, arguments: argparse.Namespace) -> int:
    """Écrit les modules, et dit ce qu'il n'a pas écrit et pourquoi.

    Un module absent de la sortie sans explication serait indiscernable d'un
    module oublié : la liste des écartés fait donc partie du résultat, pas de
    la mise en forme.
    """
    collection = load_collection(arguments.collection_root)
    output_dir = arguments.output_dir or collection.modules_dir
    specs, skipped = build_module_specs(plan, collection, only=tuple(arguments.modules))
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
