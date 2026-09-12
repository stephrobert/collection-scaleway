# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Le résultat d'une opération, dans une forme qu'une machine lit.

Chaque enchaînement livré savait rendre son résultat, et chacun le rendait à sa
façon : « 3 acted on, 1 already off » chez l'un, « 3 rebooted, 0 left alone »
chez l'autre. Tant qu'on lance ces commandes à la main, ça suffit. Dès qu'AWX,
une CI, un ticket ou une supervision veut en faire quelque chose, il faut
analyser une sortie standard, et un analyseur de sortie standard casse au
premier mot reformulé (#206).

**Les comptes se déduisent des noms, ils ne se passent pas à côté.** C'est la
décision qui porte tout le reste : un `changed: 3` transmis en plus de la liste
des machines changées est une seconde source du même fait, et deux sources du
même fait finissent par se contredire. Ici, `changed` **est** la longueur de la
liste, et rien ne peut les désaccorder.

Trois distinctions que ce dépôt a payées, et qu'un champ mal nommé annulerait :

* **`unmeasured` n'est pas zéro.** Une zone qui n'a pas répondu n'a pas été
  mesurée vide. Quand rien n'a pu être examiné, les totaux valent `null` plutôt
  que `0`, comme `fleet_report` le fait déjà et comme le rapport de couverture
  rend `n/a` plutôt que `0.0 %` ;
* **`refused` n'est pas `already_compliant`.** Une machine `locked` a été vue et
  écartée avec sa raison ; une machine déjà dans l'état visé n'avait rien à
  faire. Les confondre ferait passer un obstacle pour un succès ;
* **le mode est porté, jamais deviné.** En répétition, `changed` compte ce qui
  **bougerait**. Un compte rendu qui ne dit pas dans quel mode il a été produit
  a déjà fait lire « machines éteintes » à un opérateur dont les machines
  tournaient.
"""

from __future__ import annotations

from ansible.errors import AnsibleFilterError

DOCUMENTATION = r"""
name: operation_result
short_description: Build the machine-readable result of an operation
description:
  - Returns the common structure every shipped operation emits, so a pipeline,
    a ticket or a monitoring system can read what happened without parsing
    standard output.
  - Counts are derived from the names rather than passed alongside them, so a
    count can never contradict its own list.
options:
  _input:
    description: The operation name, as the collection publishes it.
    type: str
    required: true
  target:
    description: What the operation acted on, as the caller designated it.
    type: str
    required: true
  mode:
    description:
      - C(apply) when the operation sent what it decided, C(check) when it only
        said what it would send. In check mode the changed names are the ones
        that I(would) change.
    type: str
    required: true
  changed:
    description: Names the operation changed, or would change in check mode.
    type: list
    default: []
  already_compliant:
    description: Names that were already where they should be.
    type: list
    default: []
  refused:
    description:
      - Objects the operation saw and set aside, each carrying a name and a
        reason. A refusal without a reason is an assertion nothing verifies.
    type: list
    default: []
  refused_reason:
    description:
      - Which field of those objects carries the reason. Defaults to C(reason);
        a role setting aside a machine because of its state passes C(state), so
        the list never has to be recomposed inside a template.
    type: str
    default: reason
  unmeasured:
    description:
      - Names, zones or products the operation could not read. Nothing measured
        is not nothing found, so these are named rather than counted as zero.
    type: list
    default: []
  started_at:
    description: When the operation started, ISO 8601.
    type: str
    required: true
  completed_at:
    description: When it finished, ISO 8601.
    type: str
    required: true
"""

RETURN = r"""
_value:
  description: The operation result.
  type: dict
"""

EXAMPLES = r"""
- name: Publish what the operation did
  ansible.builtin.set_fact:
    scaleway_operation: >-
      {{ 'power_schedule' | stephrobert.scaleway.operation_result(
           target='scw_tag_office_hours',
           mode=('check' if ansible_check_mode else 'apply'),
           changed=['web-01', 'web-03'],
           already_compliant=['web-02'],
           refused=[{'name': 'db-01', 'reason': 'locked'}],
           started_at=debut, completed_at=fin) }}
"""

#: Les modes possibles. `check` dit que rien n'a été envoyé, et c'est ce qui
#: distingue une répétition d'un vrai passage pour qui lit la structure.
MODES = ("apply", "check")


def _noms(valeur: object, champ: str) -> list[str]:
    if valeur is None:
        return []
    if not isinstance(valeur, (list, tuple)):
        raise AnsibleFilterError(
            f"`{champ}` doit être une liste de noms, pas {type(valeur).__name__}. "
            "Un compte se déduit de ses noms : le passer seul le rendrait "
            "invérifiable."
        )
    return [str(element) for element in valeur]


def _refus(valeur: object, champ_raison: str) -> list[dict[str, str]]:
    """Chaque refus porte son nom et sa raison, ou il n'est pas un refus.

    Une machine écartée sans raison est indiscernable d'une machine oubliée, et
    c'est précisément ce que la structure existe pour distinguer.

    **Le champ qui porte la raison se nomme en argument.** Un rôle écarte des
    machines dont l'objet porte déjà l'explication, `state` valant `locked` par
    exemple. Sans ce paramètre, il faudrait recomposer la liste dans le
    template, et une logique dans un template est ce que ce dépôt refuse :
    l'expression devenait une chaîne de `map` et de `zip` que personne ne relit.
    """
    if valeur is None:
        return []
    if not isinstance(valeur, (list, tuple)):
        raise AnsibleFilterError("`refused` doit être une liste d'objets")

    refuses: list[dict[str, str]] = []
    for element in valeur:
        raison = element.get(champ_raison) if isinstance(element, dict) else None
        if not isinstance(element, dict) or not element.get("name") or not raison:
            raise AnsibleFilterError(
                f"refus sans nom ou sans raison : {element!r} (raison cherchée "
                f"dans `{champ_raison}`). Une machine écartée sans raison ne se "
                "distingue pas d'une machine oubliée."
            )
        refuses.append({"name": str(element["name"]), "reason": str(raison)})
    return refuses


def operation_result(
    nom: str,
    target: str,
    mode: str,
    started_at: str,
    completed_at: str,
    changed: object = None,
    already_compliant: object = None,
    refused: object = None,
    refused_reason: str = "reason",
    unmeasured: object = None,
) -> dict[str, object]:
    """La structure commune, avec ses comptes déduits de ses listes."""
    if not nom:
        raise AnsibleFilterError("une opération sans nom ne se range nulle part")
    if not target:
        raise AnsibleFilterError(
            f"`{nom}` n'a pas de cible. Une opération qui ne dit pas sur quoi "
            "elle a agi ne se relit pas."
        )
    if mode not in MODES:
        raise AnsibleFilterError(
            f"mode={mode!r} n'est ni {' ni '.join(MODES)}. En répétition, "
            "`changed` compte ce qui bougerait, et taire le mode a déjà fait "
            "lire « machines éteintes » sur des machines qui tournaient."
        )

    changees = _noms(changed, "changed")
    conformes = _noms(already_compliant, "already_compliant")
    refuses = _refus(refused, refused_reason)
    non_mesures = _noms(unmeasured, "unmeasured")

    vus = len(changees) + len(conformes) + len(refuses)
    # **`null` et non `0` quand rien n'a pu être examiné.** Un total nul se lit
    # « il n'y avait rien », et rien n'a été mesuré n'est pas rien n'a été
    # trouvé. La même règle que le ratio sans dénominateur, qui rend `n/a`.
    examines: int | None = vus if (vus or not non_mesures) else None

    return {
        "name": nom,
        "target": target,
        "mode": mode,
        "examined": examines,
        "changed": len(changees) if examines is not None else None,
        "already_compliant": len(conformes) if examines is not None else None,
        "refused": len(refuses) if examines is not None else None,
        "unmeasured": len(non_mesures),
        "names": {
            "changed": sorted(changees),
            "already_compliant": sorted(conformes),
            "refused": sorted(refuses, key=lambda refus: refus["name"]),
            "unmeasured": sorted(non_mesures),
        },
        "started_at": started_at,
        "completed_at": completed_at,
    }


class FilterModule:
    """Ce que la collection publie comme filtres."""

    def filters(self) -> dict[str, object]:
        return {"operation_result": operation_result}
