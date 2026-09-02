# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le provider Apple Silicon.

Troisième forme d'adresse rencontrée, et troisième fois que le modèle
normalisé absorbe la différence sans que le cœur bouge :

    Instance        deux champs singuliers, plus une liste moderne
    Elastic Metal   une liste, chaque entrée porte sa famille
    Apple Silicon   un seul champ, une seule adresse

Deux champs sont propres à ce produit et valent d'être exposés :

* **`ssh_username`.** Aucun autre produit Scaleway ne dit avec quel compte se
  connecter. Il est rangé dans les métadonnées du produit, d'où un `compose`
  peut en faire `ansible_user` sans que le plugin impose ce choix ;
* **`tags`.** Le plugin officiel écrit `tags=["apple_sillicon"]` en dur et jette
  les vrais, de sorte qu'un filtrage par tag perd toutes les machines de ce
  produit. Ici les tags sont ceux de Scaleway.

**Ce provider n'est pas jouable contre l'émulateur** : feint ne sert aucune
route Apple Silicon, et ne le fera pas à court terme (feint#632). Il est prouvé
par des réponses simulées.
"""

from __future__ import annotations

from typing import Any

from ..errors import AuthenticationFailed, ProductUnavailable, classify
from ..models import InventoryHost, ProviderResult
from .base import SCALEWAY_ZONES, DiscoveryContext, region_of

#: Candidates, et non mesurées : ce dépôt ne versionne pas le contrat Apple
#: Silicon. Le produit n'existe que dans quelques zones, et celles où il
#: n'existe pas se retirent d'elles-mêmes.
ZONES: tuple[str, ...] = SCALEWAY_ZONES

#: Ce qui n'appartient qu'à Apple Silicon.
METADATA_FIELDS: tuple[str, ...] = ("ssh_username", "vpc_status", "type_")


def _texte(valeur: Any) -> str | None:
    if valeur is None:
        return None
    return getattr(valeur, "value", None) or str(valeur)


def normalize(server: Any, context: DiscoveryContext) -> InventoryHost:
    """Traduit un serveur Apple Silicon en modèle normalisé."""
    zone = _texte(getattr(server, "zone", None))
    adresse = getattr(server, "ip", None)

    return InventoryHost(
        id=str(server.id),
        product="apple_silicon",
        name=getattr(server, "name", None),
        organization_id=getattr(server, "organization_id", None),
        project_id=getattr(server, "project_id", None),
        region=region_of(zone),
        zone=zone,
        state=_texte(getattr(server, "status", None)),
        tags=tuple(getattr(server, "tags", None) or ()),
        public_ipv4=(str(adresse),) if adresse else (),
        metadata={
            champ: _texte(getattr(server, champ, None))
            for champ in METADATA_FIELDS
            if getattr(server, champ, None) is not None
        },
        raw=server if context.include_raw else None,
    )


class AppleSiliconProvider:
    """Découvre les serveurs Apple Silicon des zones demandées."""

    name = "apple_silicon"

    def __init__(self, api: Any) -> None:
        self._api = api

    def discover(self, context: DiscoveryContext) -> ProviderResult:
        """Une liste par zone et par projet.

        L'API de ce produit **n'accepte ni filtre de tags ni filtre d'état** :
        `list_servers_all` ne prend que la zone, le projet et l'organisation.
        Le filtrage se fait donc entièrement côté client, sur le modèle
        normalisé, et le résultat est le même que pour les autres produits.
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
                    trouves = self._api.list_servers_all(zone=zone, project_id=projet)
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
