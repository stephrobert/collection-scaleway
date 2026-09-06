"""Le module se nomme comme Scaleway nomme son produit, et une fois seulement.

Un lecteur qui cherche les modules de Load Balancer ne tape pas « Lb » : c'est
le slug de `products.txt`, un identifiant de fichier. Le contrat, lui, porte son
nom publié, celui de la console et de la facturation.

Ces tests portent sur les contrats réels et non sur celui du laboratoire, et
c'est une exception assumée. Le défaut naît de la **rencontre** entre un slug
d'index et un titre publié qui divergent, et entre une ressource et un produit
qui portent le même nom : les deux se mesurent sur `lb`, et se fabriqueraient
sur un contrat de laboratoire. Un test qui les inventerait ne dirait rien du
fichier publié, qui est ce qu'on cherche à protéger ici.
"""

from __future__ import annotations

from generator.ansible.collection import Collection
from generator.ansible.models import AnsibleModuleSpec, build_module_specs
from generator.plan import ProductPlan


def _specs(plan: ProductPlan, collection: Collection) -> dict[str, AnsibleModuleSpec]:
    specs, _ = build_module_specs(plan, collection)
    return {spec.name: spec for spec in specs}


def test_le_produit_se_nomme_comme_le_contrat_le_publie(lb_plan, collection) -> None:
    """`lb` est le slug d'index ; « Load Balancer API » est ce que le contrat dit.

    « Manage a Scaleway Lb backend » sortait de `service.name.capitalize()`, un
    nom que Scaleway n'emploie nulle part chez lui.
    """
    specs = _specs(lb_plan, collection)
    fautifs = [nom for nom, spec in specs.items() if "Lb " in spec.short_description]
    assert fautifs == [], f"modules nommés avec le slug : {fautifs}"


def test_le_produit_ne_se_repete_pas_dans_la_ressource(lb_plan, collection) -> None:
    """La ressource de `/lbs/{lb_id}` est `load_balancer`, et le produit aussi.

    Collés, ils donnaient « Manage a Scaleway Load Balancer load balancer » et
    « Gather information about Scaleway Load Balancer load balancer stats ».
    """
    specs = _specs(lb_plan, collection)
    fautifs = [
        nom
        for nom, spec in specs.items()
        if "load balancer"
        in spec.short_description.casefold().replace("scaleway load balancer", "", 1)
    ]
    assert fautifs == [], f"produit répété : {fautifs}"


def test_la_phrase_courte_dun_module_de_lecture_est_au_pluriel(lb_plan, collection) -> None:
    """Un module d'information rend une liste : « Load Balancers », pas « Load Balancer »."""
    specs = _specs(lb_plan, collection)
    assert (
        specs["lb_load_balancer_info"].short_description
        == "Gather information about Scaleway Load Balancers"
    )


def test_la_couche_http_ne_sort_pas_dans_la_documentation(lb_plan, collection) -> None:
    """« You must set all parameters » est vrai de l'API et faux du module.

    Le module lit la ressource avant d'écrire et remplit lui-même ce qu'on ne
    lui donne pas ; la phrase suivante, que le générateur écrit, le dit. Publier
    les deux publie une contradiction, et c'est celle du contrat qui vient en
    premier.
    """
    specs = _specs(lb_plan, collection)
    fautifs = [
        nom
        for nom, spec in specs.items()
        for ligne in spec.description
        if "must set all parameters" in ligne.lower() or "PUT and not PATCH" in ligne
    ]
    assert fautifs == [], f"la couche HTTP fuit dans : {fautifs}"


def test_le_reste_de_la_phrase_du_contrat_sort_mot_pour_mot(lb_plan, collection) -> None:
    """Retirer la fuite est un nettoyage, pas une réécriture.

    Sans ce test, remplacer toute la description par une phrase du générateur
    passerait le test précédent tout en perdant ce que le contrat dit.
    """
    specs = _specs(lb_plan, collection)
    premiere = specs["lb_load_balancer"].description[0]
    assert premiere.startswith("Update the parameters of an existing Load Balancer")


def test_un_exemple_ne_porte_pas_didentifiant_doperation(instance_plan, collection) -> None:
    """`Run GetDashboard` nomme l'appel HTTP, pas ce que la tâche fait.

    `GetDashboard` est la seule opération d'Instance v1 sans `summary` : c'est
    elle qui a montré le repli.
    """
    specs = _specs(instance_plan, collection)
    fautifs = [
        f"{nom} : {tache.name}"
        for nom, spec in specs.items()
        for tache in spec.examples
        if tache.name.startswith("Run ")
    ]
    assert fautifs == [], f"exemples nommés par le contrat : {fautifs}"
    assert specs["instance_dashboard_info"].examples[0].name == "Read a Scaleway Instance dashboard"
