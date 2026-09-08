"""Ce que le contrat décide seul de la comparaison, en regardant les deux côtés.

ADR-009 dit que le type décide ce qu'il peut et qu'un override décide le reste.
Ce fichier mesure le cas que le type **seul** ne peut pas trancher : l'écriture
prend un tableau, la lecture rend un tableau d'objets, et comparer les deux
directement rend « différent » à tous les coups.
"""

from __future__ import annotations

from pathlib import Path

from generator.ansible.collection import load_collection
from generator.ansible.introductions import load_introductions
from generator.ansible.models import build_module_specs
from generator.plan import build_plan

ROOT = Path(__file__).resolve().parents[3]
SPECS = ROOT / "specs" / "scaleway"


def _strategies(produit: str, module: str) -> dict[str, str]:
    plan = build_plan(produit, "v1", spec_root=SPECS)
    specs, _ = build_module_specs(plan, load_collection(), introductions=load_introductions())
    spec = next(item for item in specs if item.name == module)
    return dict(spec.comparisons)


def test_une_liste_relue_en_objets_se_compare_par_ses_identifiants() -> None:
    """Mesuré sur le contrat Instance, des deux côtés.

    `UpdateServer` déclare `public_ips` et `private_nics` comme des tableaux ;
    `Server` les rend comme des tableaux d'objets. Sans cette stratégie, les
    deux modules réécrivaient à chaque exécution.
    """
    strategies = _strategies("instance", "instance_server")
    assert strategies["public_ips"] == "id_list"
    assert strategies["private_nics"] == "id_list"


def test_une_liste_de_chaines_des_deux_cotes_reste_comparee_dans_lordre() -> None:
    """Le contre-exemple, et il est dans le même module.

    `tags` est un tableau de chaînes à l'écriture comme à la lecture : rien à
    projeter, et le repli d'ADR-009 reste le bon.
    """
    assert _strategies("instance", "instance_server")["tags"] == "ordered_list"


def test_une_liste_didentifiants_relue_telle_quelle_nest_pas_projetee() -> None:
    """`Frontend.certificate_ids` est un tableau de chaînes des deux côtés.

    Le nom suggère des références, et le contrat dit que l'API les rend comme
    la requête les envoie. Décider sur le nom aurait projeté une liste qui n'en
    a pas besoin.
    """
    assert _strategies("lb", "lb_frontend")["certificate_ids"] == "ordered_list"


def test_aucun_autre_parametre_gere_ne_tombe_dans_ce_cas() -> None:
    """L'étendue du défaut, mesurée sur les deux produits livrés.

    Ce test dit où en est le dépôt. S'il rougit, c'est qu'un contrat en amont a
    changé de forme, et le diff dira lequel.
    """
    trouves = []
    for produit in ("instance", "lb"):
        plan = build_plan(produit, "v1", spec_root=SPECS)
        specs, _ = build_module_specs(plan, load_collection(), introductions=load_introductions())
        for spec in specs:
            trouves.extend(
                f"{spec.name}.{nom}"
                for nom, strategie in spec.comparisons
                if strategie == "id_list"
            )
    assert sorted(trouves) == ["instance_server.private_nics", "instance_server.public_ips"]
