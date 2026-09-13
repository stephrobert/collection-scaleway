# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ce qui a changé entre deux lectures, et ce dont on ne peut rien dire.

Un rapport qui annonce chaque matin le même nombre de ressources cesse d'être lu
au troisième matin. La question utile est « pourquoi y en a-t-il deux de plus
aujourd'hui », et elle demande deux instantanés plutôt qu'un.

**Une zone n'est comparable que si les deux instantanés l'ont mesurée.** C'est le
piège central de cette fonction, et il est plus coûteux ici que partout ailleurs
dans ce dépôt : une zone qui n'a pas répondu ce matin ferait apparaître tout ce
qu'elle porte comme supprimé, et une zone qu'on a simplement cessé de lire ferait
exactement la même chose. Le rapport annoncerait la disparition d'un parc, et il
serait parfaitement plausible.

**`last_change` ne déclenche pas un changement.** C'est un témoin, pas une
propriété du parc : une ligne de diff qui ne montre qu'un horodatage qui bouge ne
donne d'action à personne. Une ressource dont c'est la seule différence est donc
comptée à part, sous son propre nom, plutôt que noyée dans les changements ou
passée sous silence : quelque chose a bougé hors de ce que cette forme observe,
et c'est une information même si ce n'en est pas une sur laquelle agir.

ADR-021 porte la clé, sa mesure et sa date.
"""

from __future__ import annotations

from ansible.errors import AnsibleFilterError

try:  # pragma: no cover - le chemin d'import diffère entre collection et tests
    from ansible_collections.stephrobert.scaleway.plugins.filter.fleet_snapshot import (
        snapshot_read,
    )
except ImportError:  # pragma: no cover
    from .fleet_snapshot import snapshot_read  # type: ignore[no-redef]

DOCUMENTATION = r"""
name: fleet_diff
short_description: What changed between two observed snapshots
description:
  - Compares two snapshots and reports what appeared, what went away, what
    changed and how many resources did not move.
  - >-
    Only compares a zone both snapshots measured. A zone that did not answer,
    and a zone that was simply not read this time, would both make everything it
    holds look removed.
  - >-
    Never triggers a change on the last-change timestamp alone. It is a witness
    rather than a property, and a diff line showing only a timestamp gives
    nobody an action.
options:
  _input:
    description: The earlier snapshot.
    type: dict
    required: true
  after:
    description: The later snapshot, the one to compare against.
    type: dict
    required: true
"""

RETURN = r"""
_value:
  description: What changed, what did not, and what could not be compared.
  type: dict
"""

EXAMPLES = r"""
- name: What moved since yesterday
  ansible.builtin.set_fact:
    changements: >-
      {{ hier | stephrobert.scaleway.fleet_diff(after=aujourdhui) }}
"""

#: Les champs sur lesquels un changement se déclare. `kind` et `id` sont la clé,
#: donc hors comparaison ; `last_change` est un témoin, traité à part.
CHAMPS_COMPARES = ("name", "zone", "state", "tags", "public_addresses")

#: Ce qu'on répond à « pourquoi cette zone n'est-elle pas comparée ». Chaque
#: raison est distincte d'une autre, et c'est voulu : « elle n'a pas répondu » et
#: « on ne l'a pas lue » mènent à des actions différentes.
RAISONS = {
    "muette_avant": "did not answer in the earlier snapshot",
    "muette_apres": "did not answer in the later snapshot",
    "absente_avant": "not read in the earlier snapshot",
    "absente_apres": "not read in the later snapshot",
}


def _cle(ressource: dict) -> tuple[str, str]:
    return (str(ressource.get("kind")), str(ressource.get("id")))


def _zones_incomparables(avant: dict, apres: dict) -> dict[str, str]:
    """Les zones dont on ne peut rien conclure, chacune avec sa raison.

    Une zone doit être **mesurée des deux côtés**. Le cas qui se voit mal est le
    quatrième : une zone que le premier instantané a lue et que le second n'a
    même pas demandée. Elle n'apparaît dans aucun `zones_unmeasured`, puisque
    personne n'a échoué à la lire, et tout ce qu'elle porte passerait pour
    supprimé.
    """
    mesurees_avant = set(avant["zones_measured"])
    mesurees_apres = set(apres["zones_measured"])
    muettes_avant = set(avant["zones_unmeasured"])
    muettes_apres = set(apres["zones_unmeasured"])

    raisons: dict[str, str] = {}
    for zone in muettes_avant:
        raisons[zone] = RAISONS["muette_avant"]
    for zone in muettes_apres:
        raisons.setdefault(zone, RAISONS["muette_apres"])
    for zone in mesurees_avant - mesurees_apres:
        raisons.setdefault(zone, RAISONS["absente_apres"])
    for zone in mesurees_apres - mesurees_avant:
        raisons.setdefault(zone, RAISONS["absente_avant"])
    return dict(sorted(raisons.items()))


def _ecarts(avant: dict, apres: dict) -> dict[str, dict[str, object]]:
    """Champ par champ, ce qui diffère. `last_change` n'y déclenche rien."""
    return {
        champ: {"before": avant.get(champ), "after": apres.get(champ)}
        for champ in CHAMPS_COMPARES
        if avant.get(champ) != apres.get(champ)
    }


