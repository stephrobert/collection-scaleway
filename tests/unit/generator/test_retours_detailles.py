"""Le RETURN dit ce qu'il y a dans la ressource, pas seulement son nom.

Un module d'information publiait :

    server:
      description: Get the details of a specified Instance.
      returned: when I(server_id) is provided
      type: dict

Un lecteur de la page Galaxy ne savait pas ce qu'il pouvait lire dans
`result.server`. Il fallait appeler le module, ou aller au contrat OpenAPI, ce
que la page publiée doit précisément éviter.

Le contrat le disait pourtant : `scaleway.instance.v1.Server` déclare 36 champs,
dont 34 décrits. La connaissance existait et s'arrêtait au parser.
"""

from __future__ import annotations

import pytest

from generator.ansible.collection import Collection
from generator.ansible.models import AnsibleModuleSpec, build_module_specs
from generator.ir.enums import ApiType
from generator.plan import ProductPlan


def _specs(plan: ProductPlan, collection: Collection) -> dict[str, AnsibleModuleSpec]:
    specs, _ = build_module_specs(plan, collection)
    return {spec.name: spec for spec in specs}


def test_lir_porte_les_champs_des_ressources_rendues(instance_service) -> None:
    """Une fois par schéma, et seulement pour ce qu'une réponse désigne.

    Recopier les deux cents schémas du contrat ferait un IR que personne ne
    relit en diff, et le golden est ce qui rend la dérive visible.
    """
    noms = {objet.name for objet in instance_service.objects}
    assert "scaleway.instance.v1.Server" in noms
    assert len(noms) < 30, f"{len(noms)} ressources : le filtre par réponse ne filtre plus"

    serveur = instance_service.object("scaleway.instance.v1.Server")
    assert serveur is not None
    champs = {champ.name: champ for champ in serveur.fields}
    assert champs["id"].description == "Instance unique ID."
    assert champs["tags"].type is ApiType.ARRAY
    assert champs["tags"].item_type is ApiType.STRING


def test_une_ressource_inconnue_ne_produit_aucun_champ(instance_service) -> None:
    """Un `contains` inventé décrirait une réponse que personne n'a lue."""
    assert instance_service.object("scaleway.instance.v1.Inexistant") is None
    assert instance_service.object(None) is None


def test_le_retour_dun_module_dinformation_liste_ses_champs(instance_plan, collection) -> None:
    specs = _specs(instance_plan, collection)
    serveur = next(r for r in specs["instance_server_info"].returns if r.name == "server")
    champs = {champ.name for champ in serveur.contains}
    assert {"id", "name", "state", "commercial_type"} <= champs


def test_le_retour_dun_module_de_gestion_liste_ses_champs(instance_plan, collection) -> None:
    """La ressource écrite est celle qu'on relit : mêmes champs, même schéma."""
    specs = _specs(instance_plan, collection)
    retour = specs["instance_server"].returns[0]
    assert {champ.name for champ in retour.contains} >= {"id", "name", "state"}


def test_le_retour_dune_action_liste_les_champs_de_sa_charge_utile(
    instance_plan, collection
) -> None:
    specs = _specs(instance_plan, collection)
    tache = next(r for r in specs["instance_server_action"].returns if r.name == "task")
    assert {champ.name for champ in tache.contains} >= {"id", "status", "progress"}


def test_une_cle_que_le_generateur_invente_na_pas_de_champs(instance_plan, collection) -> None:
    """`action` et `state` sont des chaînes que le module compose lui-même.

    Leur donner un `contains` supposerait un schéma que le contrat ne porte pas
    pour elles.
    """
    specs = _specs(instance_plan, collection)
    action = next(r for r in specs["instance_server_action"].returns if r.name == "action")
    assert action.contains == ()


def test_le_repli_result_porte_aussi_ses_champs(lb_plan, collection) -> None:
    """`GetAcl` répond par la ressource, pas par une enveloppe.

    Ces modules passent par le repli `result`, qui ne transmettait pas le schéma
    et publiait donc une clé sans contenu alors que le contrat le déclarait.
    """
    specs = _specs(lb_plan, collection)
    retour = specs["lb_acl_info"].returns[0]
    assert retour.name == "result"
    assert {champ.name for champ in retour.contains} >= {"id", "name", "index"}


def test_un_champ_sans_description_sort_quand_meme(instance_plan, collection) -> None:
    """Sa présence est déjà l'information que le lecteur vient chercher."""
    specs = _specs(instance_plan, collection)
    tous = [
        champ for spec in specs.values() for retour in spec.returns for champ in retour.contains
    ]
    assert tous, "aucun champ rendu : la mesure ne mesure plus rien"
    assert all(champ.description for champ in tous)


@pytest.mark.parametrize("module", ["instance_server_info", "instance_server", "lb_backend"])
def test_le_contains_se_rend_en_documentation_ansible(
    module: str, instance_plan, lb_plan, collection
) -> None:
    """`ansible-test sanity` juge la forme ; ce test juge qu'elle est remplie."""
    specs = _specs(instance_plan, collection) | _specs(lb_plan, collection)
    retour = next(r for r in specs[module].returns if r.contains)
    rendu = retour.to_documentation()
    assert "contains" in rendu
    premier = next(iter(rendu["contains"].values()))
    assert set(premier) >= {"description", "returned", "type"}
