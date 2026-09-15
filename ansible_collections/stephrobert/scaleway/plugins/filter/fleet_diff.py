# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ce qui a changé entre deux lectures, et ce dont on ne peut rien dire.

Un rapport qui annonce chaque matin le même nombre de ressources cesse d'être lu
au troisième matin. La question utile est « pourquoi y en a-t-il deux de plus
aujourd'hui », et elle demande deux instantanés plutôt qu'un.

**Une portée n'est comparable que si les deux instantanés l'ont mesurée.** C'est le
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

#: Les champs communs sur lesquels un changement se déclare. `kind` et `id` sont
#: la clé, donc hors comparaison ; `last_change` est un témoin, traité à part ;
#: `scope_type` accompagne `scope` et ne bouge jamais seul.
CHAMPS_COMPARES = ("name", "scope", "state", "tags", "public_addresses")

#: Les champs propres à un produit qu'il faut comparer **en plus** des communs.
#:
#: **Dérivés de ce que le normaliseur produit, jamais listés une seconde fois.**
#: Une liste globale et fermée laissait un cluster passer de 1.36 à 1.37 sans que
#: le diff dise quoi avait changé : il le rangeait dans
#: `changed_outside_this_shape`, alors que la version de Kubernetes est
#: précisément l'un des changements les plus importants à suivre (#274).
#:
#: `versions_behind` et `expires_at` n'y sont pas : ils se déduisent du
#: catalogue des versions offertes, qui bouge sans que la ressource bouge. Un
#: cluster immobile verrait son retard changer tout seul, et le diff
#: annoncerait un changement que personne n'a fait.
TEMOINS = ("last_change", "versions_behind", "expires_at")

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


def _cle_portee(portee: dict) -> tuple[str, str]:
    """Le couple qui identifie une portée. Deux types peuvent porter un nom voisin."""
    return (str(portee.get("type")), str(portee.get("name")))


def _portees_incomparables(avant: dict, apres: dict) -> dict[str, str]:
    """Les zones dont on ne peut rien conclure, chacune avec sa raison.

    Une zone doit être **mesurée des deux côtés**. Le cas qui se voit mal est le
    quatrième : une zone que le premier instantané a lue et que le second n'a
    même pas demandée. Elle n'apparaît dans aucun `scopes_unmeasured`, puisque
    personne n'a échoué à la lire, et tout ce qu'elle porte passerait pour
    supprimé.
    """
    mesurees_avant = {_cle_portee(p) for p in avant["scopes_measured"]}
    mesurees_apres = {_cle_portee(p) for p in apres["scopes_measured"]}
    muettes_avant = {_cle_portee(p) for p in avant["scopes_unmeasured"]}
    muettes_apres = {_cle_portee(p) for p in apres["scopes_unmeasured"]}

    # La clé lisible porte le type : `region/fr-par` et `zone/fr-par-1` ne se
    # confondent pas dans un rapport, là où les deux noms nus se ressemblent.
    raisons: dict[str, str] = {}
    for portee in muettes_avant:
        raisons["/".join(portee)] = RAISONS["muette_avant"]
    for portee in muettes_apres:
        raisons.setdefault("/".join(portee), RAISONS["muette_apres"])
    for portee in mesurees_avant - mesurees_apres:
        raisons.setdefault("/".join(portee), RAISONS["absente_apres"])
    for portee in mesurees_apres - mesurees_avant:
        raisons.setdefault("/".join(portee), RAISONS["absente_avant"])
    return dict(sorted(raisons.items()))


def _champs_a_comparer(kind: str) -> tuple[str, ...]:
    """Les champs communs, plus ceux que ce produit seul porte, moins les témoins.

    Dérivé de ce que le normaliseur déclare plutôt que listé ici : deux listes se
    contrediraient, et c'est la seconde qui oublierait le champ neuf.
    """
    try:
        from ansible_collections.stephrobert.scaleway.plugins.filter.resource_facts import (
            SUPPLEMENTS,
        )
    except ImportError:  # pragma: no cover
        from .resource_facts import SUPPLEMENTS  # type: ignore[no-redef]

    propres = tuple(
        champ for champ in SUPPLEMENTS.get(kind, ()) if champ not in TEMOINS
    )
    return CHAMPS_COMPARES + propres


def _ecarts(avant: dict, apres: dict) -> dict[str, dict[str, object]]:
    """Champ par champ, ce qui diffère. Un témoin n'y déclenche rien."""
    return {
        champ: {"before": avant.get(champ), "after": apres.get(champ)}
        for champ in _champs_a_comparer(str(apres.get("kind") or avant.get("kind") or ""))
        if avant.get(champ) != apres.get(champ)
    }


def fleet_diff(avant: object, after: object) -> dict[str, object]:
    """Ce qui a changé, ce qui n'a pas bougé, et ce qu'on n'a pas pu comparer."""
    premier = snapshot_read(avant)
    second = snapshot_read(after)

    incomparables = _portees_incomparables(premier, second)
    # Les portées mesurées des deux côtés, moins celles dont on ne peut rien
    # conclure. La comparaison porte sur le couple `(type, nom)` : une région et
    # une zone de noms voisins ne sont pas la même portée.
    comparables = {
        _cle_portee(portee)
        for portee in premier["scopes_measured"]
        if _cle_portee(portee) in {_cle_portee(p) for p in second["scopes_measured"]}
    } - {tuple(cle.split("/", 1)) for cle in incomparables}

    def retenues(instantane: dict) -> dict[tuple[str, str], dict]:
        return {
            _cle(ressource): ressource
            for ressource in instantane["resources"]
            if (str(ressource.get("scope_type")), str(ressource.get("scope")))
            in comparables
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
        if f"{ressource.get('scope_type')}/{ressource.get('scope')}" in incomparables
    )

    return {
        "captured_before": premier["captured_at"],
        "captured_after": second["captured_at"],
        "scopes_compared": sorted("/".join(portee) for portee in comparables),
        "scopes_not_compared": incomparables,
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
    if diff.get("scopes_not_compared"):
        return "action_required"
    if diff.get("new") or diff.get("removed") or diff.get("changed"):
        return "changed"
    return "quiet"


class FilterModule:
    """Les filtres de comparaison."""

    def filters(self) -> dict[str, object]:
        return {"fleet_diff": fleet_diff, "diff_verdict": diff_verdict}
