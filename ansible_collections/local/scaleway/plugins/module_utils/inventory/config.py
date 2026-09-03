# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ce que l'utilisateur a demandé, lu une fois et validé une fois.

Le plugin lit ses options par `self.get_option` ; cette couche les transforme
en objets typés que les autres couches savent consommer. Elle ne connaît ni
Ansible ni le SDK, donc elle se teste avec un simple dictionnaire.

Elle porte aussi la clé de cache. Le plugin officiel n'y met que le chemin du
fichier d'inventaire : deux exécutions avec des profils, des projets ou des
filtres différents partagent alors le même cache. Ici, tout ce qui change le
résultat entre dans la clé.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from .address import DEFAULT_PRIORITY, FAMILIES, AddressPolicy
from .filtering import Filters
from .groups import AXES

#: Les axes de groupes proposés par défaut. Assez pour reconnaître son parc,
#: pas assez pour produire des centaines de groupes vides.
DEFAULT_GROUP_BY: tuple[str, ...] = ("product", "project", "region", "zone")

#: Les sources de nom d'hôte par défaut. Le nom d'abord, l'identifiant en
#: dernier recours : un nom d'hôte qui est une adresse IP, comme le fait le
#: plugin officiel, change dès que l'adresse change.
DEFAULT_HOSTNAMES: tuple[str, ...] = ("name", "id")


class ConfigError(ValueError):
    """La configuration demande quelque chose que le plugin ne sait pas faire."""


@dataclass(frozen=True)
class InventoryConfig:
    """La configuration entière, sous une forme que les couches consomment."""

    products: tuple[str, ...]
    zones: tuple[str, ...]
    regions: tuple[str, ...]
    project_ids: tuple[str, ...]
    organization_ids: tuple[str, ...]
    hostnames: tuple[str, ...]
    address: AddressPolicy
    require_address: bool
    group_by: tuple[str, ...]
    filters: Filters
    include_raw: bool
    strict: bool

    def cache_fingerprint(self, profile: str | None, api_url: str | None) -> str:
        """Une empreinte de tout ce qui change le résultat.

        Deux configurations différentes ne doivent jamais partager un
        inventaire en cache, même depuis le même fichier.
        """
        materiel = {
            "profile": profile,
            "api_url": api_url,
            "products": self.products,
            "zones": self.zones,
            "regions": self.regions,
            "projects": self.project_ids,
            "organizations": self.organization_ids,
            "hostnames": self.hostnames,
            "address": [self.address.priority, self.address.private_network],
            "group_by": self.group_by,
            "filters": [
                self.filters.organizations,
                self.filters.tags,
                self.filters.tags_match,
                self.filters.states,
                self.filters.exclude_tags,
                self.filters.exclude_states,
            ],
            "include_raw": self.include_raw,
            # `strict` décide si une découverte partielle échoue ou passe : il
            # change donc le résultat, et il doit entrer dans la clé. Sans lui,
            # un inventaire incomplet enregistré en mode tolérant était
            # resservi tel quel à une exécution qui demandait un refus, et
            # `_collect()` n'étant pas rejoué, les erreurs ne provoquaient plus
            # rien. Mesuré : les deux empreintes étaient identiques.
            "strict": self.strict,
        }
        serialise = json.dumps(materiel, sort_keys=True, default=list)
        return hashlib.sha256(serialise.encode("utf-8")).hexdigest()[:16]


def _liste(valeur: Any) -> tuple[str, ...]:
    if valeur is None:
        return ()
    if isinstance(valeur, str):
        return (valeur,)
    return tuple(str(item) for item in valeur)


def from_options(
    get_option: Callable[[str], Any],
    known_products: tuple[str, ...],
) -> InventoryConfig:
    """Lit et valide les options, et refuse ce qu'elle ne sait pas faire.

    Un nom inconnu dans `products`, `group_by` ou `address_priority` est une
    faute de configuration. L'ignorer produirait un inventaire silencieusement
    différent de ce qui a été demandé.
    """
    produits = _liste(get_option("products")) or ("all",)
    if produits == ("all",):
        produits = known_products
    inconnus = sorted(set(produits) - set(known_products))
    if inconnus:
        raise ConfigError(f"produit(s) inconnu(s) : {inconnus}. Connus : {list(known_products)}")

    axes = _liste(get_option("group_by")) or DEFAULT_GROUP_BY
    hors_axes = sorted(set(axes) - set(AXES))
    if hors_axes:
        raise ConfigError(f"axe(s) de groupe inconnu(s) : {hors_axes}. Connus : {list(AXES)}")

    priorite = _liste(get_option("address_priority")) or DEFAULT_PRIORITY
    hors_familles = sorted(set(priorite) - set(FAMILIES))
    if hors_familles:
        raise ConfigError(
            f"famille(s) d'adresse inconnue(s) : {hors_familles}. Connues : {list(FAMILIES)}"
        )

    correspondance = get_option("tags_match") or "any"
    if correspondance not in ("any", "all"):
        raise ConfigError(f"tags_match vaut '{correspondance}', attendu 'any' ou 'all'")

    adresse = get_option("address") or {}
    return InventoryConfig(
        products=tuple(produits),
        zones=_liste(get_option("zones")),
        regions=_liste(get_option("regions")),
        project_ids=_liste(get_option("projects")),
        organization_ids=_liste(get_option("organizations")),
        hostnames=_liste(get_option("hostnames")) or DEFAULT_HOSTNAMES,
        address=AddressPolicy(
            priority=tuple(priorite),
            private_network=adresse.get("private_network") or adresse.get("private_network_id"),
        ),
        require_address=bool(get_option("require_address")),
        group_by=tuple(axes),
        filters=Filters(
            organizations=_liste(get_option("organizations")),
            tags=_liste(get_option("tags")),
            tags_match=correspondance,
            states=_liste(get_option("states")),
            exclude_tags=_liste((get_option("exclude") or {}).get("tags")),
            exclude_states=_liste((get_option("exclude") or {}).get("states")),
        ),
        include_raw=bool(get_option("include_raw")),
        strict=bool(get_option("strict")),
    )
