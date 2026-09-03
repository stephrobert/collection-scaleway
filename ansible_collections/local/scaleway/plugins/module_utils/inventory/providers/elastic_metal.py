# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le provider Elastic Metal.

Il n'a rien en commun avec Instance dans le SDK, et tout en commun dans le
modèle normalisé. C'est la démonstration que le cœur ne connaît aucun produit :
ce fichier n'a demandé aucune modification ailleurs.

Une différence de forme mérite d'être nommée, parce que c'est elle qui aurait
fait diverger un plugin monolithique : **les adresses arrivent en liste**, avec
leur famille dans un champ, là où Instance porte deux champs singuliers. Le
modèle normalisé porte des tuples par famille, donc les deux formes y entrent
sans cas particulier.

**Ce provider n'est pas jouable contre l'émulateur** : feint ne sert aucune
route Elastic Metal, et ne le fera pas à court terme (feint#631). Il est donc
prouvé par des réponses simulées, ce qui est aussi la raison pour laquelle il
ne partage aucun état avec le reste.
"""

from __future__ import annotations

from typing import Any

from ..errors import AuthenticationFailed, ProductUnavailable, classify
from ..models import InventoryHost, ProviderResult
from .base import SCALEWAY_ZONES, DiscoveryContext, region_of

#: Candidates, et non mesurées : ce dépôt ne versionne pas le contrat Elastic
#: Metal. Une zone où le produit n'existe pas se retire d'elle-même, parce que
#: l'API le dit et que le provider le classe en « produit indisponible ».
ZONES: tuple[str, ...] = SCALEWAY_ZONES

#: Ce qui n'appartient qu'à Elastic Metal.
METADATA_FIELDS: tuple[str, ...] = ("offer_name", "offer_id", "description", "ping_status")

#: Le champ `version` d'une adresse, tel que le SDK l'écrit.
IPV6_MARKERS: tuple[str, ...] = ("i_pv6", "ipv6", "IPv6")


def _texte(valeur: Any) -> str | None:
    if valeur is None:
        return None
    return getattr(valeur, "value", None) or str(valeur)


def _addresses(server: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Sépare les adresses par famille.

    Elastic Metal rend une liste où chaque entrée porte sa version. Le plugin
    officiel garde la dernière de chaque famille ; ici on les garde toutes,
    parce qu'une machine peut en avoir plusieurs et que le modèle sait le dire.
    """
    ipv4: list[str] = []
    ipv6: list[str] = []
    for entree in getattr(server, "ips", None) or ():
        adresse = getattr(entree, "address", None)
        if not adresse:
            continue
        version = _texte(getattr(entree, "version", None)) or ""
        cible = ipv6 if any(marqueur in version for marqueur in IPV6_MARKERS) else ipv4
        cible.append(str(adresse))
    return tuple(ipv4), tuple(ipv6)


def normalize(server: Any, context: DiscoveryContext) -> InventoryHost:
    """Traduit un serveur Elastic Metal en modèle normalisé."""
    zone = _texte(getattr(server, "zone", None))
    public_v4, public_v6 = _addresses(server)

    return InventoryHost(
        id=str(server.id),
        product="elastic_metal",
        name=getattr(server, "name", None),
        organization_id=getattr(server, "organization_id", None),
        project_id=getattr(server, "project_id", None),
        region=region_of(zone),
        zone=zone,
        state=_texte(getattr(server, "status", None)),
        tags=tuple(getattr(server, "tags", None) or ()),
        public_ipv4=public_v4,
        public_ipv6=public_v6,
        metadata={
            champ: _texte(getattr(server, champ, None))
            for champ in METADATA_FIELDS
            if getattr(server, champ, None) is not None
        },
        raw=server if context.include_raw else None,
    )


class ElasticMetalProvider:
    """Découvre les serveurs Elastic Metal des zones demandées."""

    name = "elastic_metal"

    #: Elastic Metal ne rend que des adresses publiques : rien à joindre.
    joins_private_networks = False

    def __init__(self, api: Any) -> None:
        self._api = api

    def discover(self, context: DiscoveryContext) -> ProviderResult:
        """Une liste par zone, filtrée côté API sur les tags et le projet.

        L'API accepte aussi un filtre `status`, mais il ne porte pas les mêmes
        valeurs que celui d'Instance : le filtrage par état se fait donc côté
        client, sur le modèle normalisé, où il a le même sens pour tous les
        produits.
        """
        hosts: list[InventoryHost] = []
        avertissements: list[str] = []
        erreurs: list[str] = []
        appels = 0

        projets: tuple[str | None, ...] = context.project_ids or (None,)

        for zone in context.scoped_zones(ZONES):
            for projet in projets:
                try:
                    appels += 1
                    trouves = self._api.list_servers_all(
                        zone=zone,
                        tags=list(context.tags) or None,
                        project_id=projet,
                        organization_id=context.single_organization(),
                    )
                except Exception as erreur:
                    categorie = classify(getattr(erreur, "status_code", None), str(erreur))
                    if categorie is AuthenticationFailed:
                        # Fatal partout : aucune zone, aucun produit ne peut
                        # aboutir. Continuer produirait un inventaire vide qui
                        # se présente comme complet.
                        raise AuthenticationFailed(str(erreur)) from erreur
                    if categorie is ProductUnavailable:
                        avertissements.append(f"{self.name} n'est pas servi dans {zone}")
                    else:
                        erreurs.append(f"{categorie.__name__} : {self.name} {zone} : {erreur}")
                    continue

                hosts.extend(normalize(serveur, context) for serveur in trouves)

        return ProviderResult(
            hosts=tuple(sorted(hosts, key=lambda h: h.id)),
            warnings=tuple(avertissements),
            errors=tuple(erreurs),
            api_calls=appels,
        )
