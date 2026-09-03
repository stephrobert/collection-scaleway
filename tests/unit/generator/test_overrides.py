"""Un override est une affirmation : il doit désigner quelque chose, et se justifier."""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ir.enums import GenerationMode, OperationKind
from generator.ir.models import ApiService
from generator.overrides.loader import OverrideError, load_overrides
from generator.plan import plan_service


def _write(root: Path, contenu: str) -> Path:
    path = root / "widget.yml"
    path.write_text(contenu, encoding="utf-8")
    return path


def test_un_produit_sans_fichier_donne_un_ensemble_vide(tmp_path: Path) -> None:
    overrides = load_overrides("widget", root=tmp_path)
    assert overrides.operations == {}
    assert overrides.source is None


def test_un_override_change_la_classification(tmp_path: Path, widget_service: ApiService) -> None:
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.CreateWidget:
    generation: ignore
    reason: création de ressource, périmètre Terraform
""",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))
    creation = next(item for item in plan.operations if item.operation.id == "CreateWidget")
    assert creation.kind is OperationKind.IGNORE
    assert creation.mode is GenerationMode.OVERRIDE
    assert creation.module is None


def test_un_override_renomme_le_module(tmp_path: Path, widget_service: ApiService) -> None:
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.WidgetAction:
    module: widget_machine_action
""",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))
    action = next(item for item in plan.operations if item.operation.id == "WidgetAction")
    assert action.module == "widget_machine_action"


def test_un_champ_inconnu_est_refuse(tmp_path: Path) -> None:
    """Une faute de frappe produirait sinon un override silencieusement inerte."""
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.GetWidget:
    generatoin: ignore
    reason: faute de frappe volontaire
""",
    )
    with pytest.raises(OverrideError, match="champs inconnus"):
        load_overrides("widget", root=tmp_path)


def test_une_classification_sans_raison_est_refusee(tmp_path: Path) -> None:
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.GetWidget:
    generation: ignore
""",
    )
    with pytest.raises(OverrideError, match="reason"):
        load_overrides("widget", root=tmp_path)


def test_une_valeur_de_generation_inconnue_est_refusee(tmp_path: Path) -> None:
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.GetWidget:
    generation: peut-etre
    reason: valeur inventée
""",
    )
    with pytest.raises(OverrideError, match="generation"):
        load_overrides("widget", root=tmp_path)


def test_un_override_orphelin_est_signale(tmp_path: Path, widget_service: ApiService) -> None:
    """Une clé qui ne désigne aucune opération décrit une API qui n'existe pas."""
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.DisparuDepuis:
    generation: ignore
    reason: opération retirée de l'API
""",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))
    assert plan.orphan_overrides == ("widget.v1.Widget.DisparuDepuis",)


def test_manual_reste_hors_de_la_couverture_automatique(
    tmp_path: Path, widget_service: ApiService
) -> None:
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.UpdateWidget:
    generation: manual
    reason: comparaison de listes ordonnées, écrite à la main
""",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))
    mise_a_jour = next(item for item in plan.operations if item.operation.id == "UpdateWidget")
    assert mise_a_jour.kind is OperationKind.WORKFLOW
    assert mise_a_jour.mode is GenerationMode.MANUAL
    assert mise_a_jour.is_day2, "un workflow reste une opération Day-2"
    assert plan.coverage() is not None and plan.coverage() < 1.0


def test_les_overrides_du_produit_instance_ne_sont_pas_orphelins(instance_plan) -> None:
    """Le fichier livré doit désigner des opérations qui existent réellement."""
    assert instance_plan.orphan_overrides == ()


def test_un_parametre_arbitre_sans_raison_est_refuse(tmp_path: Path) -> None:
    """Restreindre, exiger ou masquer un paramètre est un arbitrage.

    Le contrat déclare l'enum et les champs ; s'en écarter est une décision, et
    une décision sans raison est indéfendable à la relecture.
    """
    (tmp_path / "demo.yml").write_text(
        "operations:\n"
        "  demo.v1.Thing.ThingAction:\n"
        "    parameters:\n"
        "      action:\n"
        "        choices: [poweron]\n",
        encoding="utf-8",
    )
    with pytest.raises(OverrideError) as erreur:
        load_overrides("demo", root=tmp_path)
    assert "reason" in str(erreur.value)


def test_un_arbitrage_avec_sa_raison_est_accepte(tmp_path: Path) -> None:
    """Sans cette moitié, le test précédent passerait sur un refus permanent."""
    (tmp_path / "demo.yml").write_text(
        "operations:\n"
        "  demo.v1.Thing.ThingAction:\n"
        "    parameters:\n"
        "      action:\n"
        "        choices: [poweron]\n"
        "        reason: seule l'alimentation est du Day-2\n",
        encoding="utf-8",
    )
    override = load_overrides("demo", root=tmp_path).get("demo.v1.Thing.ThingAction")
    assert override is not None
    assert override.parameters["action"].choices == ("poweron",)


def test_une_attente_sans_raison_est_refusee(tmp_path: Path) -> None:
    """Le contrat ne dit pas quel état suit une action : c'est une décision."""
    (tmp_path / "demo.yml").write_text(
        "operations:\n"
        "  demo.v1.Thing.ThingAction:\n"
        "    wait:\n"
        "      states:\n"
        "        poweron: running\n",
        encoding="utf-8",
    )
    with pytest.raises(OverrideError) as erreur:
        load_overrides("demo", root=tmp_path)
    assert "reason" in str(erreur.value)


def test_un_parametre_csv_sans_raison_est_refuse(tmp_path: Path) -> None:
    """Exposer autrement qu'à l'identique un paramètre du contrat est un arbitrage.

    Le chargeur refuse déjà `choices`, `required` et `expose` sans raison. `csv`
    change la forme sous laquelle un utilisateur écrit un filtre : il rejoint la
    liste plutôt que d'y échapper.
    """
    fichier = tmp_path / "instance.yml"
    fichier.write_text(
        "operations:\n"
        "  instance.v1.Server.ListServers:\n"
        "    parameters:\n"
        "      tags:\n"
        "        csv: true\n",
        encoding="utf-8",
    )
    with pytest.raises(OverrideError) as erreur:
        load_overrides("instance", root=tmp_path)
    assert "reason" in str(erreur.value)
