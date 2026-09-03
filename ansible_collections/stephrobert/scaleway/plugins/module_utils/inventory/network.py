# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""L'index réseau, et la jointure en mémoire.

Le plugin officiel demande à IPAM les adresses **d'une carte réseau à la
fois** : un appel par carte et par machine, soit deux mille appels pour mille
Instances à deux cartes. Et il en tire moins que ce qu'un seul appel régional
donnerait, parce qu'il jette la relation réseau.

Ici, on liste une fois par région, on indexe, puis on joint :

    list_i_ps(region)              -> adresses, avec leur ressource et leur réseau
    list_private_networks(region)  -> nom du réseau, et son VPC
    list_vpcs(region)              -> nom du VPC
              |
              v
      index en dictionnaires
              |
              v
      jointure O(cartes réseau)

La complexité en appels devient `O(régions)` au lieu de `O(hosts × cartes)`.

Ce module ne connaît pas le SDK : il travaille sur des enregistrements déjà
normalisés, ce qui le rend testable sans réseau et réutilisable par n'importe
quel provider.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .models import NetworkAttachment


@dataclass(frozen=True)
class IpamAddress:
    """Une adresse IPAM, réduite à ce dont la jointure a besoin.

    `private_network_id` et `vpc_id` viennent de `ipam.v1.Source`, que l'API
    rend avec chaque adresse. C'est cette information que le plugin officiel
    ne conserve pas.
    """

    address: str
    is_ipv6: bool
    resource_id: str | None = None
    private_network_id: str | None = None
    vpc_id: str | None = None
    mac_address: str | None = None


@dataclass(frozen=True)
class PrivateNetworkInfo:
    """Ce qu'on sait d'un réseau privé, et de son VPC."""

    id: str
    name: str | None = None
    vpc_id: str | None = None


@dataclass(frozen=True)
class NicRef:
    """Une carte réseau privée telle que la porte déjà la réponse du produit.

    Pour Instance, `instance.v1.PrivateNIC` donne l'identifiant, le réseau et
    l'adresse MAC : la liaison machine vers réseau ne coûte donc aucun appel
    supplémentaire.
    """

    id: str
    private_network_id: str | None = None
    mac_address: str | None = None


@dataclass(frozen=True)
class NetworkIndex:
    """Les index construits une fois, consultés autant de fois qu'il faut."""

    addresses_by_resource: Mapping[str, tuple[IpamAddress, ...]]
    networks: Mapping[str, PrivateNetworkInfo]
    vpc_names: Mapping[str, str]

    @property
    def address_count(self) -> int:
        return sum(len(v) for v in self.addresses_by_resource.values())


def strip_netmask(address: str) -> str:
    """`10.0.0.5/22` -> `10.0.0.5`. IPAM rend un CIDR, Ansible veut une adresse."""
    return address.split("/", 1)[0]


def build_index(
    addresses: tuple[IpamAddress, ...],
    networks: tuple[PrivateNetworkInfo, ...] = (),
    vpc_names: Mapping[str, str] | None = None,
) -> NetworkIndex:
    """Construit les index de jointure. Une seule passe sur chaque liste."""
    par_ressource: dict[str, list[IpamAddress]] = {}
    for adresse in addresses:
        if not adresse.resource_id:
            continue
        par_ressource.setdefault(adresse.resource_id, []).append(adresse)

    return NetworkIndex(
        addresses_by_resource={
            ressource: tuple(sorted(liste, key=lambda a: (a.is_ipv6, a.address)))
            for ressource, liste in par_ressource.items()
        },
        networks={reseau.id: reseau for reseau in networks},
        vpc_names=dict(vpc_names or {}),
    )


def attach(nics: tuple[NicRef, ...], index: NetworkIndex) -> tuple[NetworkAttachment, ...]:
    """Joint les cartes réseau d'une machine avec l'index, sans appel d'API.

    Le rattachement conserve **toutes** les adresses de chaque réseau, et le
    réseau lui-même. C'est ce qui permet ensuite de choisir `ansible_host` par
    réseau nommé plutôt que par ordre d'arrivée.
    """
    rattachements: list[NetworkAttachment] = []

    for nic in nics:
        adresses = index.addresses_by_resource.get(nic.id, ())
        reseau_id = nic.private_network_id or next(
            (a.private_network_id for a in adresses if a.private_network_id), None
        )
        if reseau_id is None:
            continue

        info = index.networks.get(reseau_id)
        vpc_id = info.vpc_id if info else next((a.vpc_id for a in adresses if a.vpc_id), None)

        rattachements.append(
            NetworkAttachment(
                private_network_id=reseau_id,
                private_network_name=info.name if info else None,
                vpc_id=vpc_id,
                vpc_name=index.vpc_names.get(vpc_id) if vpc_id else None,
                ipv4=tuple(strip_netmask(a.address) for a in adresses if not a.is_ipv6),
                ipv6=tuple(strip_netmask(a.address) for a in adresses if a.is_ipv6),
                mac_address=nic.mac_address
                or next((a.mac_address for a in adresses if a.mac_address), None),
            )
        )

    # Trié par nom de réseau puis par identifiant : deux exécutions doivent
    # rendre le même ordre, sur lequel la sélection d'adresse s'appuie.
    return tuple(
        sorted(
            rattachements,
            key=lambda a: (a.private_network_name or "", a.private_network_id),
        )
    )


def flatten(attachments: tuple[NetworkAttachment, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Les adresses privées, toutes réseaux confondus, dans l'ordre des réseaux."""
    ipv4 = tuple(adresse for a in attachments for adresse in a.ipv4)
    ipv6 = tuple(adresse for a in attachments for adresse in a.ipv6)
    return ipv4, ipv6
