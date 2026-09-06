"""Un exemple par chose que le module sait faire, pas une par opération HTTP.

Les préambules disent déjà ce qui distingue les trois classes. Les tâches, elles,
montraient toutes la même chose : les paramètres obligatoires, une fois. Ce qui
manquait est ce qu'un opérateur vient chercher sur la page.
"""

from __future__ import annotations

import re
from pathlib import Path

from generator.ansible.collection import Collection
from generator.ansible.models import AnsibleModuleSpec, build_module_specs
from generator.plan import ProductPlan
from generator.renderer.modules import render_module


def _specs(plan: ProductPlan, collection: Collection) -> dict[str, AnsibleModuleSpec]:
    specs, _ = build_module_specs(plan, collection)
    return {spec.name: spec for spec in specs}


def test_un_module_dinformation_montre_comment_filtrer(instance_plan, collection) -> None:
    """Lister un parc entier pour en garder trois machines n'est pas une réponse.

    Les filtres sont la moitié des options d'un module d'information, et aucune
    tâche n'en montrait un seul.
    """
    specs = _specs(instance_plan, collection)
    tache = next(t for t in specs["instance_server_info"].examples if t.name.startswith("Filter"))
    assert "tags" in tache.parameters
    assert tache.parameters["tags"] == ["production"]


def test_un_tri_nest_pas_un_filtre(lb_plan, collection) -> None:
    """`order_by` trie, et le repli l'avait retenu faute d'autre option.

    L'exemple s'appelait « filtered by order_by » sur
    `lb_load_balancer_private_network_info`, et il montrait comment ordonner une
    liste à quelqu'un qui cherchait comment la réduire.
    """
    specs = _specs(lb_plan, collection)
    fautifs = [
        f"{nom} : {tache.name}"
        for nom, spec in specs.items()
        for tache in spec.examples
        if "order_by" in tache.parameters
    ]
    assert fautifs == [], f"un tri présenté comme un filtre : {fautifs}"


def test_un_module_de_gestion_montre_le_mode_simulation(instance_plan, collection) -> None:
    """Son préambule en parle depuis toujours, aucune tâche ne le montrait.

    C'est pourtant ce qu'on fait avant d'écrire sur un parc qu'on ne possède pas
    seul, et `--diff` est ce qui rend la comparaison lisible plutôt que de
    rendre un `changed` sans contenu.
    """
    specs = _specs(instance_plan, collection)
    tache = next(t for t in specs["instance_server"].examples if t.keywords)
    assert dict(tache.keywords) == {"check_mode": True, "diff": True}
    rendu = tache.to_documentation()
    assert rendu["check_mode"] is True
    assert rendu["diff"] is True


def test_lexemple_de_simulation_porte_les_memes_parametres(instance_plan, collection) -> None:
    """Une simulation qui n'écrit pas la même chose ne simule rien."""
    specs = _specs(instance_plan, collection)
    ecriture, simulation = specs["instance_server"].examples[:2]
    assert simulation.parameters == ecriture.parameters


def test_les_taches_dexemple_se_nomment_comme_la_page(instance_plan, collection) -> None:
    """« Update a Scaleway instance server » venait du nom du module.

    La phrase courte de la même page dit « Manage a Scaleway Instance server » :
    deux façons de nommer la même ressource, à trois lignes d'écart.
    """
    specs = _specs(instance_plan, collection)
    assert specs["instance_server"].examples[0].name == "Update a Scaleway Instance server"


def test_le_rendu_nemet_jamais_dancre_yaml(instance_plan, collection) -> None:
    """La garde vit dans le sérialiseur, donc elle s'éprouve sur le rendu.

    Le test suivant lit les fichiers du dépôt : il resterait vert si le
    sérialiseur se remettait à factoriser, puisque les fichiers commités ne
    portent déjà plus d'ancre. Il faut rendre pour que la garde morde.
    """
    spec = _specs(instance_plan, collection)["instance_server_private_nic"]
    rendu = render_module(spec, source="specs/scaleway/instance.v1.yml")
    assert "&id" not in rendu and "*id" not in rendu, rendu


def test_aucun_exemple_publie_ne_porte_dancre_yaml() -> None:
    """Une ancre est du YAML valide qu'on ne peut pas copier tâche par tâche.

    La tâche d'écriture et sa simulation partagent leurs paramètres : `safe_dump`
    écrivait `tags: &id001` à la première et `tags: *id001` à la seconde, où la
    seconde ne dit plus ce qu'elle envoie. Le golden l'a montré à la ligne près.
    """
    modules = Path(__file__).resolve().parents[3] / (
        "ansible_collections/stephrobert/scaleway/plugins/modules"
    )
    fautifs = [
        chemin.name
        for chemin in sorted(modules.glob("*.py"))
        if re.search(r": [&*]id\d+", chemin.read_text(encoding="utf-8"))
    ]
    assert fautifs == [], f"ancres YAML publiées dans : {fautifs}"
