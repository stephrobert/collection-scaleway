# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Normaliser une ressource, pour qu'une règle cesse de connaître un produit.

Une politique d'audit dont les règles lisent `modification_date` et `public_ips`
lit un objet Instance. Le jour où Elastic Metal aura des modules, il faudra ou
bien réécrire les règles, ou bien les remplir de conditions par produit, et un
playbook géant de règles par produit est exactement ce que « les règles sont des
données » existe pour éviter (#210).

**La couture est ici, et nulle part ailleurs.** Un normaliseur par produit, une
forme commune, et des règles qui ne parlent que de cette forme. Ajouter un
produit ajoute un normaliseur ; il n'ajoute pas une ligne dans une règle.

**Ce n'est pas une abstraction spéculative, et la différence tient à une
mesure.** L'inventaire expose déjà une forme normalisée pour Instance, Elastic Metal et
Apple Silicon, mais sans les dates ni les adresses : le vérifier a montré qu'il
ne peut pas servir de source aux règles écrites. Les modules, eux, rendent tout, pour Instance
seulement. La couture est donc le seul endroit où l'on peut, aujourd'hui,
séparer ce qu'une règle demande de ce qu'un produit nomme.

**Un produit inconnu se refuse.** Le normaliser « au mieux » rendrait une
ressource dont les champs manquants se liraient comme des absences : une machine
sans étiquette et une machine dont on ne sait pas lire les étiquettes se
ressemblent trop pour qu'on les confonde.
"""

from __future__ import annotations

from ansible.errors import AnsibleFilterError

DOCUMENTATION = r"""
name: resource_facts
short_description: Normalise a product payload into the shape rules speak
description:
  - Turns what a reading module returned into the common shape the audit rules
    are written against, so a rule never names a product's own fields.
  - Refuses a product it does not know rather than normalising it as best it
    can, because a missing field and an unreadable one look alike.
options:
  _input:
    description: What the reading module returned, one product's payloads.
    type: list
    required: true
  kind:
    description: Which product these payloads come from.
    type: str
    required: true
"""

RETURN = r"""
_value:
  description: One normalised resource per payload.
  type: list
  elements: dict
"""

EXAMPLES = r"""
- name: Normalise what the zones answered
  ansible.builtin.set_fact:
    faits: >-
      {{ machines | stephrobert.scaleway.resource_facts(kind='instance') }}
"""

#: La forme commune. Une règle ne parle que de ces noms, et c'est ce qui lui
#: permet de valoir pour un produit qu'elle ne connaît pas.
#:
#: `last_change` plutôt que `modification_date` : le nom dit ce que la règle
#: cherche, pas ce que l'API d'un produit a choisi d'appeler son champ.
#:
#: `id` en premier parce que c'est la seule identité que le contrat promette.
#: Mesuré sur le compte réel : deux machines peuvent porter le même nom dans une
#: zone, et les mentions d'unicité du contrat Instance portent toutes sur un
#: identifiant, aucune sur un nom. Une forme sans `id` ne permet pas de
#: reconnaître une ressource d'un run à l'autre (#231).
CHAMPS = (
    "kind",
    "id",
    "name",
    "zone",
    "state",
    "tags",
    "public_addresses",
    "last_change",
)

#: Ce que chaque produit porte **en plus**, et qu'aucun autre ne porte
#: forcément. La forme commune ne peut pas les accueillir : un cluster n'a pas
#: d'action permise et une machine n'a pas de version majeure à rattraper.
#:
#: **Un champ absent d'ici pour un produit n'est pas un champ vide.** La règle
#: qui le lit ne parle pas de ce produit, et elle saute la ressource au lieu de
#: la déclarer conforme. C'est la même distinction que partout ailleurs ici :
#: « je ne juge pas ça » et « j'ai jugé, c'est bon » ne se ressemblent pas.
#:
#: Aligner tout le monde sur le plus petit dénominateur aurait été plus simple
#: et aurait coûté les règles de #252, qui n'existent que parce que ces
#: champs-là existent.
SUPPLEMENTS: dict[str, tuple[str, ...]] = {
    "instance": ("planned_maintenance", "end_of_service", "allowed_actions"),
    "lb": (),
    "k8s_cluster": ("version", "upgrade_available", "expires_at", "versions_behind"),
    "k8s_node": ("health_conditions",),
    "lb_certificate": ("expires_at",),
}


def _adresses(charge: dict) -> list[str]:
    brutes = charge.get("public_ips") or (
        [charge["public_ip"]] if charge.get("public_ip") else []
    )
    return [
        adresse.get("address", "?") if isinstance(adresse, dict) else str(adresse)
        for adresse in brutes
    ]


def _instance(charge: dict) -> dict[str, object]:
    return {
        "kind": "instance",
        "id": charge.get("id"),
        "name": charge.get("name"),
        "zone": charge.get("zone"),
        "state": charge.get("state"),
        "tags": list(charge.get("tags") or []),
        "public_addresses": _adresses(charge),
        "last_change": charge.get("modification_date") or charge.get("creation_date"),
        # Les trois relevés dans la transcription réelle du 14 septembre 2026 :
        # `maintenances` vaut `[]`, `end_of_service` vaut `false`, et
        # `allowed_actions` vaut `["stop_in_place", "backup"]` sur une machine
        # arrêtée. Aucun n'est supposé.
        #
        # **`planned_maintenance` et pas `maintenances`** : la forme commune dit
        # ce que la règle cherche, pas ce que l'API d'un produit a choisi
        # d'appeler son champ.
        "planned_maintenance": list(charge.get("maintenances") or []),
        "end_of_service": charge.get("end_of_service"),
        "allowed_actions": list(charge.get("allowed_actions") or []),
    }


def _minorielle(version: object) -> tuple[int, int] | None:
    """La majeure et la mineure d'une version, ou rien si ce n'en est pas une.

    Rendre `(0, 0)` sur une chaîne qu'on ne sait pas lire ferait compter un
    retard énorme et parfaitement faux ; rien se lit « on ne sait pas ».
    """
    morceaux = str(version or "").split(".")
    if len(morceaux) < 2:
        return None
    try:
        return int(morceaux[0]), int(morceaux[1])
    except ValueError:
        return None


def _calendrier(contexte: dict, version: object) -> tuple[object, object]:
    """L'échéance de cette version, et son retard en mineures, depuis le catalogue.

    **La jointure vit ici, à la couture, et pas dans une règle.** C'est la seule
    place où le vocabulaire d'un produit a droit de cité : une règle qui saurait
    rapprocher un `version` d'un `ListVersions` ne serait plus une règle sur un
    parc.

    **Les deux rendent `None` séparément.** Une version absente du catalogue ne
    permet ni de dater sa fin de vie ni de compter son retard, mais un catalogue
    sans date de fin de vie permet encore de compter : les confondre perdrait la
    moitié de l'information qu'on a.

    Mesuré le 14 septembre 2026 : `ListVersions` rend bien `deprecated_at` et
    `end_of_life_at`, mais `scaleway.k8s.v1.Version` ne porte aucune clé
    `required` et les déclare `type: [string, "null"]`. L'absence est donc un
    cas normal, pas un incident.
    """
    catalogue = [v for v in (contexte.get("versions") or []) if isinstance(v, dict)]
    if not catalogue:
        return None, None

    echeance = next(
        (v.get("end_of_life_at") for v in catalogue if v.get("name") == version), None
    )

    courante = _minorielle(version)
    offertes = [m for m in (_minorielle(v.get("name")) for v in catalogue) if m]
    retard = None
    if courante and offertes:
        derniere = max(offertes)
        # Le retard se compte en mineures de la même majeure. Une majeure
        # d'écart n'est pas « quelques mineures de plus » : c'est une autre
        # question, et la compter dans le même nombre la ferait disparaître.
        retard = (
            derniere[1] - courante[1]
            if derniere[0] == courante[0]
            else None
        )
    return echeance, retard


def _k8s_cluster(charge: dict, contexte: dict | None = None) -> dict[str, object]:
    """Un cluster Kapsule, dans la forme commune.

    Il n'a pas de zone : le contrat le place dans une **région**, et la ranger
    sous `zone` est délibéré plutôt que commode. Tout ce qui compare deux runs
    dans ce dépôt raisonne sur des zones lues et des zones muettes ; une
    ressource dont la portée n'entrerait pas dans ce champ sortirait de ces
    comparaisons sans que rien ne le dise (#234).
    """
    echeance, retard = _calendrier(contexte or {}, charge.get("version"))
    return {
        "kind": "k8s_cluster",
        "id": charge.get("id"),
        "name": charge.get("name"),
        "zone": charge.get("region"),
        "state": charge.get("status"),
        "tags": list(charge.get("tags") or []),
        # Un cluster managé n'expose pas d'adresse publique de ressource : son
        # `cluster_url` est un point d'entrée d'API, pas une adresse du parc, et
        # le faire passer pour telle ferait rendre `public_ip` vrai sur tous les
        # clusters du monde.
        "public_addresses": [],
        "last_change": charge.get("updated_at") or charge.get("created_at"),
        "version": charge.get("version"),
        "upgrade_available": charge.get("upgrade_available"),
        # `expires_at` porte la fin de vie de la **version qu'il fait tourner**,
        # pas la sienne : c'est ce qu'un opérateur agit, et c'est le même nom que
        # l'échéance d'un certificat, donc la même règle pour les deux.
        "expires_at": echeance,
        "versions_behind": retard,
    }


def _k8s_node(charge: dict) -> dict[str, object]:
    """Un nœud de pool, dans la forme commune.

    **`conditions` est mesuré, pas contracté.** Relevé le 14 septembre 2026 sur
    la réponse réelle, où il vaut
    `{"DiskPressure": "False", ..., "Ready": "True"}` ; `scaleway.k8s.v1.Node`
    ne le déclare pas, non plus que `public_ip_v4` et `public_ip_v6`.

    La conséquence est portée par la règle et non ici : son absence vaut « non
    mesuré », jamais « sain ». Le jour où l'API cesserait de le rendre, aucun
    golden ne rougirait, et une règle qui lirait l'absence comme une bonne
    nouvelle annoncerait un parc sain sur zéro champ lu.
    """
    return {
        "kind": "k8s_node",
        "id": charge.get("id"),
        "name": charge.get("name"),
        "zone": charge.get("region"),
        "state": charge.get("status"),
        "tags": [],
        "public_addresses": [
            adresse
            for adresse in (charge.get("public_ip_v4"), charge.get("public_ip_v6"))
            if adresse
        ],
        "last_change": charge.get("updated_at") or charge.get("created_at"),
        "health_conditions": charge.get("conditions"),
    }


def _lb_certificate(charge: dict) -> dict[str, object]:
    """Un certificat de load balancer, dans la forme commune.

    `not_valid_after` devient `expires_at`, le même nom que porte l'échéance
    d'une exception de politique : c'est la même question posée à deux objets,
    et lui donner deux noms obligerait à écrire deux règles pour une chose.
    """
    return {
        "kind": "lb_certificate",
        "id": charge.get("id"),
        "name": charge.get("name"),
        "zone": (charge.get("lb") or {}).get("zone"),
        "state": charge.get("status"),
        "tags": [],
        "public_addresses": [],
        "last_change": charge.get("updated_at") or charge.get("created_at"),
        "expires_at": charge.get("not_valid_after"),
    }


def _lb(charge: dict) -> dict[str, object]:
    """Un load balancer, dans la forme commune.

    Le vocabulaire diffère, et c'est exactement ce que cette couture existe pour
    absorber : le contrat nomme `status` ce qu'Instance nomme `state`, ses
    adresses vivent sous `ip[].ip_address`, et ses dates sont `updated_at` et
    `created_at` là où Instance dit `modification_date`. Une règle qui devrait
    connaître ces trois écarts ne serait plus une règle sur un parc.
    """
    return {
        "kind": "lb",
        "id": charge.get("id"),
        "name": charge.get("name"),
        "zone": charge.get("zone"),
        "state": charge.get("status"),
        "tags": list(charge.get("tags") or []),
        "public_addresses": [
            adresse.get("ip_address", "?") if isinstance(adresse, dict) else str(adresse)
            for adresse in (charge.get("ip") or [])
        ],
        "last_change": charge.get("updated_at") or charge.get("created_at"),
    }


#: Les produits que ce normaliseur sait lire. Le jour où Elastic Metal aura des
#: modules, il s'ajoute ici, et aucune règle ne bouge.
#: Les normaliseurs qui ont besoin d'autre chose que leur propre charge utile.
#: Déclaré plutôt que deviné par introspection : une signature qui change sans
#: qu'on s'en aperçoive ferait passer le contexte à personne, en silence.
AVEC_CONTEXTE = (_k8s_cluster,)

NORMALISEURS = {
    "instance": _instance,
    "lb": _lb,
    "k8s_cluster": _k8s_cluster,
    "k8s_node": _k8s_node,
    "lb_certificate": _lb_certificate,
}


def resource_facts(
    charges: object, kind: str, context: object = None
) -> list[dict[str, object]]:
    """Les ressources, dans la forme que les règles lisent.

    `context` porte ce qu'un produit a besoin de rapprocher pour se normaliser,
    et rien d'autre : le catalogue des versions Kubernetes, pour qu'un cluster
    puisse dire quand la sienne meurt. C'est mesuré par l'appelant et passé
    ici, jamais deviné.
    """
    normaliseur = NORMALISEURS.get(kind)
    if normaliseur is None:
        raise AnsibleFilterError(
            f"aucun normaliseur pour `{kind}`. Les produits connus sont "
            f"{', '.join(sorted(NORMALISEURS))}. Normaliser au mieux rendrait "
            "des champs absents qui se liraient comme des absences : une "
            "machine sans étiquette et une machine dont on ne sait pas lire les "
            "étiquettes ne doivent pas se ressembler."
        )

    if not isinstance(charges, (list, tuple)):
        raise AnsibleFilterError(
            f"`resource_facts` attend une liste de charges utiles, pas "
            f"{type(charges).__name__}"
        )

    if context is not None and not isinstance(context, dict):
        raise AnsibleFilterError(
            f"`context` est un dictionnaire de mesures, pas {type(context).__name__}"
        )

    normalisees = [
        normaliseur(charge, context or {})
        if normaliseur in AVEC_CONTEXTE
        else normaliseur(charge)
        for charge in charges
    ]

    # **Un normaliseur qui oublie un champ le rend indiscernable d'un champ que
    # l'API n'a pas rendu.** La règle qui le lit sauterait la ressource en
    # croyant que ce produit ne porte pas ce champ, et le parc sortirait
    # conforme parce que personne ne l'a jugé. Le contrôle porte sur la forme
    # produite, une fois, et non sur chaque ressource.
    attendus = set(CHAMPS) | set(SUPPLEMENTS.get(kind, ()))
    for ressource in normalisees[:1]:
        if set(ressource) != attendus:
            manquants = sorted(attendus - set(ressource))
            surnumeraires = sorted(set(ressource) - attendus)
            raise AnsibleFilterError(
                f"le normaliseur `{kind}` ne rend pas la forme déclarée : "
                f"manque {manquants or 'rien'}, en trop {surnumeraires or 'rien'}. "
                "Un champ manquant se lirait comme un champ que ce produit ne "
                "porte pas, et la règle qui le juge sauterait la ressource."
            )

    # **Une ressource sans identité ne se normalise pas « au mieux ».** Elle
    # entrerait dans un instantané que rien ne pourrait comparer, et le diff la
    # verrait apparaître puis disparaître à chaque run. Le contrat promet un
    # identifiant sur toute ressource que ces modules lisent : son absence dit
    # que la charge utile n'est pas celle qu'on croit.
    sans_identite = [
        ressource.get("name") or "<sans nom>"
        for ressource in normalisees
        if not ressource.get("id")
    ]
    if sans_identite:
        raise AnsibleFilterError(
            f"{len(sans_identite)} ressource(s) `{kind}` sans identifiant : "
            f"{', '.join(sans_identite[:5])}. Une ressource sans `id` ne peut pas "
            "être reconnue d'un run à l'autre, et un instantané qui la porte "
            "produirait une apparition puis une disparition à chaque lecture."
        )

    return normalisees


class FilterModule:
    """Ce que la collection publie comme filtres."""

    def filters(self) -> dict[str, object]:
        return {"resource_facts": resource_facts}
