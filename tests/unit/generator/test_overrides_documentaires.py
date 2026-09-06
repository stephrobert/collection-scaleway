"""Combler un trou du contrat est une décision, et une décision se contrôle.

Ce que ces tests protègent tient en une phrase : **la page publiée sur Galaxy
est immuable**. Un module qui y arrive avec « Not documented by the Scaleway API
contract. » ou avec `zone: <zone>` publie ça pour toujours, et le lecteur n'a
nulle part où aller le compléter.

Les overrides documentaires réparent ça, et introduisent trois façons de mentir
que ces tests refusent : publier un texte sans dire d'où il vient, recouvrir la
phrase du contrat par la sienne, et garder un texte que le contrat a rendu
inutile.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.collection import Collection
from generator.ansible.models import build_module_specs
from generator.ir.models import ApiService
from generator.overrides.loader import OverrideError, load_overrides
from generator.plan import plan_service

COLLECTION = Collection(namespace="demo", name="widget", version="0.0.1", path=Path("/dev/null"))


def _write(root: Path, contenu: str) -> Path:
    path = root / "widget.yml"
    path.write_text(contenu, encoding="utf-8")
    return path


def _option(service: ApiService, root: Path, module: str, nom: str):
    plan = plan_service(service, load_overrides("widget", root=root))
    specs, _ = build_module_specs(plan, COLLECTION)
    spec = next(s for s in specs if s.name == module)
    return next(o for o in spec.options if o.name == nom)


def test_une_cle_declaree_deux_fois_est_refusee(tmp_path: Path) -> None:
    """YAML garde la dernière occurrence, et efface la première sans un mot.

    Le cas est arrivé : un second bloc `MigrateLb` a remplacé celui qui portait
    `resource: load_balancer`, le module publié a changé de nom, et aucun
    contrôle n'a rougi. Le contrôle d'orphelins ne pouvait rien y faire, la clé
    désignant bien une opération : c'est la décision qui avait disparu.
    """
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.GetWidget:
    resource: widget
  widget.v1.Widget.GetWidget:
    parameters:
      widget_id:
        description: UUID of the widget.
        reason: le contrat ne le décrit pas
""",
    )
    with pytest.raises(OverrideError, match="deux fois"):
        load_overrides("widget", root=tmp_path)


def test_une_description_publiee_sans_raison_est_refusee(tmp_path: Path) -> None:
    """Le texte sortira sur Galaxy sous le nom de la collection.

    Un lecteur n'a aucun moyen de le distinguer d'une phrase de Scaleway. La
    raison est ce qui dit d'où il vient, et elle n'est pas facultative.
    """
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.GetWidget:
    parameters:
      widget_id:
        description: UUID of the widget.
""",
    )
    with pytest.raises(OverrideError, match="sans `reason`"):
        load_overrides("widget", root=tmp_path)


def test_une_valeur_dexemple_sans_raison_est_refusee(tmp_path: Path) -> None:
    """Un exemple se copie : une valeur fausse y est pire qu'un trou."""
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.GetWidget:
    parameters:
      widget_id:
        example: "42"
""",
    )
    with pytest.raises(OverrideError, match="sans `reason`"):
        load_overrides("widget", root=tmp_path)


def test_un_override_comble_le_trou_du_contrat(tmp_path: Path, widget_service: ApiService) -> None:
    """`GetWidget.widget_id` n'a pas de description dans le contrat."""
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.GetWidget:
    parameters:
      widget_id:
        description: UUID of the widget.
        reason: transposé de la description que porte ListWidgets
""",
    )
    option = _option(widget_service, tmp_path, "widget_widget_info", "widget_id")
    assert option.description == ("UUID of the widget.",)


def test_le_contrat_gagne_toujours_sur_loverride(
    tmp_path: Path, widget_service: ApiService
) -> None:
    """Recouvrir une phrase du contrat ferait diverger la page de l'API.

    Et la divergence serait invisible : rien, sur la page publiée, ne dit qu'un
    texte vient d'un override plutôt que de Scaleway.
    """
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.ListWidgets:
    parameters:
      state:
        description: Ce texte ne doit jamais sortir.
        reason: tentative de recouvrement, que le générateur doit ignorer
""",
    )
    option = _option(widget_service, tmp_path, "widget_widget_info", "state")
    assert option.description != ("Ce texte ne doit jamais sortir.",)


def test_un_override_qui_ne_comble_plus_rien_est_orphelin(
    tmp_path: Path, widget_service: ApiService
) -> None:
    """Le jour où l'amont documente le champ, le texte écrit ici devient mort.

    Il ne se voit plus sur la page, donc plus personne ne le relit, et une
    relecture le croirait publié. Il sort par le canal des orphelins, ce qui
    fait sortir `report --strict` en 2.
    """
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.ListWidgets:
    parameters:
      state:
        description: Ce texte ne comble plus rien.
        reason: le contrat décrit déjà `state`, donc cet override est inerte
""",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))
    assert any("state" in orphelin for orphelin in plan.orphan_overrides), (
        f"orphelins vus : {plan.orphan_overrides}"
    )
