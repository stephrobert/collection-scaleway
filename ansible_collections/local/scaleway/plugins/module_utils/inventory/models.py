# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le modèle normalisé de l'inventaire, et lui seul.

Aucun objet du SDK Scaleway ne traverse cette frontière. Un provider traduit ce
que son API rend en `InventoryHost` ; tout ce qui vient après (sélection
d'adresse, nom d'hôte, groupes, variables) ne connaît que ce modèle.

C'est ce qui permet d'ajouter un produit sans toucher au cœur : Elastic Metal
et Apple Silicon n'ont rien en commun avec Instance dans le SDK, et tout en
commun ici.

**Le modèle porte la relation réseau, pas seulement l'adresse.** Le plugin
officiel range les adresses privées dans `vpc_ipv4: str | None`, et c'est
précisément cette forme qui perd l'information : une machine sur deux réseaux
privés en garde une seule, sans dire laquelle. L'API la donne, mesuré sur
IPAM et sur les cartes réseau ; le modèle doit la garder.

Les dataclasses sont gelées et les collections sont des tuples : un inventaire
immuable se compare, se hache et se sérialise sans surprise, ce qui est la
condition d'un cache honnête.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NetworkAttachment:
    """Le rattachement d'une machine à un réseau privé.

    Répond à « cette machine est sur quel réseau, dans quel VPC », et pas
    seulement « cette machine a l'adresse 10.42.1.8 ».
    """

    private_network_id: str
    private_network_name: str | None = None
    vpc_id: str | None = None
    vpc_name: str | None = None
    ipv4: tuple[str, ...] = ()
    ipv6: tuple[str, ...] = ()
    mac_address: str | None = None

    @property
    def addresses(self) -> tuple[str, ...]:
        return (*self.ipv4, *self.ipv6)

    def to_variable(self) -> dict[str, Any]:
        """Ce que l'utilisateur voit dans ses hostvars."""
        return {
            "id": self.private_network_id,
            "name": self.private_network_name,
            "vpc_id": self.vpc_id,
            "vpc_name": self.vpc_name,
            "ipv4": list(self.ipv4),
            "ipv6": list(self.ipv6),
            "mac_address": self.mac_address,
        }


@dataclass(frozen=True)
class InventoryHost:
    """Une ressource sur laquelle Ansible peut vouloir agir.

    « Vouloir agir » et non « pouvoir se connecter » : un host sans route SSH
    reste utile, parce qu'un playbook peut le piloter par les modules Day-2 en
    `delegate_to: localhost`. C'est pourquoi `id` et `product` sont
    obligatoires là où l'adresse ne l'est pas.
    """

    id: str
    product: str
    name: str | None = None

    organization_id: str | None = None
    project_id: str | None = None

    region: str | None = None
    zone: str | None = None
    state: str | None = None

    tags: tuple[str, ...] = ()

    public_ipv4: tuple[str, ...] = ()
    public_ipv6: tuple[str, ...] = ()
    private_ipv4: tuple[str, ...] = ()
    private_ipv6: tuple[str, ...] = ()

    private_networks: tuple[NetworkAttachment, ...] = ()

    #: Ce qui n'appartient qu'à ce produit, exposé sous son propre préfixe.
    metadata: Mapping[str, Any] = field(default_factory=dict)

    #: La réponse brute, seulement si l'utilisateur l'a demandée.
    raw: Any | None = None

    def attachment(self, network: str) -> NetworkAttachment | None:
        """Le rattachement au réseau nommé, par son identifiant ou son nom."""
        for attachement in self.private_networks:
            if network in (attachement.private_network_id, attachement.private_network_name):
                return attachement
        return None


@dataclass(frozen=True)
class ProviderResult:
    """Ce qu'un provider rend : des hosts, et ce qui s'est mal passé.

    Les avertissements et les erreurs font partie du résultat, pas d'un effet
    de bord. Un provider qui échoue en silence rend un inventaire incomplet
    avec un code de retour 0, et c'est le défaut principal du plugin officiel.
    """

    hosts: tuple[InventoryHost, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    #: Nombre d'appels d'API réellement effectués, pour le mode debug.
    api_calls: int = 0

    def merge(self, other: ProviderResult) -> ProviderResult:
        return ProviderResult(
            hosts=(*self.hosts, *other.hosts),
            warnings=(*self.warnings, *other.warnings),
            errors=(*self.errors, *other.errors),
            api_calls=self.api_calls + other.api_calls,
        )
