# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ce qui est nouveau, ce qui persiste, ce qui est résolu.

`fleet_audit` sait dire ce qui ne va pas. Lancé tous les matins, il affiche les
mêmes avertissements, et les gens cessent de les lire. C'est le mode de
défaillance d'un outil récurrent, et il est plus dangereux qu'une panne : il ne
se voit pas.

Trois ensembles, aucune devinette, calculés depuis les identités stables des
constats : présent avant et après, absent avant, absent après.

**Un constat disparu n'est pas un constat résolu.** C'est le refus central de ce
module. Une zone qui n'a pas répondu ce matin fait disparaître tout ce qu'elle
portait, et l'annoncer « résolu » est la pire ligne qu'un tel rapport puisse
écrire : elle dit à quelqu'un que son problème est réglé alors que personne n'a
regardé. Un constat dont la zone n'a pas été mesurée sort donc en non mesuré,
avec ce qui l'y met.

**Un constat excusé n'est pas un constat résolu non plus.** Une exception change
son statut, elle ne fait pas disparaître le problème (#235). Il reste dans
`persisting`, avec son statut, et le rapport le range où l'appelant veut.

**La collection ne tient pas d'historique.** « Première vue il y a quatre jours »
suppose de savoir depuis quand, et cette date vient de l'appelant : elle est
apposée sur les constats neufs et recopiée sur ceux qui persistent, de sorte
qu'elle remonte aussi loin que l'appelant a conservé ses rapports. Si elle n'y
est pas, elle est absente et le rapport le dit, jamais inventée.
"""

from __future__ import annotations

from ansible.errors import AnsibleFilterError

DOCUMENTATION = r"""
name: audit_changes
short_description: What is new, what persists, what is resolved
description:
  - >-
    Compares the findings of two audits by their stable identity, and sorts them
    into new, persisting and resolved. A report that shows the same warnings
    every morning stops being read by the third morning.
  - >-
    A finding that vanished because its zone did not answer never comes out as
    resolved. It comes out as unmeasured, which is not the same thing and does
    not send anybody the message that their problem is fixed.
  - >-
    Stamps C(first_seen) on a new finding and carries it over on a persisting
    one, so the date goes back as far as the caller kept its reports. It is never
    invented when the caller has none.
options:
  _input:
    description: The findings of this run.
    type: list
    required: true
  previous:
    description: >-
      The findings of the previous run, as they were kept. C(none) says there is
      no previous run, which is not the same as a previous run with no findings.
    type: list
    required: false
  zones_measured:
    description: The zones this run read.
    type: list
    required: true
  now:
    description: The reference instant, in UTC.
    type: str
    required: true
"""

RETURN = r"""
_value:
  description: The three sets, what could not be concluded, and their counts.
  type: dict
"""

EXAMPLES = r"""
- name: What moved since the last audit
  ansible.builtin.set_fact:
    changements: >-
      {{ constats | stephrobert.scaleway.audit_changes(
           previous=constats_gardes | default(none),
           zones_measured=zones_lues,
           now=now(utc=true, fmt='%Y-%m-%dT%H:%M:%SZ')) }}
"""

#: Pourquoi un constat disparu n'est pas conclu résolu. Deux raisons, et elles
#: mènent à deux actions différentes : relancer la lecture de la zone, ou
#: réparer un rapport conservé qui ne porte pas assez pour être comparé.
RAISONS = {
    "zone_muette": "its zone was not measured by this run",
    "zone_inconnue": "the kept finding does not say which zone it was in",
}


def _identite(constat: object, quoi: str) -> str:
    """L'identité d'un constat, refusée plutôt que devinée si elle manque.

    Sans identité, un constat ne se compare à rien. Le laisser passer le
    rangerait dans `new` à chaque run, et « nouveau » cesserait de vouloir dire
    quelque chose pour tous les autres.
    """
    if not isinstance(constat, dict):
        raise AnsibleFilterError(
            f"{quoi} porte un {type(constat).__name__}, pas un constat"
        )
    identite = constat.get("id")
    if not identite:
        raise AnsibleFilterError(
            f"{quoi} porte un constat sans `id` : {constat!r}. Sans identité il "
            "se rangerait dans les nouveaux à chaque run, et `nouveau` ne "
            "voudrait plus rien dire pour les autres."
        )
    return str(identite)


def _en_table(constats: object, quoi: str) -> dict[str, dict]:
    """Les constats rangés par identité, avec le refus des doublons.

    Deux constats de même identité dans un même run veulent dire que l'identité
    ne distingue plus ce qu'elle doit distinguer. En garder un au hasard
    rendrait le rapport dépendant de l'ordre de lecture.
    """
    if not isinstance(constats, (list, tuple)):
        raise AnsibleFilterError(
            f"{quoi} est une liste, pas un {type(constats).__name__}"
        )
    table: dict[str, dict] = {}
    for constat in constats:
        identite = _identite(constat, quoi)
        if identite in table:
            raise AnsibleFilterError(
                f"{quoi} porte deux fois l'identité `{identite}`. Une identité "
                "qui ne distingue plus deux constats rendrait le rapport "
                "dépendant de l'ordre de lecture."
            )
        table[identite] = dict(constat)
    return table


def _statut(constat: dict) -> str:
    """Le statut d'un constat, `open` quand aucune exception n'est passée."""
    return str(constat.get("status") or "open")


def audit_changes(
    constats: object,
    zones_measured: object,
    now: str,
    previous: object = None,
) -> dict[str, object]:
    """Les trois ensembles, et ce dont on ne peut rien conclure."""
    if not isinstance(zones_measured, (list, tuple)):
        raise AnsibleFilterError(
            f"les zones mesurées sont une liste, pas un {type(zones_measured).__name__}"
        )
    if not now:
        raise AnsibleFilterError("l'instant de référence est requis")

    actuels = _en_table(constats, "les constats de ce run")
    mesurees = {str(zone) for zone in zones_measured}

    # **Aucun run précédent n'est pas un run précédent sans constat.** Annoncer
    # tout le parc comme nouveau au premier run noierait la première lecture
    # sous ce qu'elle est censée servir à établir ; l'annoncer comme persistant
    # affirmerait l'avoir déjà vu. Le premier run est donc une référence, et il
    # le dit.
    if previous is None:
        return {
            "baseline": True,
            "new": [],
            "persisting": [],
            "resolved": [],
            "unmeasured": [],
            "current": [
                dict(constat, first_seen=now) for constat in actuels.values()
            ],
            "counts": {
                "new": 0,
                "persisting": 0,
                "resolved": 0,
                "unmeasured": 0,
                "current": len(actuels),
            },
        }

    anciens = _en_table(previous, "les constats conservés")

    neufs: list[dict] = []
    persistants: list[dict] = []
    for identite in sorted(set(actuels) - set(anciens)):
        neufs.append(dict(actuels[identite], first_seen=now))
    for identite in sorted(set(actuels) & set(anciens)):
        # **La date du plus ancien des deux, jamais celle d'aujourd'hui.** Elle
        # est recopiée pour remonter aussi loin que l'appelant a conservé ses
        # rapports ; si le constat conservé n'en porte pas, elle est absente et
        # le rapport le dira plutôt que de la fabriquer.
        vue = anciens[identite].get("first_seen")
        constat = dict(actuels[identite])
        if vue:
            constat["first_seen"] = vue
        persistants.append(constat)

    resolus: list[dict] = []
    indecidables: list[dict] = []
    for identite in sorted(set(anciens) - set(actuels)):
        ancien = anciens[identite]
        zone = ancien.get("zone")
        if not zone:
            indecidables.append(dict(ancien, reason=RAISONS["zone_inconnue"]))
        elif str(zone) not in mesurees:
            indecidables.append(dict(ancien, reason=RAISONS["zone_muette"]))
        else:
            # **`seen_resolved_at`, et pas `resolved_at`.** Ce qu'on sait est
            # qu'il n'est plus là à ce run ; le moment où quelqu'un l'a réglé est
            # quelque part entre les deux lectures, et le dater d'aujourd'hui
            # serait un nombre plausible et faux.
            resolus.append(dict(ancien, seen_resolved_at=now))

    return {
        "baseline": False,
        "new": neufs,
        "persisting": persistants,
        "resolved": resolus,
        # **Ni résolus, ni persistants.** Les ranger dans l'un des deux serait
        # une affirmation, et c'est précisément ce qu'on ne peut pas faire ici.
        "unmeasured": indecidables,
        "current": neufs + persistants,
        "counts": {
            "new": len(neufs),
            "persisting": len(persistants),
            "resolved": len(resolus),
            "unmeasured": len(indecidables),
            "current": len(actuels),
        },
    }


# **Il n'y a pas de champ `since`, et c'est délibéré.** « Depuis la dernière
# fois » suppose de savoir quand la dernière fois a eu lieu, et rien ici ne le
# porte : la plus ancienne `first_seen` conservée date le plus vieux constat, pas
# le run précédent, et sur un run où rien n'était neuf elle ne date rien du tout.
# Un appelant qui veut nommer sa référence le fait avec ce qu'il a stocké à côté.


def changes_verdict(changements: object) -> str:
    """Ce que ces changements demandent, calculé et jamais passé en paramètre.

    **Un appelant capable de forcer ce niveau pourrait produire un rapport qui
    se dit calme alors qu'il ne l'est pas**, et c'est exactement ce qu'un outil
    récurrent ne doit pas pouvoir faire.

    `action_required` compte la mesure impossible au même rang qu'un nouveau
    constat bloquant : une zone muette n'est pas une bonne nouvelle, et la
    présenter comme un parc calme est le vert sur zéro fichier examiné.
    """
    if not isinstance(changements, dict):
        raise AnsibleFilterError(
            f"le verdict se calcule sur un résultat d'`audit_changes`, "
            f"pas sur un {type(changements).__name__}"
        )
    if changements.get("baseline"):
        # Une première lecture n'est ni calme ni alarmante : il n'y a rien à
        # quoi la comparer, et le dire est plus utile que de trancher.
        return "baseline"

    if changements.get("unmeasured"):
        return "action_required"
    if any(
        constat.get("severity") == "fail" and _statut(constat) == "open"
        for constat in changements.get("new") or []
    ):
        return "action_required"
    if changements.get("new") or changements.get("resolved"):
        return "changed"
    return "quiet"


class FilterModule:
    """Ce que la collection publie pour comparer deux audits."""

    def filters(self) -> dict[str, object]:
        return {
            "audit_changes": audit_changes,
            "changes_verdict": changes_verdict,
        }
