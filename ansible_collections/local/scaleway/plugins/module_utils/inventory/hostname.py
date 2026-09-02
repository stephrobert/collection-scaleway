# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le choix de `inventory_hostname`, et le refus des collisions.

Deux machines Scaleway peuvent porter le même nom : le nom n'est unique ni
dans une zone, ni dans un projet, ni dans une organisation. Un inventaire qui
l'ignore appelle `add_host` deux fois avec la même clé, et la seconde machine
**écrase** la première, ses variables et ses groupes. Sans un mot.

Ce module rend ce cas impossible : le nom retenu est désambiguïsé de façon
déterministe, et la collision est signalée.
"""

from __future__ import annotations

from .models import InventoryHost

#: Les sources acceptées, et ce qu'elles lisent dans le modèle normalisé.
#: `hostname`, `vpc_ipv4` et `vpc_ipv6` sont les noms du plugin officiel :
#: une configuration existante doit continuer de fonctionner.
LEGACY_SOURCES: dict[str, str] = {
    "hostname": "name",
    "vpc_ipv4": "private_ipv4",
    "vpc_ipv6": "private_ipv6",
}

#: Préfixe qui lit un tag de la forme `<clé>=<valeur>`.
TAG_PREFIX = "tag:"


def resolve_source(host: InventoryHost, source: str) -> str | None:
    """La valeur d'une source pour cette machine, ou `None` si elle manque."""
    source = LEGACY_SOURCES.get(source, source)

    if source.startswith(TAG_PREFIX):
        cle = source[len(TAG_PREFIX) :]
        marqueur = f"{cle}="
        for tag in host.tags:
            if tag.startswith(marqueur):
                valeur = tag[len(marqueur) :].strip()
                return valeur or None
        return None

    valeur = getattr(host, source, None)
    if isinstance(valeur, tuple):
        return valeur[0] if valeur else None
    if isinstance(valeur, str):
        return valeur or None
    return None


def pick_hostname(host: InventoryHost, sources: tuple[str, ...]) -> tuple[str, str] | None:
    """Le premier nom disponible, avec la source qui l'a fourni."""
    for source in sources:
        valeur = resolve_source(host, source)
        if valeur:
            return valeur, source
    return None


def assign_hostnames(
    hosts: tuple[InventoryHost, ...],
    sources: tuple[str, ...],
) -> tuple[tuple[tuple[InventoryHost, str], ...], tuple[str, ...]]:
    """Attribue un nom unique à chaque machine, et dit ce qu'il a fallu faire.

    La désambiguïsation est déterministe et documentée : au premier conflit, la
    zone est ajoutée ; si le conflit persiste, l'identifiant. Un identifiant
    Scaleway étant unique, la boucle se termine toujours.

    Les machines sont traitées dans l'ordre reçu, et cet ordre est déterministe
    parce que les providers trient. Deux exécutions produisent donc le même
    inventaire, y compris les noms désambiguïsés.
    """
    attribues: list[tuple[InventoryHost, str]] = []
    avertissements: list[str] = []
    pris: set[str] = set()

    for host in hosts:
        choix = pick_hostname(host, sources)
        if choix is None:
            avertissements.append(
                f"{host.id} ({host.product}) : aucune des sources {list(sources)} "
                "ne donne de nom, machine écartée"
            )
            continue

        nom, source = choix
        if nom not in pris:
            pris.add(nom)
            attribues.append((host, nom))
            continue

        for suffixe in (host.zone, host.id):
            if not suffixe:
                continue
            candidat = f"{nom}_{suffixe}"
            if candidat not in pris:
                pris.add(candidat)
                attribues.append((host, candidat))
                avertissements.append(
                    f"nom '{nom}' déjà pris (source {source}) : {host.id} devient '{candidat}'"
                )
                break
        else:  # pragma: no cover - un identifiant Scaleway est unique
            avertissements.append(f"{host.id} : impossible de désambiguïser '{nom}', écartée")

    return tuple(attribues), tuple(avertissements)
