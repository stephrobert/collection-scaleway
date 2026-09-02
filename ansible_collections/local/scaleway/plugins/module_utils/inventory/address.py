# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le choix de `ansible_host`, et l'explication de ce choix.

C'est la décision la plus lourde de conséquences du plugin : elle détermine
par où Ansible joindra la machine. Elle est donc **pure** — aucun appel d'API,
aucune lecture de configuration globale — et elle **s'explique** : la sélection
rend la raison à côté de l'adresse, pour que le mode debug puisse répondre à
« pourquoi cette IP a-t-elle été choisie ».

Le modèle normalisé porte plusieurs adresses par famille et plusieurs réseaux
privés. Choisir, c'est donc ordonner, et l'ordre appartient à l'utilisateur.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import InventoryHost

#: Les familles d'adresses que l'on sait ordonner. Un nom hors de cette liste
#: est une faute de configuration, pas un repli silencieux.
FAMILIES: tuple[str, ...] = ("private_ipv4", "public_ipv4", "private_ipv6", "public_ipv6")

#: L'ordre par défaut : le réseau privé d'abord, parce qu'un contrôleur qui
#: gère un parc Scaleway est le plus souvent dedans, et qu'une adresse privée
#: ne dépend pas de l'attribution d'une IP publique.
DEFAULT_PRIORITY: tuple[str, ...] = FAMILIES


@dataclass(frozen=True)
class AddressPolicy:
    """Ce que l'utilisateur a demandé, sous une forme que la fonction sait lire."""

    priority: tuple[str, ...] = DEFAULT_PRIORITY
    #: Nom ou identifiant d'un réseau privé. Quand il est donné, seules les
    #: adresses de ce réseau sont éligibles.
    private_network: str | None = None

    def families(self) -> tuple[str, ...]:
        """Les familles retenues, dans l'ordre, sans les inconnues."""
        return tuple(nom for nom in self.priority if nom in FAMILIES)


@dataclass(frozen=True)
class AddressSelection:
    """L'adresse choisie, et de quoi expliquer pourquoi."""

    address: str | None
    #: `private_ipv4`, `public_ipv6`, ... ou la raison de l'échec.
    source: str
    private_network: str | None = None
    #: Ce qui a été regardé, dans l'ordre, avant de trancher.
    considered: tuple[str, ...] = ()

    @property
    def found(self) -> bool:
        return self.address is not None

    def explain(self, host_name: str) -> str:
        """Une ligne lisible pour le mode debug."""
        if not self.found:
            return f"{host_name}: aucune adresse ({self.source}), examiné {list(self.considered)}"
        reseau = f", réseau {self.private_network}" if self.private_network else ""
        return f"{host_name}: {self.address} par {self.source}{reseau}"


def _from_families(
    familles: tuple[str, ...],
    source: dict[str, tuple[str, ...]],
) -> tuple[str, str] | None:
    """La première adresse non vide, dans l'ordre demandé."""
    for famille in familles:
        adresses = source.get(famille, ())
        if adresses:
            return adresses[0], famille
    return None


def select_ansible_host(host: InventoryHost, policy: AddressPolicy) -> AddressSelection:
    """Choisit l'adresse par laquelle Ansible joindra cette machine.

    Deux modes, et le second l'emporte quand il est demandé :

    * **par famille** : on suit l'ordre de `priority` et on prend la première
      adresse disponible ;
    * **par réseau privé** : seules les adresses du réseau nommé sont
      éligibles. Une machine sur `backend` et `monitoring` peut ainsi être
      jointe par `backend` de façon déterministe, ce que l'ordre des familles
      seul ne permet pas.

    Aucune adresse trouvée n'est un résultat, pas une erreur : c'est
    l'appelant qui décide d'écarter le host ou de le garder sans
    `ansible_host`.
    """
    familles = policy.families()

    if policy.private_network is not None:
        attachement = host.attachment(policy.private_network)
        if attachement is None:
            return AddressSelection(
                address=None,
                source=f"réseau privé '{policy.private_network}' absent de cette machine",
                considered=tuple(
                    a.private_network_name or a.private_network_id for a in host.private_networks
                ),
            )
        disponibles = {"private_ipv4": attachement.ipv4, "private_ipv6": attachement.ipv6}
        ordre = tuple(f for f in familles if f.startswith("private_")) or (
            "private_ipv4",
            "private_ipv6",
        )
        trouve = _from_families(ordre, disponibles)
        if trouve is None:
            return AddressSelection(
                address=None,
                source=f"aucune adresse sur le réseau '{policy.private_network}'",
                private_network=attachement.private_network_name or attachement.private_network_id,
                considered=ordre,
            )
        adresse, famille = trouve
        return AddressSelection(
            address=adresse,
            source=famille,
            private_network=attachement.private_network_name or attachement.private_network_id,
            considered=ordre,
        )

    disponibles = {
        "private_ipv4": host.private_ipv4,
        "public_ipv4": host.public_ipv4,
        "private_ipv6": host.private_ipv6,
        "public_ipv6": host.public_ipv6,
    }
    trouve = _from_families(familles, disponibles)
    if trouve is None:
        return AddressSelection(
            address=None,
            source="aucune adresse dans les familles demandées",
            considered=familles,
        )

    adresse, famille = trouve
    reseau = None
    if famille.startswith("private_"):
        for attachement in host.private_networks:
            if adresse in attachement.addresses:
                reseau = attachement.private_network_name or attachement.private_network_id
                break
    return AddressSelection(
        address=adresse, source=famille, private_network=reseau, considered=familles
    )
