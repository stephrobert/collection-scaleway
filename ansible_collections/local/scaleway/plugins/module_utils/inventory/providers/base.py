# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ce qu'un provider doit savoir faire, et ce qu'il ne doit pas faire.

**Un provider ne touche jamais à l'objet d'inventaire d'Ansible.** Il rend un
`ProviderResult` ; c'est le moteur qui décide ensuite quoi en faire. Sans cette
règle, ajouter un produit demanderait de toucher au cœur, ce que l'étape 5 du
brief interdit précisément.

**Un provider n'importe pas le SDK.** Il reçoit un objet d'API qui expose les
méthodes dont il a besoin. Un test lui passe un objet qui rend des réponses
figées, et la normalisation se mesure sans réseau ni identifiants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..models import ProviderResult


@dataclass(frozen=True)
class DiscoveryContext:
    """Ce que l'utilisateur a demandé, tel qu'un provider en a besoin."""

    zones: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    project_ids: tuple[str, ...] = ()
    organization_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    states: tuple[str, ...] = ()
    include_raw: bool = False
    #: Les index réseau, construits une fois pour tous les providers.
    network: Any | None = None

    def scoped_zones(self, available: tuple[str, ...]) -> tuple[str, ...]:
        """Les zones à interroger pour ce produit.

        Sans demande explicite, on prend celles que le produit déclare, et non
        une liste écrite en dur : le plugin officiel en oublie trois sur dix.
        """
        if not self.zones:
            return available
        return tuple(zone for zone in self.zones if zone in available)


#: Les zones Scaleway connues, mesurées sur le contrat OpenAPI d'Instance.
#:
#: Pour un produit dont ce dépôt ne versionne pas le contrat, cette liste sert
#: de **candidates** : le provider interroge, et une zone où le produit n'existe
#: pas répond en le disant, ce qui la retire sans bruit. C'est l'inverse du
#: plugin officiel, qui code sept zones en dur et en oublie trois pour tout le
#: monde.
SCALEWAY_ZONES: tuple[str, ...] = (
    "fr-par-1",
    "fr-par-2",
    "fr-par-3",
    "nl-ams-1",
    "nl-ams-2",
    "nl-ams-3",
    "pl-waw-1",
    "pl-waw-2",
    "pl-waw-3",
    "it-mil-1",
)


class InventoryProvider(Protocol):
    """L'interface qu'un produit doit remplir pour entrer dans l'inventaire."""

    name: str

    def discover(self, context: DiscoveryContext) -> ProviderResult: ...


@dataclass
class ProviderReport:
    """Ce qu'un provider a fait, pour le mode debug et le rapport d'échec."""

    name: str
    hosts: int = 0
    api_calls: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def region_of(zone: str | None) -> str | None:
    """`fr-par-1` -> `fr-par`. Les produits zonaux ne rendent pas leur région.

    La règle est mécanique et vient de la forme des identifiants Scaleway :
    une zone est une région suivie d'un index. Elle est écrite ici une fois,
    plutôt que devinée dans chaque provider.
    """
    if not zone:
        return None
    morceaux = zone.rsplit("-", 1)
    if len(morceaux) == 2 and morceaux[1].isdigit():
        return morceaux[0]
    return zone
