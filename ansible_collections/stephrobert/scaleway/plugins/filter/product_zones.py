# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ce qu'un produit offre, distingué de ce qu'on n'a pas pu mesurer.

Le rapport de parc demandait au Load Balancer des zones que son contrat ne
déclare pas, et les rendait « non mesurées ». Chaque exécution propre en
annonçait deux, et `zones_unmeasured` porte pourtant l'affirmation la plus
répétée de ce dépôt : rien n'a été mesuré n'est pas rien n'a été trouvé (#222).

Un signal qui crie au loup est un signal que personne ne lit. Le jour où une
zone ne répond vraiment pas, la ligne aurait eu la même allure que les deux
autres.

**La carte vient du contrat**, écrite par le générateur dans `module_utils`.
Recopier huit zones dans un rôle en ferait une seconde source, fausse le jour
où le produit en ouvre une.
"""

from __future__ import annotations

from ansible.errors import AnsibleFilterError

try:  # pragma: no cover - le chemin d'import diffère entre collection et tests
    from ansible_collections.stephrobert.scaleway.plugins.module_utils.zones import ZONES
except ImportError:  # pragma: no cover
    from ..module_utils.zones import ZONES  # type: ignore[no-redef]

DOCUMENTATION = r"""
name: product_zones
short_description: Split asked zones into what a product offers and what it does not
description:
  - Returns the asked zones a product's contract declares, and those it does
    not, so a report never calls a zone unmeasured when it was never offered.
options:
  _input:
    description: The zones somebody asked for.
    type: list
    required: true
  kind:
    description: The product, as the contracts name it.
    type: str
    required: true
"""

RETURN = r"""
_value:
  description: Two lists, C(offered) and C(not_offered), both sorted.
  type: dict
"""

EXAMPLES = r"""
- name: Ask each product only what it serves
  ansible.builtin.set_fact:
    zones_lb: >-
      {{ zones | stephrobert.scaleway.product_zones(kind='lb') }}
"""


def product_zones(zones: object, kind: str) -> dict[str, list[str]]:
    """Les zones demandées, partagées entre offertes et non offertes."""
    declarees = ZONES.get(kind)
    if declarees is None:
        raise AnsibleFilterError(
            f"aucune zone connue pour `{kind}`. Les produits générés sont "
            f"{', '.join(sorted(ZONES))}. La carte vient des contrats : un "
            "produit absent d'ici n'a pas de module, donc rien à interroger."
        )

    if not isinstance(zones, (list, tuple)):
        raise AnsibleFilterError(
            f"`product_zones` attend une liste de zones, pas {type(zones).__name__}"
        )

    demandees = [str(zone) for zone in zones]
    return {
        "offered": sorted(zone for zone in demandees if zone in declarees),
        # Nommées, pas tues : une zone qu'un produit n'offre pas est un fait sur
        # le produit, et c'est une information. La taire ferait croire que le
        # rapport a couvert ce qu'on lui avait demandé.
        "not_offered": sorted(zone for zone in demandees if zone not in declarees),
    }


class FilterModule:
    """Ce que la collection publie comme filtres."""

    def filters(self) -> dict[str, object]:
        return {"product_zones": product_zones}
