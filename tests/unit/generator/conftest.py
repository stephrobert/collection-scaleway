"""Fixtures partagées des tests du générateur."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.collection import Collection, load_collection
from generator.ir.models import ApiService
from generator.overrides.loader import OverrideSet
from generator.parser.openapi import parse_document
from generator.plan import ProductPlan, build_plan, plan_service
from generator.source.base import VendoredSpecSource

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
WIDGET_SPECS = FIXTURES / "widget" / "input"
INSTANCE_SPECS = REPO_ROOT / "specs" / "scaleway"


@pytest.fixture(scope="session")
def widget_service() -> ApiService:
    """IR du contrat de test, indépendant des évolutions de l'API Scaleway."""
    return parse_document(VendoredSpecSource(root=WIDGET_SPECS).load("widget", "v1"))


@pytest.fixture()
def widget_plan(widget_service: ApiService) -> ProductPlan:
    return plan_service(widget_service, OverrideSet(source=None))


@pytest.fixture(scope="session")
def instance_service() -> ApiService:
    """IR du contrat Instance réel, tel qu'il est versionné dans `specs/`."""
    return parse_document(VendoredSpecSource(root=INSTANCE_SPECS).load("instance", "v1"))


@pytest.fixture(scope="session")
def instance_plan() -> ProductPlan:
    return build_plan("instance", "v1", spec_root=INSTANCE_SPECS)


@pytest.fixture(scope="session")
def lb_plan() -> ProductPlan:
    """Le second produit généré, et celui dont le nom publié diffère du slug.

    « Load Balancer API » d'un côté, `lb` de l'autre : c'est sur lui que se
    voient les défauts de vocabulaire qu'Instance ne peut pas montrer.
    """
    return build_plan("lb", "v1", spec_root=INSTANCE_SPECS)


@pytest.fixture(scope="session")
def collection() -> Collection:
    """La collection livrée, lue dans `galaxy.yml` comme le générateur le fait."""
    return load_collection()
