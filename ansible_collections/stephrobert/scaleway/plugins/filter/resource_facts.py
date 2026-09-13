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
NORMALISEURS = {"instance": _instance, "lb": _lb}


def resource_facts(charges: object, kind: str) -> list[dict[str, object]]:
    """Les ressources, dans la forme que les règles lisent."""
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

    normalisees = [normaliseur(charge) for charge in charges]

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
