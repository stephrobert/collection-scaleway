# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le filtrage qui reste à faire une fois les réponses reçues.

Ce qui peut se filtrer côté API l'est côté API : c'est le provider qui passe
`tags`, `state` et `project` dans sa requête, pour ne pas transférer ce qu'on
va jeter. Ce module ne traite que ce que l'API ne sait pas exprimer :

* `tags_match: all`, alors que l'API applique un OU ;
* les exclusions, que l'API n'exprime pas ;
* les états pour les produits dont l'API ne filtre pas dessus.

Les fonctions sont pures : elles décident sur le modèle normalisé, sans appel.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import InventoryHost


@dataclass(frozen=True)
class Filters:
    """Ce que l'utilisateur garde, et ce qu'il écarte."""

    tags: tuple[str, ...] = ()
    tags_match: str = "any"
    states: tuple[str, ...] = ()
    exclude_tags: tuple[str, ...] = ()
    exclude_states: tuple[str, ...] = ()

    def api_tags(self) -> tuple[str, ...]:
        """Les tags à passer à l'API.

        En mode `all`, l'API ne sait pas l'exprimer : on lui demande quand même
        les tags, ce qui réduit déjà le transfert, et on affine ici.
        """
        return self.tags


def keep(host: InventoryHost, filters: Filters) -> tuple[bool, str]:
    """Garde-t-on cette machine, et sinon pourquoi.

    La raison est rendue pour que le mode debug puisse répondre à « pourquoi
    cette machine n'apparaît-elle pas ».
    """
    tags = set(host.tags)

    for tag in filters.exclude_tags:
        if tag in tags:
            return False, f"exclue par le tag '{tag}'"

    if host.state and host.state in filters.exclude_states:
        return False, f"exclue par l'état '{host.state}'"

    if filters.states and (host.state or "") not in filters.states:
        return False, f"état '{host.state}' hors de {list(filters.states)}"

    if filters.tags:
        demandes = set(filters.tags)
        if filters.tags_match == "all":
            manquants = sorted(demandes - tags)
            if manquants:
                return False, f"tags manquants {manquants}"
        elif not demandes & tags:
            return False, f"aucun des tags {sorted(demandes)}"

    return True, "retenue"


def apply(
    hosts: tuple[InventoryHost, ...],
    filters: Filters,
) -> tuple[tuple[InventoryHost, ...], tuple[str, ...]]:
    """Applique les filtres, et rend les raisons des écarts."""
    gardes: list[InventoryHost] = []
    raisons: list[str] = []
    for host in hosts:
        garde, raison = keep(host, filters)
        if garde:
            gardes.append(host)
        else:
            raisons.append(f"{host.name or host.id} ({host.product}) : {raison}")
    return tuple(gardes), tuple(raisons)
