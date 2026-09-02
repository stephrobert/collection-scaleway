"""Les groupes natifs, et l'assainissement de leurs noms.

Le cas qui motive ce module est `production/web` : le plugin officiel le laisse
passer tel quel, et Ansible se retrouve avec un nom de groupe invalide.
"""

from __future__ import annotations

import pytest

from ansible_collections.local.scaleway.plugins.module_utils.inventory.groups import (
    AXES,
    group_names,
    sanitize_group_name,
)
from ansible_collections.local.scaleway.plugins.module_utils.inventory.models import (
    InventoryHost,
    NetworkAttachment,
)


@pytest.mark.parametrize(
    ("brut", "attendu"),
    [
        ("web", "web"),
        ("web-front", "web_front"),
        ("web front", "web_front"),
        ("env:prod", "env_prod"),
        ("production/web", "production_web"),
        ("a...b", "a_b"),
        ("-bordure-", "bordure"),
        ("2024", "_2024"),
        ("!!!", "inconnu"),
        ("", "inconnu"),
    ],
)
def test_un_nom_de_groupe_devient_valide_pour_ansible(brut: str, attendu: str) -> None:
    assert sanitize_group_name(brut) == attendu


def test_les_accents_sont_deplies_pas_supprimes() -> None:
    """Deplier garde le nom lisible pour qui ecrit le playbook."""
    assert sanitize_group_name("pré-prod") == "pre_prod"


@pytest.mark.parametrize("brut", ["production/web", "pré-prod", "2024", "env:prod", "!!!"])
def test_un_nom_assaini_est_un_point_fixe_pour_ansible(brut: str) -> None:
    """Le contrôle qui mesure vraiment quelque chose.

    `Group("production/web")` ne lève pas : Ansible **accepte** le nom et se
    contente d'un avertissement. Un test qui construit un `Group` ne prouverait
    donc rien du tout. La référence est `to_safe_group_name`, la fonction
    qu'Ansible applique lui-même : un nom assaini par nos soins doit en sortir
    inchangé, là où le nom brut, lui, en sort modifié.
    """
    from ansible.inventory.group import to_safe_group_name

    assaini = sanitize_group_name(brut)
    assert to_safe_group_name(assaini, force=True, silent=True) == assaini
    assert to_safe_group_name(brut, force=True, silent=True) != brut


def test_un_nom_commencant_par_un_chiffre_garde_ses_chiffres() -> None:
    """Ansible remplace le chiffre de tête (`2024` -> `_024`), et perd un caractère.

    Le préfixer conserve l'information, et le résultat reste un point fixe pour
    Ansible : `_2024` en ressort inchangé.
    """
    from ansible.inventory.group import to_safe_group_name

    assert sanitize_group_name("2024") == "_2024"
    assert to_safe_group_name("2024", force=True, silent=True) == "_024"


def test_chaque_axe_produit_son_groupe() -> None:
    host = InventoryHost(
        id="i-1",
        product="instance",
        project_id="proj-1",
        region="fr-par",
        zone="fr-par-1",
        state="running",
        tags=("env=prod",),
        private_networks=(NetworkAttachment("pn-1", "backend", "vpc-1", "socle"),),
    )
    noms = group_names(host, AXES)
    assert noms == (
        "scw_private_network_backend",
        "scw_product_instance",
        "scw_project_proj_1",
        "scw_region_fr_par",
        "scw_state_running",
        "scw_tag_env_prod",
        "scw_vpc_socle",
        "scw_zone_fr_par_1",
    )


def test_le_produit_est_un_axe_pas_un_tag_injecte() -> None:
    """Le plugin officiel injecte le produit dans les tags, et fausse le filtrage."""
    host = InventoryHost(id="i-1", product="instance", tags=("env=prod",))
    assert host.tags == ("env=prod",)
    assert "scw_product_instance" in group_names(host, ("product", "tags"))


def test_un_champ_absent_ne_cree_pas_de_groupe_vide() -> None:
    host = InventoryHost(id="i-1", product="instance")
    assert group_names(host, AXES) == ("scw_product_instance",)


def test_les_groupes_sont_tries_et_dedoublonnes() -> None:
    """Deux exécutions doivent produire le même inventaire, octet pour octet."""
    host = InventoryHost(id="i-1", product="instance", tags=("a", "a", "b"))
    assert group_names(host, ("tags", "tags")) == ("scw_tag_a", "scw_tag_b")