def fleet_diff(avant: object, after: object) -> dict[str, object]:
    """Ce qui a changé, ce qui n'a pas bougé, et ce qu'on n'a pas pu comparer."""
    premier = snapshot_read(avant)
    second = snapshot_read(after)

    incomparables = _zones_incomparables(premier, second)
    comparables = sorted(
        (set(premier["zones_measured"]) & set(second["zones_measured"]))
        - set(incomparables)
    )

    def retenues(instantane: dict) -> dict[tuple[str, str], dict]:
        return {
            _cle(ressource): ressource
            for ressource in instantane["resources"]
            if ressource.get("zone") in comparables
        }

    ancien, nouveau = retenues(premier), retenues(second)

    apparues = sorted(set(nouveau) - set(ancien))
    disparues = sorted(set(ancien) - set(nouveau))
    communes = sorted(set(ancien) & set(nouveau))

    changees: list[dict[str, object]] = []
    inchangees = 0
    hors_forme = 0
    for cle in communes:
        ecarts = _ecarts(ancien[cle], nouveau[cle])
        if ecarts:
            changees.append(
                {
                    "kind": cle[0],
                    "id": cle[1],
                    "name": nouveau[cle].get("name"),
                    "fields": ecarts,
                }
            )
        elif ancien[cle].get("last_change") != nouveau[cle].get("last_change"):
            hors_forme += 1
        else:
            inchangees += 1

    # Combien de ressources les instantanés portent dans les zones qu'on n'a pas
    # pu comparer. Le compte est ce qui empêche de lire « aucun changement »
    # quand la vérité est « on n'a rien pu regarder ».
    ecartees = sum(
        1
        for instantane in (premier, second)
        for ressource in instantane["resources"]
        if ressource.get("zone") in incomparables
    )

    return {
        "captured_before": premier["captured_at"],
        "captured_after": second["captured_at"],
        "zones_compared": comparables,
        "zones_not_compared": incomparables,
        "resources_not_compared": ecartees,
        "new": [nouveau[cle] for cle in apparues],
        "removed": [ancien[cle] for cle in disparues],
        "changed": changees,
        "unchanged": inchangees,
        # Nommé plutôt que compté avec les autres : quelque chose a bougé hors de
        # ce que cette forme observe, ce qui n'est ni un changement sur lequel
        # agir ni une absence de changement.
        "changed_outside_this_shape": hors_forme,
    }


def diff_verdict(diff: object) -> str:
    """Le niveau que ce diff mérite, calculé et jamais passé en paramètre.

    Un outil récurrent qui écrit « tout va bien » tous les matins finit ignoré.
    Trois niveaux, et celui du milieu est le seul qui demande de lire.

    **Une mesure impossible vaut `action_required`**, au même rang qu'un
    changement. Une zone muette n'est pas une bonne nouvelle, et la présenter
    comme un parc calme est le vert sur zéro fichier examiné.
    """
    if not isinstance(diff, dict):
        raise AnsibleFilterError(
            f"un diff est un dictionnaire, pas {type(diff).__name__}"
        )
    if diff.get("zones_not_compared"):
        return "action_required"
    if diff.get("new") or diff.get("removed") or diff.get("changed"):
        return "changed"
    return "quiet"


class FilterModule:
    """Les filtres de comparaison."""

    def filters(self) -> dict[str, object]:
        return {"fleet_diff": fleet_diff, "diff_verdict": diff_verdict}
