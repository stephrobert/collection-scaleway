# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Les ressources qu'un sélecteur désigne, dans une population lue par l'API.

Le pendant de `select_hosts`, pour ce qui ne vient pas de l'inventaire. La
grammaire est la même, écrite une seule fois : un critère et un seul, une clé
inconnue refusée, une combinaison d'étiquettes nommée.

**Ce qui change d'une population à l'autre est le vocabulaire, pas la
grammaire.** Un groupe de nœuds est un pool ; un groupe de machines est un
groupe d'inventaire. La table de correspondance est déclarée par produit ici,
et c'est la seule chose que ce filtre ajoute.
"""

from __future__ import annotations

from ansible.errors import AnsibleFilterError

try:  # pragma: no cover - le chemin d'import diffère entre collection et tests
    from ansible_collections.stephrobert.scaleway.plugins.module_utils.selecteur import (
        SelecteurError,
        designer,
    )
except ImportError:  # pragma: no cover
    from ..module_utils.selecteur import SelecteurError, designer  # type: ignore[no-redef]

DOCUMENTATION = r"""
name: select_resources
short_description: What a selector designates among resources read from the API
description:
  - >-
    The counterpart of C(select_hosts) for what does not come from the
    inventory. The grammar is the same: exactly one of the criteria this
    product accepts, plus C(match) when several tags are given.
  - >-
    An ambiguous C(name) is refused rather than settled, because two resources
    can carry one name and acting on the first would act on one nobody named.
options:
  _input:
    description: The selector.
    type: dict
    required: true
  _resources:
    description: The resources to choose among, in the common shape.
    type: list
    required: true
  kind:
    description: Which product these resources are, which says what a group is.
    type: str
    required: true
"""

RETURN = r"""
_value:
  description: The resources the selector designates.
  type: list
  elements: dict
"""

EXAMPLES = r"""
- name: The nodes of one pool
  ansible.builtin.set_fact:
    designes: >-
      {{ {'group': 'production'}
         | stephrobert.scaleway.select_resources(noeuds, kind='k8s_node') }}
"""

#: Ce qu'un critère nomme, produit par produit. C'est tout ce qui distingue une
#: population d'une autre.
#:
#: `group` n'est pas au même endroit selon le produit, et c'est bien pourquoi il
#: est déclaré : un pool groupe des nœuds, et une machine n'a pas de groupe
#: hors de l'inventaire, où `select_hosts` la trouve.
#:
#: `tags` est absent de `k8s_node` : mesuré, `scaleway.k8s.v1.Node` ne porte pas
#: d'étiquettes. `scaleway.k8s.v1.Pool` en porte, et faire passer celles du pool
#: pour celles du nœud ajouterait un saut que l'utilisateur ne voit pas.
CHAMPS = {
    "instance": {"name": "name", "tags": "tags", "id": "id"},
    "lb": {"name": "name", "tags": "tags", "id": "id"},
    "k8s_cluster": {"name": "name", "tags": "tags", "id": "id"},
    "k8s_pool": {"name": "name", "tags": "tags", "id": "id"},
    "k8s_node": {"group": "pool", "name": "name", "id": "id"},
    "lb_certificate": {"name": "name", "id": "id"},
}


def select_resources(selecteur: object, resources: object, kind: str) -> list[dict]:
    """Les ressources de ce produit que ce sélecteur désigne."""
    champs = CHAMPS.get(kind)
    if champs is None:
        raise AnsibleFilterError(
            f"aucune table de sélection pour `{kind}`. Les produits connus sont "
            f"{', '.join(sorted(CHAMPS))}. Sélectionner au mieux ferait chercher "
            "un champ qui n'existe pas, donc ne rien désigner, donc se lire "
            "comme un parc vide."
        )
    if not isinstance(resources, (list, tuple)):
        raise AnsibleFilterError(
            f"les ressources sont une liste, pas {type(resources).__name__}"
        )

    try:
        return designer(
            selecteur, list(resources), champs=champs, quoi=f"le sélecteur `{kind}`"
        )
    except SelecteurError as erreur:
        raise AnsibleFilterError(str(erreur)) from erreur


#: Où chaque produit attend la portée d'une de ses ressources. Une machine se
#: lit par sa zone, un nœud de pool par sa région : c'est ce que chaque API
#: demande, et rien ne le déduit du reste. La forme normalisée range les deux
#: sous `zone`, parce que c'est la portée de la ressource et non le nom que son
#: produit lui donne.
PORTEE = {"instance": "scope", "k8s_node": "scope"}


def reboot_target(ressource: object, kind: str) -> dict[str, object]:
    """Ce qu'il faut pour redémarrer une ressource, dans une forme commune.

    **Une forme commune, pour que la vague n'ait pas à connaître les deux.** Un
    roulement qui dispatcherait sur le produit à chaque ligne finirait par en
    oublier une, et ce serait celle qui redémarre.
    """
    if kind not in PORTEE:
        raise AnsibleFilterError(
            f"aucune portée connue pour `{kind}`. Les produits que ce rôle "
            f"redémarre sont {', '.join(sorted(PORTEE))}."
        )
    if not isinstance(ressource, dict):
        raise AnsibleFilterError(
            f"une cible de redémarrage est un objet, pas {type(ressource).__name__}"
        )
    portee = ressource.get(PORTEE[kind])
    if not portee or not ressource.get("id"):
        raise AnsibleFilterError(
            f"la ressource `{ressource.get('name') or '?'}` ne porte pas "
            f"{PORTEE[kind]} et id. Redémarrer sans savoir où viserait une "
            "ressource que personne n'a désignée."
        )
    return {
        "kind": kind,
        "scope": portee,
        "id": ressource["id"],
        "name": ressource.get("name"),
    }


class FilterModule:
    """Ce que la collection publie pour désigner des ressources."""

    def filters(self) -> dict[str, object]:
        return {
            "select_resources": select_resources,
            "reboot_target": reboot_target,
        }
