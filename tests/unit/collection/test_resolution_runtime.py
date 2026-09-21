"""Résoudre un nom en identifiant, et refuser plutôt que de choisir.

Le défaut que ce lookup existe pour supprimer n'est pas l'absence de résultat,
c'est le **mauvais** résultat rendu sans un mot : `| first` sur trois candidats,
ou le filtre de l'API pris pour une sélection.

Ces tests ne touchent pas le réseau : l'API est remplacée par une fonction qui
rend des pages, ce qui permet de mesurer exactement ce que le runtime fait de la
réponse.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

    return scaleway


class _ApiFausse:
    """Une API qui rend ce qu'on lui a dit de rendre, et note ce qu'on lui demande."""

    def __init__(self, elements: list[dict[str, Any]]) -> None:
        self.elements = elements
        self.appels: list[dict[str, Any]] = []

    def request(
        self,
        operation: Any,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        path_values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.appels.append({"params": dict(params or {}), "path_values": dict(path_values or {})})
        # Une seule page : `total_count` la déclare complète, donc `paginate`
        # s'arrête sans avoir à deviner.
        return {operation.payload_field: self.elements, "total_count": len(self.elements)}


def _lookup(runtime: Any, **surcharges: Any) -> Any:
    operation = runtime.Operation(
        id="ListWidgets",
        method="GET",
        path="/labo/v1/zones/{zone}/widgets",
        path_params=("zone",),
        query_params=("name", "page", "page_size"),
        payload_field="widgets",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    )
    defauts: dict[str, Any] = {
        "parameter": "widget_id",
        "service": "labo",
        "schema": "labo.v1.Widget",
        "operation": operation,
        "scope": (),
        "filters_by_name": True,
    }
    defauts.update(surcharges)
    return runtime.ResourceLookup(**defauts)


# --- le verdict unique ------------------------------------------------------


def test_un_seul_nom_exact_rend_son_identifiant(runtime: Any) -> None:
    api = _ApiFausse([{"id": "uuid-1", "name": "web"}])

    trouve = runtime.resolve_resource_id(
        api, _lookup(runtime), name="web", values={"zone": "fr-par-1"}
    )

    assert trouve == "uuid-1"


# --- le piège que le contrat déclare lui-même -------------------------------


def test_un_prefixe_rendu_par_l_api_n_est_pas_une_correspondance(runtime: Any) -> None:
    """Le contrat le dit : « "server1" will return "server100" and "server1" ».

    L'API filtre par préfixe. Un lookup qui lui ferait confiance rendrait
    `server100` à qui demande `server1`, ce qui est le défaut de `| first`
    déplacé dans le plugin, en moins visible.
    """
    api = _ApiFausse([{"id": "uuid-100", "name": "server100"}])

    with pytest.raises(runtime.ResolutionError) as erreur:
        runtime.resolve_resource_id(
            api, _lookup(runtime), name="server1", values={"zone": "fr-par-1"}
        )

    assert "aucune ressource nommée exactement" in str(erreur.value)
    assert "server100" in str(erreur.value)


def test_la_comparaison_locale_s_execute_meme_quand_l_api_a_filtre(runtime: Any) -> None:
    """Sinon le chemin de comparaison n'existerait que pour un contrat futur."""
    api = _ApiFausse([{"id": "uuid-1", "name": "web"}, {"id": "uuid-2", "name": "web-preprod"}])

    trouve = runtime.resolve_resource_id(
        api, _lookup(runtime, filters_by_name=True), name="web", values={"zone": "fr-par-1"}
    )

    assert trouve == "uuid-1"
    assert api.appels[0]["params"]["name"] == "web"


def test_le_filtre_n_est_pas_envoye_quand_le_contrat_ne_le_declare_pas(runtime: Any) -> None:
    api = _ApiFausse([{"id": "uuid-1", "name": "web"}])

    runtime.resolve_resource_id(
        api, _lookup(runtime, filters_by_name=False), name="web", values={"zone": "fr-par-1"}
    )

    assert "name" not in api.appels[0]["params"]


class _ApiQuiFiltre(_ApiFausse):
    """Une API qui **applique** le filtre `name`, par préfixe, comme la vraie.

    `_ApiFausse` l'ignore, ce qui est le cas facile. Celle-ci reproduit ce que
    le contrat déclare et ce que l'émulateur fait : demander un nom absent rend
    une liste vide, donc il n'y a plus rien à citer à l'utilisateur.
    """

    def request(self, operation, **kwargs):
        params = kwargs.get("params") or {}
        filtre = params.get("name")
        retenus = (
            [e for e in self.elements if str(e.get("name", "")).startswith(filtre)]
            if filtre
            else list(self.elements)
        )
        self.appels.append(
            {"params": dict(params), "path_values": dict(kwargs.get("path_values") or {})}
        )
        return {operation.payload_field: retenus, "total_count": len(retenus)}


