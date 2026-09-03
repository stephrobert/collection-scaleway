# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le provider Instance.

Il traduit `instance.v1.Server` en `InventoryHost`, et rien d'autre. Il ne
connaît ni Ansible, ni le cache, ni les groupes, et il n'importe pas le SDK :
il reçoit un objet d'API, ce qui permet de le tester avec des réponses figées.

Deux points où il se sépare du plugin officiel :

* **les adresses publiques sont plurielles.** Le SDK expose `public_ips`, une
  liste dont chaque entrée porte sa famille. Le plugin officiel ne lit que
  `public_ip` et `ipv6`, donc une seule adresse par famille ;
* **les cartes réseau privées ne déclenchent aucun appel.** Elles sont déjà
  dans la réponse ; la jointure avec IPAM se fait ensuite, en mémoire.
"""

from __future__ import annotations

from typing import Any

from ..errors import AuthenticationFailed, ProductUnavailable, classify
from ..models import InventoryHost, ProviderResult
from ..network import NicRef, attach, flatten
from .base import SCALEWAY_ZONES, DiscoveryContext, region_of

#: Mesurées sur le contrat OpenAPI d'Instance versionné dans ce dépôt.
ZONES: tuple[str, ...] = SCALEWAY_ZONES

#: Ce qui n'appartient qu'à Instance, exposé sous son propre préfixe plutôt
#: que versé dans l'espace global des hostvars.
METADATA_FIELDS: tuple[str, ...] = (
    "commercial_type",
    "hostname",
    "arch",
    "boot_type",
    "dynamic_ip_required",
    "routed_ip_enabled",
)


def _texte(valeur: Any) -> str | None:
    """Un enum du SDK rendu en chaîne, sans supposer sa forme."""
    if valeur is None:
        return None
    return getattr(valeur, "value", None) or str(valeur)


def _public_addresses(server: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Toutes les adresses publiques, par famille.

    `public_ips` est la source moderne ; `public_ip` et `ipv6` sont les champs
    historiques, gardés en repli pour les SDK plus anciens.
    """
    ipv4: list[str] = []
    ipv6: list[str] = []

    for entree in getattr(server, "public_ips", None) or ():
        adresse = getattr(entree, "address", None)
        if not adresse:
            continue
        famille = _texte(getattr(entree, "family", None)) or ""
        (ipv6 if "6" in famille else ipv4).append(str(adresse))

    if not ipv4:
        historique = getattr(server, "public_ip", None)
        if historique is not None and getattr(historique, "address", None):
            ipv4.append(str(historique.address))
    if not ipv6:
        historique = getattr(server, "ipv6", None)
        if historique is not None and getattr(historique, "address", None):
            ipv6.append(str(historique.address))

    return tuple(ipv4), tuple(ipv6)


def normalize(server: Any, context: DiscoveryContext) -> InventoryHost:
    """Traduit un serveur Instance en modèle normalisé."""
    zone = _texte(getattr(server, "zone", None))
    nics = tuple(
        NicRef(
            id=str(nic.id),
            private_network_id=getattr(nic, "private_network_id", None),
            mac_address=getattr(nic, "mac_address", None),
        )
        for nic in getattr(server, "private_nics", None) or ()
        if getattr(nic, "id", None)
    )

    rattachements = attach(nics, context.network) if context.network is not None else ()
    prive_v4, prive_v6 = flatten(rattachements)
    public_v4, public_v6 = _public_addresses(server)

    return InventoryHost(
        id=str(server.id),
        product="instance",
        name=getattr(server, "name", None) or getattr(server, "hostname", None),
        organization_id=getattr(server, "organization", None),
        project_id=getattr(server, "project", None),
        region=region_of(zone),
        zone=zone,
        state=_texte(getattr(server, "state", None)),
        tags=tuple(getattr(server, "tags", None) or ()),
        public_ipv4=public_v4,
        public_ipv6=public_v6,
        private_ipv4=prive_v4,
        private_ipv6=prive_v6,
        private_networks=rattachements,
        metadata={
            champ: _texte(getattr(server, champ, None))
            for champ in METADATA_FIELDS
            if getattr(server, champ, None) is not None
        },
        raw=server if context.include_raw else None,
    )


class InstanceProvider:
    """Découvre les Instances des zones demandées."""

    name = "instance"

    #: Instance porte `private_nics`, que la jointure IPAM complète.
    joins_private_networks = True

    def __init__(self, api: Any) -> None:
        self._api = api

    def discover(self, context: DiscoveryContext) -> ProviderResult:
        """Une liste par zone, et par état si des états sont demandés.

        L'état est un enum côté API : filtrer sur plusieurs états demande donc
        une requête par état. Le filtrage par tags et par projet, lui, tient
        dans la même requête.
        """
        hosts: list[InventoryHost] = []
        avertissements: list[str] = []
        erreurs: list[str] = []
        appels = 0

        etats: tuple[str | None, ...] = context.states or (None,)
        projets: tuple[str | None, ...] = context.project_ids or (None,)

        for zone in context.scoped_zones(ZONES):
            for etat in etats:
                for projet in projets:
                    try:
                        appels += 1
                        trouves = self._api.list_servers_all(
                            zone=zone,
                            tags=list(context.tags) or None,
                            state=etat,
                            project=projet,
                            organization=context.single_organization(),
                        )
                    except Exception as erreur:
                        categorie = classify(getattr(erreur, "status_code", None), str(erreur))
                        if categorie is AuthenticationFailed:
                            # Fatal partout : aucune zone, aucun produit ne peut
                            # aboutir. Continuer produirait un inventaire vide
                            # qui se présente comme complet.
                            raise AuthenticationFailed(str(erreur)) from erreur
                        message = f"{self.name} {zone} : {erreur}"
                        if categorie is ProductUnavailable:
                            avertissements.append(f"{self.name} n'est pas servi dans {zone}")
                        else:
                            erreurs.append(f"{categorie.__name__} : {message}")
                        continue

                    hosts.extend(normalize(serveur, context) for serveur in trouves)

        # Trié par identifiant : l'ordre décide de la désambiguïsation des noms,
        # donc il doit être le même d'une exécution à l'autre.
        return ProviderResult(
            hosts=tuple(sorted(hosts, key=lambda h: h.id)),
            warnings=tuple(avertissements),
            errors=tuple(erreurs),
            api_calls=appels,
        )
