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


def test_un_override_de_parametre_qui_ne_designe_rien_est_orphelin(
    tmp_path: Path, widget_service: ApiService
) -> None:
    """Une faute de frappe dans `parameters` produisait un override inerte.

    Toutes les lectures d'`override.parameters` sont des recherches par nom :
    `tgas: {comparison: set}` ne changeait rien, ne rougissait nulle part, et
    la règle 2 du dépôt n'était tenue que pour la clé de l'opération.
    """
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.UpdateWidget:
    parameters:
      tgas:
        comparison: set
        reason: faute de frappe volontaire, pour le test
""",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))
    assert plan.orphan_overrides == (
        "widget.v1.Widget.UpdateWidget.parameters.tgas : aucun paramètre de ce nom sur l'opération",
    )


def test_un_override_de_parametre_qui_designe_un_parametre_nest_pas_orphelin(
    tmp_path: Path, widget_service: ApiService
) -> None:
    """Le contre-exemple, sans lequel le test précédent passerait aussi sur un
    contrôle qui déclarerait tout orphelin."""
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.UpdateWidget:
    parameters:
      tags:
        comparison: set
        reason: les tags sont un ensemble
""",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))
    assert plan.orphan_overrides == ()


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


def test_un_csv_hors_dun_filtre_de_requete_est_inerte(
    tmp_path: Path, widget_service: ApiService
) -> None:
    """`csv` ne veut dire quelque chose que sur un filtre de requête.

    Le runtime joint les valeurs par des virgules au moment de construire la
    chaîne de requête, et nulle part ailleurs. Posé sur un champ de corps,
    l'override était accepté et silencieusement inerte : le module exposait une
    liste que rien ne joindrait, et l'utilisateur recevait une erreur de l'API
    sur une option que la page lui promettait.

    Reproduit dans #128 avant d'être corrigé.
    """
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.UpdateWidget:
    parameters:
      tags:
        csv: true
        reason: essai, sur un champ de corps
""",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))

    assert plan.orphan_overrides == (
        "widget.v1.Widget.UpdateWidget.parameters.tags : `csv` sur un paramètre body, "
        "alors qu'il ne s'applique qu'à un filtre de requête",
    )


def test_un_csv_sur_un_filtre_de_requete_reste_accepte(
    tmp_path: Path, widget_service: ApiService
) -> None:
    """Le contre-exemple, sans lequel le refus pourrait tout refuser.

    C'est la forme que les overrides réels emploient, et la rendre orpheline
    ferait échouer `report --strict` sur ce que le dépôt fait déjà.
    """
    _write(
        tmp_path,
        """
operations:
  widget.v1.Widget.ListWidgets:
    parameters:
      state:
        csv: true
        reason: le contrat décrit la virgule comme séparateur
""",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))

    assert plan.orphan_overrides == ()