def test_un_refus_relit_sans_le_filtre_pour_avoir_de_quoi_citer(runtime) -> None:
    """Mesuré contre l'émulateur : le filtre retire ce que le message doit dire.

    Sans cette relecture, « aucune ressource nommée exactement X » était suivi
    de « la liste est vide », alors que la portée contenait des voisins. Le
    message perdait sa partie utile exactement quand elle sert.
    """
    api = _ApiQuiFiltre([{"id": "a", "name": "web-01"}, {"id": "b", "name": "web-02"}])

    with pytest.raises(runtime.ResolutionError) as erreur:
        runtime.resolve_resource_id(api, _lookup(runtime), name="base", values={"zone": "fr-par-1"})

    message = str(erreur.value)
    assert "web-01" in message and "web-02" in message
    assert "La liste est vide" not in message
    # Deux appels : le filtré qui décide, puis le complet qui explique.
    assert len(api.appels) == 2
    assert api.appels[0]["params"].get("name") == "base"
    assert "name" not in api.appels[1]["params"]


def test_une_portee_reellement_vide_le_dit_encore(runtime) -> None:
    """La relecture ne doit pas transformer un vide en silence."""
    api = _ApiQuiFiltre([])

    with pytest.raises(runtime.ResolutionError) as erreur:
        runtime.resolve_resource_id(api, _lookup(runtime), name="web", values={"zone": "fr-par-1"})

    assert "La liste est vide" in str(erreur.value)


def test_un_prefixe_rendu_par_une_api_qui_filtre_reste_un_refus(runtime) -> None:
    """Le cas exact du contrat : « server1 » rend « server100 » et rien d'autre."""
    api = _ApiQuiFiltre([{"id": "uuid-100", "name": "server100"}])

    with pytest.raises(runtime.ResolutionError) as erreur:
        runtime.resolve_resource_id(
            api, _lookup(runtime), name="server1", values={"zone": "fr-par-1"}
        )

    assert "aucune ressource nommée exactement" in str(erreur.value)
    assert "server100" in str(erreur.value)


# --- les deux refus ---------------------------------------------------------


def test_aucune_correspondance_cite_ce_qui_a_ete_trouve(runtime: Any) -> None:
    """La question de l'utilisateur à cet instant est « ai-je fait une faute »."""
    api = _ApiFausse([{"id": "a", "name": "web-01"}, {"id": "b", "name": "web-02"}])

    with pytest.raises(runtime.ResolutionError) as erreur:
        runtime.resolve_resource_id(api, _lookup(runtime), name="web", values={"zone": "fr-par-1"})

    message = str(erreur.value)
    assert "web-01" in message and "web-02" in message


def test_une_liste_vide_le_dit_plutot_que_de_citer_personne(runtime: Any) -> None:
    api = _ApiFausse([])

    with pytest.raises(runtime.ResolutionError) as erreur:
        runtime.resolve_resource_id(api, _lookup(runtime), name="web", values={"zone": "fr-par-1"})

    assert "La liste est vide" in str(erreur.value)


def test_deux_noms_identiques_sont_une_ambiguite_pas_un_choix(runtime: Any) -> None:
    """Scaleway n'impose pas l'unicité des noms : le cas n'est pas théorique."""
    api = _ApiFausse([{"id": "uuid-1", "name": "web"}, {"id": "uuid-2", "name": "web"}])

    with pytest.raises(runtime.ResolutionError) as erreur:
        runtime.resolve_resource_id(api, _lookup(runtime), name="web", values={"zone": "fr-par-1"})

    message = str(erreur.value)
    assert "2 ressources" in message
    # Le refus nomme les candidats : sans ça, il n'y a rien à trancher.
    assert "uuid-1" in message and "uuid-2" in message


def test_une_portee_manquante_est_refusee_avant_l_appel(runtime: Any) -> None:
    """Lister sans `lb_id` ne rendrait pas moins de résultats : ça rendrait 404."""
    api = _ApiFausse([{"id": "uuid-1", "name": "web"}])

    with pytest.raises(runtime.ResolutionError) as erreur:
        runtime.resolve_resource_id(
            api, _lookup(runtime, scope=("lb_id",)), name="web", values={"zone": "fr-par-1"}
        )

    assert "lb_id" in str(erreur.value)
    assert api.appels == [], "la portée se vérifie avant d'appeler, pas après"


def test_une_ressource_sans_identifiant_dans_la_reponse_est_dite(runtime: Any) -> None:
    """Le contrat en déclare un ; si l'API n'en rend pas, on ne rend pas None."""
    api = _ApiFausse([{"name": "web"}])

    with pytest.raises(runtime.ResolutionError) as erreur:
        runtime.resolve_resource_id(api, _lookup(runtime), name="web", values={"zone": "fr-par-1"})

    assert "ne porte pas d'identifiant" in str(erreur.value)


# --- ce que la portée fait du chemin ---------------------------------------


def test_la_portee_est_transmise_au_rendu_du_chemin(runtime: Any) -> None:
    api = _ApiFausse([{"id": "uuid-1", "name": "web"}])

    runtime.resolve_resource_id(
        api,
        _lookup(runtime, scope=("lb_id",)),
        name="web",
        values={"zone": "fr-par-1", "lb_id": "uuid-lb"},
    )

    assert api.appels[0]["path_values"] == {"zone": "fr-par-1", "lb_id": "uuid-lb"}


