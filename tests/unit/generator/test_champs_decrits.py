"""Un champ publié dit quelque chose, ou la release est refusée.

La 0.2.0 est partie sur Galaxy avec **cent** « Not documented by the Scaleway
API contract. » dans ses blocs `RETURN`. Le générateur venait de gagner le droit
de publier les champs des ressources, et la porte documentaire ne regardait que
les clés de premier niveau : la surface publiée s'était élargie, la mesure non.

Quatre étages traitent le trou, du plus sûr au moins informatif, et le dernier
bloque la publication :

    la description du champ, au contrat
    une décision humaine, avec sa raison
    ce que le contrat en dit ailleurs, quand il ne le dit qu'une fois
    une reformulation qui ne redit que le nom
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.collection import Collection
from generator.ansible.models import UNDOCUMENTED, AnsibleModuleSpec, build_module_specs
from generator.overrides.loader import OverrideError, load_overrides
from generator.plan import ProductPlan, plan_service


def _specs(plan: ProductPlan, collection: Collection) -> dict[str, AnsibleModuleSpec]:
    specs, _ = build_module_specs(plan, collection)
    return {spec.name: spec for spec in specs}


def _champs(spec: AnsibleModuleSpec) -> dict[str, tuple[str, ...]]:
    return {champ.name: champ.description for retour in spec.returns for champ in retour.contains}


def test_aucun_champ_publie_ne_porte_le_repli(instance_plan, lb_plan, collection) -> None:
    """C'est le défaut que la 0.2.0 a publié cent fois."""
    fautifs = [
        f"{nom}.{champ}"
        for plan in (instance_plan, lb_plan)
        for nom, spec in _specs(plan, collection).items()
        for retour in spec.returns
        for champ in retour.contains
        if UNDOCUMENTED in champ.description
    ]
    assert fautifs == [], f"{len(fautifs)} champ(s) publiés sans description : {fautifs[:8]}"


def test_le_contrat_decrit_le_champ_quand_il_le_decrit(instance_plan, collection) -> None:
    """Le premier étage, et il doit rester le premier."""
    champs = _champs(_specs(instance_plan, collection)["instance_server_info"])
    assert champs["name"] == ("Instance name.",)


def test_ce_que_le_contrat_dit_ailleurs_sert_quand_il_ne_le_dit_quune_fois(
    instance_service,
) -> None:
    """`protocol` n'est décrit qu'une fois dans instance.v1 : rien à trancher.

    `name` y est décrit treize fois, « Instance name. », « Volume name. »,
    « Snapshot name. » : aucune ne vaut pour les autres ressources, et le
    glossaire n'en retient donc aucune. C'est l'unicité qui rend la reprise
    sûre, et c'est pour ça qu'elle est la condition.
    """
    assert instance_service.described("protocol") == "Protocol family this rule applies to."
    assert instance_service.described("name") is None


def test_une_reformulation_ne_dit_que_le_nom(instance_plan, collection) -> None:
    """« Count of volumes. » et non « Number of volumes in the selected zone ».

    La seconde serait plus utile et serait une invention : le contrat ne dit ni
    la zone ni le périmètre, et un lecteur bâtirait dessus.
    """
    champs = _champs(_specs(instance_plan, collection)["instance_dashboard_info"])
    assert champs["volumes_count"] == ("Count of volumes.",)
    assert champs["security_groups_count"] == ("Count of security groups.",)


def test_une_decision_humaine_passe_avant_les_mecanismes(instance_plan, collection) -> None:
    """Les champs que le contrat ne décrit nulle part portent une phrase décidée.

    Les assertions ci-dessous les nomment un par un : une liste dit lesquels,
    un compte ne dirait que combien.
    """
    champs = _champs(_specs(instance_plan, collection)["instance_image_info"])
    assert champs["public"] == ("Whether the image is public.",)
    assert champs["from_server"] == ("Server the image comes from.",)


def test_un_champ_deprecie_le_dit(instance_plan, collection) -> None:
    """L'information existait pour les options et se perdait pour les retours.

    Un lecteur bâtissait sur `default_bootscript` sans savoir que le contrat le
    déclare déprécié.
    """
    champs = _champs(_specs(instance_plan, collection)["instance_image_info"])
    assert any("Deprecated" in ligne for ligne in champs["default_bootscript"])


def test_une_description_de_retour_sans_raison_est_refusee(tmp_path: Path) -> None:
    """Elle sortira sur Galaxy sous le nom de la collection."""
    (tmp_path / "widget.yml").write_text(
        """
returns:
  demo.Widget:
    couleur:
      description: Colour of the widget.
""",
        encoding="utf-8",
    )
    with pytest.raises(OverrideError, match="sans `reason`"):
        load_overrides("widget", root=tmp_path)


def test_un_override_de_retour_qui_ne_designe_rien_est_orphelin(
    tmp_path: Path, widget_service
) -> None:
    """Une ressource ou un champ que le contrat ne rend pas."""
    (tmp_path / "widget.yml").write_text(
        """
returns:
  scaleway.disparu.v1.Widget:
    couleur:
      description: Colour of the widget.
      reason: la ressource a disparu du contrat
""",
        encoding="utf-8",
    )
    plan = plan_service(widget_service, load_overrides("widget", root=tmp_path))
    assert any("scaleway.disparu" in orphelin for orphelin in plan.orphan_overrides)


def test_une_reformulation_met_les_abreviations_en_capitales(instance_plan, collection) -> None:
    """`ips_count` sortait « Count of ips. » sous une phrase courte disant « Instance IPs ».

    La table des acronymes n'était appliquée qu'au nom du schéma, pas au nom du
    champ : deux moitiés de la même phrase, une seule passée par la table.
    """
    champs = _champs(_specs(instance_plan, collection)["instance_dashboard_info"])
    assert champs["ips_count"] == ("Count of IPs.",)
    assert champs["private_nics_count"] == ("Count of private NICs.",)
