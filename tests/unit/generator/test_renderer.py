"""Le renderer écrit, et il écrit toujours la même chose.

Les tests portent sur le contrat de laboratoire : ils ne doivent pas rougir le
jour où Scaleway ajoute un serveur. La dérive du contrat réel est mesurée
ailleurs, par le golden de l'IR et par `mise run check:generated`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

from generator.ansible.collection import Collection
from generator.ansible.models import build_module_spec, build_module_specs
from generator.overrides.loader import OverrideSet
from generator.plan import ProductPlan
from generator.renderer.modules import (
    GENERATED_HEADER,
    RenderError,
    python_literal,
    quote,
    render_module,
)

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
GOLDEN = FIXTURES / "widget" / "expected_modules"
LAB_SOURCE = "tests/fixtures/widget/input/widget.v1.yml"

LAB_COLLECTION = Collection(
    namespace="lab",
    name="widget",
    version="9.9.9",
    path=FIXTURES / "widget" / "ansible_collections" / "lab" / "widget",
    authors=("Contrat de laboratoire (@lab)",),
)


def _rendu(plan: ProductPlan, module: str) -> str:
    spec = build_module_spec(module, plan.modules()[module], plan.service, LAB_COLLECTION)
    return render_module(spec, source=LAB_SOURCE)


# --- déterminisme ----------------------------------------------------------


def test_deux_rendus_produisent_le_meme_octet(widget_plan: ProductPlan) -> None:
    """Règle 6 du projet : même contrat, même sortie, octet pour octet."""
    assert _rendu(widget_plan, "widget_widget_info") == _rendu(widget_plan, "widget_widget_info")


def test_le_rendu_est_identique_au_golden(widget_plan: ProductPlan) -> None:
    """Régénérer après un changement voulu : `mise run golden:update`."""
    for chemin in sorted(GOLDEN.glob("*.py")):
        assert _rendu(widget_plan, chemin.stem) == chemin.read_text(encoding="utf-8"), chemin.name


def test_le_golden_contient_tous_les_modules_rendables(widget_plan: ProductPlan) -> None:
    """Un module qui cesserait d'être produit doit se voir dans le diff."""
    specs, _ = build_module_specs(widget_plan, LAB_COLLECTION)
    assert {spec.name for spec in specs} == {chemin.stem for chemin in GOLDEN.glob("*.py")}


# --- ce que le fichier produit porte ---------------------------------------


def test_un_fichier_produit_dit_quil_est_produit(widget_plan: ProductPlan) -> None:
    assert GENERATED_HEADER in _rendu(widget_plan, "widget_widget_info")


def test_le_module_ne_porte_aucune_logique(widget_plan: ProductPlan) -> None:
    """Le client, l'erreur et la pagination vivent dans le module_utils.

    La mesure est structurelle : un module généré ne définit que `main`, et
    `main` ne fait que deux choses. Une logique qui s'inviterait dans le
    template ferait immédiatement grossir ce compte.
    """
    arbre = ast.parse(_rendu(widget_plan, "widget_widget_info"))
    fonctions = [n.name for n in ast.walk(arbre) if isinstance(n, ast.FunctionDef)]
    assert fonctions == ["main"]

    main = next(n for n in ast.walk(arbre) if isinstance(n, ast.FunctionDef))
    assert len(main.body) == 2
    assert not [n for n in ast.walk(main) if isinstance(n, (ast.If, ast.For, ast.While, ast.Try))]


def test_la_documentation_produite_est_du_yaml_relisible(widget_plan: ProductPlan) -> None:
    """`ansible-test sanity` le dirait aussi, mais bien plus tard."""
    module = ast.parse(_rendu(widget_plan, "widget_widget_info"))
    blocs = {
        cible.id: noeud.value.value
        for noeud in module.body
        if isinstance(noeud, ast.Assign) and isinstance(noeud.value, ast.Constant)
        for cible in noeud.targets
        if isinstance(cible, ast.Name)
    }
    documentation = yaml.safe_load(blocs["DOCUMENTATION"])
    assert documentation["module"] == "widget_widget_info"
    assert set(documentation["options"]) == {"zone", "widget_id", "state"}
    assert yaml.safe_load(blocs["EXAMPLES"])[0]["lab.widget.widget_widget_info"]["zone"]
    assert yaml.safe_load(blocs["RETURN"])["widgets"]["type"] == "list"


def test_la_documentation_decrit_ce_que_le_module_accepte(widget_plan: ProductPlan) -> None:
    """La preuve de la source unique, faite sur le fichier produit lui-même."""
    rendu = _rendu(widget_plan, "widget_widget_info")
    module = ast.parse(rendu)
    documentation = None
    argument_spec = None
    for noeud in module.body:
        if not isinstance(noeud, ast.Assign) or not isinstance(noeud.targets[0], ast.Name):
            continue
        if noeud.targets[0].id == "DOCUMENTATION":
            documentation = yaml.safe_load(noeud.value.value)  # type: ignore[attr-defined]
        if noeud.targets[0].id == "MODULE_ARGUMENT_SPEC":
            argument_spec = ast.literal_eval(noeud.value)

    assert documentation is not None and argument_spec is not None
    assert set(documentation["options"]) == set(argument_spec)
    for nom, entree in argument_spec.items():
        assert documentation["options"][nom]["type"] == entree["type"]


def test_un_module_sans_liste_ne_declare_pas_de_selecteur(widget_plan: ProductPlan) -> None:
    rendu = _rendu(widget_plan, "widget_widget_gizmo_info")
    assert "selector=" not in rendu
    assert "list_operation=" in rendu
    assert "get_operation=" not in rendu


# --- les littéraux ---------------------------------------------------------


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [
        ("texte", '"texte"'),
        ('avec "guillemets"', "'avec \"guillemets\"'"),
        ("l'apostrophe", '"l\'apostrophe"'),
    ],
)
def test_les_chaines_sont_citees_comme_ruff_les_citerait(valeur: str, attendu: str) -> None:
    assert quote(valeur) == attendu


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [
        ((), "()"),
        (("zone",), '("zone",)'),
        (("zone", "server_id"), '("zone", "server_id")'),
        ([], "[]"),
        ({}, "{}"),
        ({"type": "str"}, '{"type": "str"}'),
        (True, "True"),
        (None, "None"),
        (3, "3"),
    ],
)
def test_les_petits_litteraux_tiennent_sur_une_ligne(valeur: object, attendu: str) -> None:
    assert python_literal(valeur) == attendu


def test_un_litteral_long_se_deplie_et_reste_relisible() -> None:
    """Le rendu doit rester du Python valide, quelle que soit sa longueur."""
    valeur = {"choices": [f"valeur-numero-{index:02d}" for index in range(12)]}
    rendu = python_literal(valeur)
    assert "\n" in rendu
    assert ast.literal_eval(rendu) == valeur


def test_une_triple_quote_dans_la_documentation_est_refusee(widget_plan: ProductPlan) -> None:
    """Elle fermerait le bloc `r\"\"\"` et casserait le fichier produit."""
    spec = build_module_spec(
        "widget_widget_info",
        widget_plan.modules()["widget_widget_info"],
        widget_plan.service,
        LAB_COLLECTION,
    )
    piege = type(spec)(
        **{
            **spec.__dict__,
            "short_description": 'court """ description',
        }
    )
    with pytest.raises(RenderError):
        render_module(piege, source=LAB_SOURCE)


def test_le_plan_de_laboratoire_ne_depend_daucun_override(widget_plan: ProductPlan) -> None:
    assert widget_plan.overrides == OverrideSet(source=None)