# --- la table générée -------------------------------------------------------


def test_la_table_generee_s_importe_et_porte_ce_que_les_contrats_declarent(
    collection_root: Path,
) -> None:
    """Un fichier qui s'analyse syntaxiquement n'est pas un fichier qui s'exécute."""
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import resolution

    # `private_network_id`, `vpc_id` et `vpc_connector_id` sont arrivés avec le
    # lot réseau, et ce n'est pas un détail de table : l'inventaire dynamique
    # traversait déjà ces deux APIs, mais rien ne permettait de désigner un VPC
    # ou un réseau privé **par son nom** dans un playbook. Il fallait un UUID.
    assert set(resolution.RESOLUTIONS) == {
        "backend_id",
        "certificate_id",
        "cluster_id",
        "frontend_id",
        "image_id",
        "lb_id",
        "node_id",
        "placement_group_id",
        "pool_id",
        "private_network_id",
        "security_group_id",
        "server_id",
        "snapshot_id",
        "subscriber_id",
        "volume_id",
        "vpc_connector_id",
        "vpc_id",
    }
    backend = resolution.RESOLUTIONS["backend_id"]
    assert backend.operation.id == "ListBackends"
    assert backend.scope == ("lb_id",)
    assert "lb_id" in backend.operation.path_params


def test_les_refus_de_la_table_portent_leur_raison(collection_root: Path) -> None:
    """Un refus muet enverrait chercher une faute de frappe dans un nom correct."""
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import resolution

    assert set(resolution.UNRESOLVABLE) == {
        "acl_id",
        "ip_id",
        "private_nic_id",
        "route_id",
        "rule_id",
        "security_group_rule_id",
    }
    # `acl_id` est refusé pour une autre raison que les autres : le Load
    # Balancer le résout et Kubernetes ne le peut pas, donc le nom désigne deux
    # choses et laquelle n'est pas décidable.
    #
    # **Trois causes et non deux, depuis le lot réseau.** Cette boucle exigeait
    # « ne porte pas de champ name » de tout refus sauf `acl_id`, et `rule_id`
    # l'a démentie : la règle d'entrée d'un VPC n'est rendue par aucune
    # opération de liste, ce qui est un obstacle différent d'un schéma sans
    # `name`. Les deux se disent, et le contrôle porte sur ce qu'un refus doit
    # être - intelligible - plutôt que sur l'unique cause qu'on connaissait.
    CAUSES = (
        "ne porte pas de champ name",
        "n'est rendu par une opération de liste",
    )
    for nom, raison in resolution.UNRESOLVABLE.items():
        if nom == "acl_id":
            assert "n'est pas décidable depuis le nom" in raison
            continue  # sa raison est double, et l'autre moitié est testée à part
        assert any(cause in raison for cause in CAUSES), (
            f"`{nom}` est refusé sans nommer de cause connue : {raison!r}. "
            "Un refus muet enverrait chercher une faute de frappe dans un nom correct."
        )


def test_un_nom_que_deux_produits_revendiquent_ne_se_resout_pas() -> None:
    """Rendre l'identifiant du mauvais produit est pire que ne rien rendre.

    `acl_id` existe dans le Load Balancer et dans Kubernetes, et ce ne sont pas
    les mêmes ACL. Le premier le résout, le second ne le peut pas faute de champ
    `name` : la résolution du premier restait donc seule en piste, et quelqu'un
    qui écrit `acl_id` en pensant à une règle de cluster obtenait une règle de
    load balancer sans que rien ne le dise.
    """
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import resolution

    assert "acl_id" not in resolution.RESOLUTIONS
    assert "acl_id" in resolution.UNRESOLVABLE
    # Les deux raisons sont publiées : aucune ne vaut pour l'autre produit.
    assert "opération de liste" in resolution.UNRESOLVABLE["acl_id"]
    assert "lb le résout" in resolution.UNRESOLVABLE["acl_id"]


def test_un_nom_ambigu_se_resout_quand_on_dit_le_produit() -> None:
    """Refusé sauf si l'on désambiguïse, et non refusé tout court.

    Retirer la possibilité de résoudre une ACL de load balancer par son nom
    parce qu'un autre produit porte le même nom de paramètre punirait
    l'utilisateur pour notre nommage.
    """
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import resolution

    assert "acl_id" in resolution.AMBIGUOUS
    assert set(resolution.AMBIGUOUS["acl_id"]) == {"lb"}
    lookup = resolution.AMBIGUOUS["acl_id"]["lb"]
    assert lookup.operation.id == "ListAcls"
    assert lookup.scope == ("frontend_id",)


def test_le_refus_dun_nom_ambigu_dit_comment_le_lever() -> None:
    """Un refus qui ne dit pas quoi faire ensuite envoie chercher au hasard."""
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import resolution

    assert "service=lb" in resolution.UNRESOLVABLE["acl_id"]
