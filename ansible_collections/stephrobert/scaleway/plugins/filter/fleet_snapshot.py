# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Un instantané du parc, que la collection produit et ne stocke pas.

Un rapport qui dit chaque matin combien il y a de ressources cesse d'être lu au
troisième matin. Ce qu'on veut savoir est ce qui a changé, et comparer demande
deux lectures dans la même forme, avec une clé.

**La clé est `(kind, id)`, et c'est une mesure, pas un choix de style.** Deux
machines peuvent porter le même nom dans la même zone : l'API accepte les deux
créations et rend deux identifiants distincts. Un instantané clé sur le nom
fusionnerait ces deux machines en une ressource qui « a changé », et le rapport
dirait le contraire de la vérité. Le nom reste, comme étiquette lisible, pas
comme identité. ADR-021 porte la mesure et sa date.

**Le stockage appartient à l'appelant.** Artefact de CI, objet sur un stockage
d'objets, dépôt git, système de fichiers : la collection rend l'instantané et
s'arrête là. Elle ne devient ni une CMDB ni un service caché, et cette limite
est la décision, pas une étape vers autre chose (#231).

**`zones_unmeasured` vit dans l'instantané lui-même.** Rien n'a été mesuré n'est
pas rien n'a été trouvé, et un diff calculé sans cette information annoncerait la
disparition d'un parc entier le jour où une zone ne répond pas.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from ansible.errors import AnsibleFilterError

DOCUMENTATION = r"""
name: fleet_snapshot
short_description: Build a versioned snapshot of what a read observed
description:
  - Turns normalised resources into a snapshot the caller stores wherever it
    wants, so a later run can say what changed rather than what exists.
  - >-
    Keys every resource on its kind and its identifier. A name is not an
    identity, because two machines can carry the same name in one zone.
  - Carries the zones that did not answer, because a diff computed without them
    would announce the disappearance of a whole fleet.
options:
  _input:
    description: The normalised resources, as C(resource_facts) returns them.
    type: list
    required: true
  zones_measured:
    description: The zones that answered.
    type: list
    required: true
  zones_unmeasured:
    description: The zones that were asked and did not answer.
    type: list
    default: []
  captured_at:
    description: When the read started, in UTC.
    type: str
    required: true
  collection_version:
    description: The version of this collection that produced the snapshot.
    type: str
    required: true
"""

RETURN = r"""
_value:
  description: The snapshot, ready to be serialised by the caller.
  type: dict
"""

EXAMPLES = r"""
- name: Keep what this read observed
  ansible.builtin.set_fact:
    snapshot: >-
      {{ faits | stephrobert.scaleway.fleet_snapshot(
           zones_measured=zones_qui_ont_repondu,
           zones_unmeasured=zones_muettes,
           captured_at=debut,
           collection_version=version) }}
"""

#: La version de la forme, et non celle de la collection. Un instantané
#: d'aujourd'hui sera comparé à un instantané d'il y a trois mois : un lecteur
#: doit refuser ce qu'il ne sait pas lire plutôt que de le lire de travers.
#:
#: Elle n'avance que lorsqu'un champ change de sens ou disparaît. Un champ
#: ajouté ne la fait pas bouger : un lecteur qui l'ignore lit encore juste.
SCHEMA_VERSION = 1

#: Ce qu'un instantané porte à sa racine. Un lecteur les exige tous : un
#: instantané tronqué et un parc vide se ressemblent trop pour qu'on les
#: confonde, et le second est une information alors que le premier est une panne.
ENTETE = (
    "schema_version",
    "captured_at",
    "collection_version",
    "zones_measured",
    "zones_unmeasured",
    "resources",
)


#: Où la version de la collection se lit, selon qu'on tourne depuis le dépôt ou
#: depuis une collection installée. Les deux existent pour de vrai :
#: `ansible-galaxy collection install` écrit `MANIFEST.json` et **n'emporte pas**
#: `galaxy.yml`, tandis qu'`ansible-test` et les tests du dépôt travaillent en
#: place, où c'est l'inverse. Chercher un seul des deux marcherait chez celui qui
#: l'a écrit et nulle part ailleurs.
SOURCES_DE_VERSION = (
    ("MANIFEST.json", ("collection_info", "version")),
    ("galaxy.yml", ("version",)),
)


def collection_version(_entree: object = None) -> str | None:
    """La version de cette collection, lue là où elle se trouve vraiment.

    L'entrée est ignorée : un filtre Jinja reçoit toujours la valeur qu'on lui
    passe en premier argument, et celui-ci ne répond qu'à une question sur le
    disque. Un lookup serait plus juste sur le papier, mais un lookup ne peut pas
    vivre dans le même fichier que les filtres qui s'en servent, et deux fichiers
    pour une question sont deux endroits à tenir.

    Rend `None` plutôt qu'une chaîne inventée quand aucune des deux sources n'est
    lisible : un instantané qui mentirait sur son producteur serait pire qu'un
    instantané qui dit ne pas le savoir.
    """
    racine = Path(__file__).resolve().parents[2]
    for nom, chemin in SOURCES_DE_VERSION:
        fichier = racine / nom
        if not fichier.is_file():
            continue
        try:
            charge = (
                json.loads(fichier.read_text(encoding="utf-8"))
                if nom.endswith(".json")
                else yaml.safe_load(fichier.read_text(encoding="utf-8"))
            )
        except (ValueError, yaml.YAMLError):
            continue
        for cle in chemin:
            charge = (charge or {}).get(cle)
        if isinstance(charge, str) and charge:
            return charge
    return None


def _liste(valeur: object, nom: str) -> list:
    if not isinstance(valeur, (list, tuple)):
        raise AnsibleFilterError(
            f"`{nom}` doit être une liste, pas {type(valeur).__name__}"
        )
    return list(valeur)


def fleet_snapshot(
    ressources: object,
    zones_measured: object,
    captured_at: str,
    collection_version: str,
    zones_unmeasured: object = (),
) -> dict[str, object]:
    """L'instantané, trié, et refusant ce qu'on ne pourrait pas comparer."""
    normalisees = _liste(ressources, "les ressources")
    mesurees = sorted(_liste(zones_measured, "zones_measured"))
    muettes = sorted(_liste(zones_unmeasured, "zones_unmeasured"))

    # `all` sur les deux membres, et non la vérité du tuple : `("", "")` est un
    # tuple non vide, donc vrai, et la garde écrite ainsi ne mordait pas. Le
    # refus venait alors du contrôle suivant, avec un message qui ne disait pas
    # la même chose.
    sans_identite = [
        ressource
        for ressource in normalisees
        if not all(_cle_de(ressource, tolerant=True))
    ]
    if sans_identite:
        raise AnsibleFilterError(
            f"{len(sans_identite)} ressource(s) sans `kind` ou sans `id` : un "
            "instantané qui les porte ne peut pas être comparé, et le diff les "
            "verrait apparaître puis disparaître à chaque lecture. Elles "
            "viennent d'un normaliseur, qui refuse déjà ce cas : une charge "
            "utile a donc contourné `resource_facts`."
        )

    # **Un doublon est un refus, pas un dédoublonnage silencieux.** Deux
    # ressources de même clé veulent dire que la même a été lue deux fois, ou que
    # deux lectures ont été concaténées : dans les deux cas le diff qui suivrait
    # compterait faux, et garder « la dernière » choisirait pour l'utilisateur.
    vues: dict[tuple[str, str], int] = {}
    for ressource in normalisees:
        cle = _cle_de(ressource)
        vues[cle] = vues.get(cle, 0) + 1
    doublons = sorted(f"{kind}/{identifiant}" for (kind, identifiant), n in vues.items() if n > 1)
    if doublons:
        raise AnsibleFilterError(
            f"{len(doublons)} ressource(s) lue(s) deux fois : {', '.join(doublons[:5])}. "
            "Un instantané qui les porte fait compter faux au diff, et en garder "
            "une choisirait à la place de l'utilisateur."
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at,
        "collection_version": collection_version,
        "zones_measured": mesurees,
        "zones_unmeasured": muettes,
        # Trié par clé : le même parc doit produire les mêmes octets deux fois,
        # sinon deux instantanés ne se comparent pas et le fichier n'est qu'une
        # décoration. C'est la règle de déterminisme que le générateur applique
        # déjà à ce qu'il écrit.
        "resources": sorted(normalisees, key=_cle_de),
    }


def _cle_de(ressource: object, tolerant: bool = False) -> tuple[str, str]:
    """La clé d'une ressource : son produit et son identifiant.

    `tolerant` sert au contrôle qui cherche les ressources inutilisables : il a
    besoin de les détecter, pas de lever dessus.
    """
    if not isinstance(ressource, dict):
        if tolerant:
            return ("", "")
        raise AnsibleFilterError(
            f"une ressource doit être un dictionnaire, pas {type(ressource).__name__}"
        )
    kind = ressource.get("kind") or ""
    identifiant = ressource.get("id") or ""
    if not (kind and identifiant) and not tolerant:
        raise AnsibleFilterError(f"ressource sans clé : {ressource}")
    return (str(kind), str(identifiant))


def snapshot_read(instantane: object) -> dict[str, object]:
    """Le même instantané, ou un refus qui dit pourquoi.

    Séparé de la construction, parce que ce n'est pas le même moment : on
    construit ce qu'on vient de lire, et on relit ce que quelqu'un a rangé il y
    a trois mois, avec une version de la collection qui n'existait pas.
    """
    if not isinstance(instantane, dict):
        raise AnsibleFilterError(
            f"un instantané est un dictionnaire, pas {type(instantane).__name__}. "
            "Un fichier tronqué ou une lecture ratée arrive sous cette forme."
        )

    manquants = [champ for champ in ENTETE if champ not in instantane]
    if manquants:
        raise AnsibleFilterError(
            f"instantané incomplet, il manque {', '.join(manquants)}. Un fichier "
            "tronqué et un parc vide se ressemblent, et seul le second est une "
            "information."
        )

    vue = instantane["schema_version"]
    if vue != SCHEMA_VERSION:
        raise AnsibleFilterError(
            f"instantané en version {vue}, cette collection lit la version "
            f"{SCHEMA_VERSION}. Comparer deux formes dont l'une porte un champ "
            "de plus produirait des changements qui n'ont pas eu lieu."
        )

    return instantane


class FilterModule:
    """Les filtres d'instantané."""

    def filters(self) -> dict[str, object]:
        return {
            "fleet_snapshot": fleet_snapshot,
            "snapshot_read": snapshot_read,
            "collection_version": collection_version,
        }
