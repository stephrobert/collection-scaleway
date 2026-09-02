"""Régénère les golden fixtures depuis les contrats versionnés.

Un golden se met à jour délibérément : la commande est séparée des tests pour
qu'un diff inattendu apparaisse dans une revue, jamais dans un `pytest -u`.

Deux golden, et ils ne mesurent pas la même chose :

* `tests/fixtures/<produit>/expected_ir.json` fige ce que le **parser** lit du
  contrat réel. Il bouge quand Scaleway bouge ;
* `tests/fixtures/widget/expected_modules/` fige ce que le **renderer** écrit,
  à partir du contrat de laboratoire. Il ne doit pas bouger le jour où
  Scaleway ajoute un serveur, et c'est exactement pour ça qu'il porte sur
  `widget` et non sur `instance`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from generator.ansible.collection import Collection
from generator.ansible.models import build_module_specs
from generator.overrides.loader import OverrideSet
from generator.parser.openapi import parse_document
from generator.plan import plan_service
from generator.renderer.modules import write_modules
from generator.source.base import VendoredSpecSource

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
WIDGET_SPECS = FIXTURES / "widget" / "input"
WIDGET_MODULES = FIXTURES / "widget" / "expected_modules"

#: Identité figée pour le golden de rendu. Elle ne lit pas `galaxy.yml` : le
#: golden mesure le renderer, pas le namespace du jour.
LAB_COLLECTION = Collection(
    namespace="lab",
    name="widget",
    version="9.9.9",
    path=FIXTURES / "widget" / "ansible_collections" / "lab" / "widget",
    authors=("Contrat de laboratoire (@lab)",),
)


def update_ir() -> None:
    """Fige l'IR de chaque contrat versionné."""
    source = VendoredSpecSource(root=ROOT / "specs" / "scaleway")
    for product, version in source.available():
        service = parse_document(source.load(product, version))
        target = FIXTURES / product / "expected_ir.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(service.to_json(), encoding="utf-8")
        print(f"{target.relative_to(ROOT)} : {len(service.operations)} opérations")


def update_rendered_modules() -> None:
    """Fige les modules rendus depuis le contrat de laboratoire."""
    service = parse_document(VendoredSpecSource(root=WIDGET_SPECS).load("widget", "v1"))
    plan = plan_service(service, OverrideSet(source=None))
    specs, _ = build_module_specs(plan, LAB_COLLECTION)

    if WIDGET_MODULES.exists():
        # Un module retiré du plan doit disparaître du golden, sinon le diff
        # ne dirait rien le jour où le renderer cesse de le produire.
        shutil.rmtree(WIDGET_MODULES)
    written = write_modules(
        specs, WIDGET_MODULES, source="tests/fixtures/widget/input/widget.v1.yml"
    )
    for path in written:
        print(f"{path.relative_to(ROOT)}")


def main() -> int:
    update_ir()
    update_rendered_modules()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
