"""Ce que le compte rendu de génération écarte, et sous quelle raison.

Le compte rendu publiait six écarts sous une seule étiquette, « hors du
périmètre demandé ». C'est circulaire : ça dit qu'ils sont absents parce qu'on
ne les a pas demandés, sans dire pourquoi on ne les a pas demandés. Un lecteur
ne pouvait pas distinguer un module qu'on a **choisi** de ne pas produire d'un
module que le modèle **ne sait pas** produire.

Les six étaient tous du second genre, et chacun avait sa raison, documentée,
que `build_module_specs` produit déjà quand on l'appelle sans périmètre.

C'est la règle « rien ne disparaît en silence » appliquée à moitié : l'opération
ne disparaissait pas, sa raison si.
"""

from __future__ import annotations

from generator.ansible.collection import load_collection
from generator.ansible.models import build_module_specs
from generator.plan import build_plan

#: Ce que le modèle refuse, mesuré, produit par produit. Un témoin : ce compte
#: doit bouger quand le modèle change, jamais tout seul.
REFUS_ATTENDUS = {
    "instance": {
        "instance_ip_action",
        "instance_security_group_rule_info",
        "instance_security_group_rules",
        "instance_server_user_data",
        "instance_snapshot_action",
    },
    "lb": {"lb_load_balancer_action"},
}


def _sans_perimetre(produit: str) -> tuple[list[str], list[tuple[str, str]]]:
    plan = build_plan(produit, "v1")
    specs, ecartes = build_module_specs(plan, load_collection())
    return [spec.name for spec in specs], ecartes


def test_sans_perimetre_tout_ecart_porte_une_raison_du_modele() -> None:
    """Aucune tautologie : chaque raison dit ce que le modèle n'a pas su faire."""
    for produit in REFUS_ATTENDUS:
        _, ecartes = _sans_perimetre(produit)
        for nom, raison in ecartes:
            assert "périmètre" not in raison and "non demandé" not in raison, (
                f"{produit} écarte `{nom}` sous « {raison} », qui ne dit rien du module. "
                "Un périmètre par défaut déguise un refus du modèle en décision humaine."
            )


def test_les_refus_du_modele_sont_ceux_quon_a_mesures() -> None:
    """Le témoin. Un refus de plus est une régression, un de moins une victoire.

    Les deux méritent d'être vues : sans ce compte, le modèle peut se mettre à
    refuser un module de plus sans que rien ne l'annonce, et le compte rendu se
    lirait comme avant.
    """
    for produit, attendus in REFUS_ATTENDUS.items():
        _, ecartes = _sans_perimetre(produit)
        assert {nom for nom, _ in ecartes} == attendus


def test_le_perimetre_reste_disponible_pour_restreindre_volontairement() -> None:
    """Le cas voisin : `--module` doit encore marcher, et se nommer honnêtement.

    Le supprimer serait aller trop loin : restreindre une génération à un module
    reste utile quand on travaille sur lui.
    """
    plan = build_plan("lb", "v1")
    specs, ecartes = build_module_specs(plan, load_collection(), only=("lb_ip",))
    assert [spec.name for spec in specs] == ["lb_ip"]
    raisons = {raison for nom, raison in ecartes if nom == "lb_acl"}
    assert raisons == {"non demandé : `--module` restreint cette production"}
