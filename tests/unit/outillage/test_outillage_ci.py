"""L'outillage de la CI n'est déclaré qu'à un endroit.

Le défaut mesuré : la version de `mise` et le condensat de l'action qui
l'installe étaient recopiés dans neuf étapes réparties sur quatre workflows.
Dependabot rattrape le condensat, pas la version : une des neuf pouvait partir
seule, et rien ne l'aurait vu.
"""

from __future__ import annotations

from pathlib import Path

import outillage_ci
import pytest
import yaml

ENVELOPPE = """\
runs:
  using: composite
  steps:
    - uses: jdx/mise-action@aaaa # v4.2.5
      with:
        version: 2026.2.23
"""

WORKFLOW_PROPRE = """\
jobs:
  build:
    steps:
      - uses: ./.github/actions/mise
      - run: mise run check
"""

WORKFLOW_EN_DOUBLE = """\
jobs:
  build:
    steps:
      - uses: jdx/mise-action@aaaa # v4.2.5
        with:
          version: 2026.2.23
"""


@pytest.fixture
def depot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un dépôt à nous, jamais celui du projet."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "actions" / "mise").mkdir(parents=True)
    (tmp_path / ".github" / "actions" / "mise" / "action.yml").write_text(
        ENVELOPPE, encoding="utf-8"
    )
    monkeypatch.setattr(outillage_ci, "ROOT", tmp_path)
    monkeypatch.setattr(outillage_ci, "WORKFLOWS", tmp_path / ".github" / "workflows")
    monkeypatch.setattr(outillage_ci, "ACTIONS", tmp_path / ".github" / "actions")
    return tmp_path


def _outil() -> outillage_ci.Outil:
    return outillage_ci.SOUS_SURVEILLANCE[0]


def test_une_seule_declaration_dans_lenveloppe_est_conforme(depot: Path) -> None:
    (depot / ".github" / "workflows" / "ci.yml").write_text(WORKFLOW_PROPRE, encoding="utf-8")
    assert outillage_ci.declarations(_outil()) == [".github/actions/mise/action.yml"]


def test_un_appel_direct_dans_un_workflow_est_vu(depot: Path) -> None:
    """La ligne exacte que les neuf étapes portaient."""
    (depot / ".github" / "workflows" / "ci.yml").write_text(WORKFLOW_EN_DOUBLE, encoding="utf-8")
    trouvees = outillage_ci.declarations(_outil())
    assert ".github/workflows/ci.yml" in trouvees
    assert len(trouvees) == 2, trouvees


def test_les_etapes_dune_action_composite_sont_lues(depot: Path) -> None:
    """Une action composite n'a pas de `jobs`, et c'est là que l'appel vit.

    Ne lire que les `jobs` rendrait le contrôle aveugle à l'enveloppe
    elle-même : il conclurait que l'outil n'est déclaré nulle part.
    """
    (depot / ".github" / "workflows" / "ci.yml").write_text(WORKFLOW_PROPRE, encoding="utf-8")
    document = yaml.safe_load(ENVELOPPE)
    assert len(outillage_ci._etapes(document)) == 1


def test_un_outil_declare_nulle_part_est_refuse(depot: Path) -> None:
    """L'autre bord : un contrôle qui ne trouve rien ne doit pas conclure « conforme ».

    Sans lui, retirer l'enveloppe **et** tous les appels passerait pour une
    mise en conformité, alors que la CI n'installerait plus rien.
    """
    (depot / ".github" / "actions" / "mise" / "action.yml").write_text(
        "runs:\n  using: composite\n  steps:\n    - run: true\n", encoding="utf-8"
    )
    (depot / ".github" / "workflows" / "ci.yml").write_text(WORKFLOW_PROPRE, encoding="utf-8")
    assert outillage_ci.declarations(_outil()) == []


def test_le_depot_na_quune_declaration() -> None:
    """Le seul test du fichier qui regarde le dépôt, et c'est voulu."""
    for outil in outillage_ci.SOUS_SURVEILLANCE:
        attendu = f".github/actions/{Path(outil.enveloppe).name}/action.yml"
        assert outillage_ci.declarations(outil) == [attendu]


def test_le_plancher_de_mise_est_declare() -> None:
    """`mise.toml` refuse un `mise` trop ancien pour le lire.

    C'est une autre chose que l'épingle de CI, et les deux existent : l'une fixe
    ce que la CI installe, l'autre protège le poste de qui développe.
    """
    import tomllib

    document = tomllib.loads((outillage_ci.ROOT / "mise.toml").read_text(encoding="utf-8"))
    assert document.get("min_version"), "mise.toml ne déclare aucun plancher de version"


def test_le_plancher_et_lepingle_disent_la_meme_version() -> None:
    """Ce qui empêche le gel de revenir.

    L'épingle a été posée sur la version installée du poste, et rien ne pouvait
    la lever : Dependabot suit le condensat de l'action, pas son entrée
    `version:`. Lier les deux fait qu'on ne peut plus monter l'une sans l'autre.
    """
    outil = outillage_ci.SOUS_SURVEILLANCE[0]
    epinglee = outillage_ci.version_epinglee(outil)
    assert epinglee, "l'enveloppe n'épingle aucune version"
    assert epinglee == outillage_ci.plancher()


def test_une_enveloppe_sans_version_est_vue(depot: Path) -> None:
    """Une enveloppe qui n'épingle rien laisse l'action résoudre « la dernière ».

    C'est le cas qui a produit la panne du 8 septembre 2026 : le point de
    version annonçait un numéro dont la release ne portait aucun artefact.
    """
    (depot / ".github" / "actions" / "mise" / "action.yml").write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: jdx/mise-action@aaaa\n",
        encoding="utf-8",
    )
    assert outillage_ci.version_epinglee(outillage_ci.SOUS_SURVEILLANCE[0]) is None


def test_une_divergence_entre_le_plancher_et_lepingle_est_refusee(depot: Path) -> None:
    """Le refus lui-même, et pas seulement l'invariant qu'il protège.

    Le test précédent compare les deux valeurs du dépôt ; celui-ci exerce la
    branche qui refuse, sans laquelle la comparaison ne serait qu'une lecture.
    """
    (depot / ".github" / "workflows" / "ci.yml").write_text(WORKFLOW_PROPRE, encoding="utf-8")
    (depot / "mise.toml").write_text('min_version = "1.0.0"\n', encoding="utf-8")

    assert outillage_ci.main([]) == 2


def test_un_plancher_egal_a_lepingle_passe(depot: Path) -> None:
    """Le contre-exemple : le refus doit laisser passer ce qui est conforme."""
    (depot / ".github" / "workflows" / "ci.yml").write_text(WORKFLOW_PROPRE, encoding="utf-8")
    (depot / "mise.toml").write_text('min_version = "2026.2.23"\n', encoding="utf-8")

    assert outillage_ci.main([]) == 0
