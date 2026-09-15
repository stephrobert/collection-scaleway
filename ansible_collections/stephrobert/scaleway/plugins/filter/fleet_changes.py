# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ce qui a bougé, agrégé, et le silence quand rien n'a bougé.

Ce qui rend un outil récurrent utile n'est pas ce qu'il sait faire : c'est qu'on
ait envie de le lire le lendemain. Une version qui augmente le nombre de
notifications sans augmenter le rapport signal sur bruit rend le produit pire.

**La règle du jalon est exécutable, pas déclarative.** Deux runs sur un parc
inchangé, et le second sort `quiet` en ne produisant presque rien. Une règle
qu'aucun contrôle ne vérifie est une intention, et ce dépôt refuse ça partout
ailleurs.

**Pas de score composite.** `Cloud score: 83/100` fait joli et perd tout : un
nombre composite ne se remonte pas jusqu'à ce qui l'a fait bouger. Ce qui sort
est explicable ligne par ligne, chaque ligne comptant une chose nommée.

**Le niveau est calculé, jamais passé en paramètre.** Un appelant capable de le
forcer produirait un rapport qui se dit calme alors qu'il ne l'est pas, ce qui
est exactement ce qu'un outil récurrent ne doit pas pouvoir faire.
"""

from __future__ import annotations

from ansible.errors import AnsibleFilterError

DOCUMENTATION = r"""
name: changes_summary
short_description: One line per thing that moved, and nothing composite
description:
  - >-
    Aggregates what the fleet diff and the audit comparison found into counts
    that are explainable line by line. No composite score: a composite number
    cannot be traced back to what moved it.
  - >-
    Counts what was not measured apart from what did not move. A zone nobody
    could read is not a calm fleet, and presenting it as one is the green over
    zero files examined.
options:
  _input:
    description: The audit comparison, as C(audit_changes) returned it.
    type: dict
    required: true
  diff:
    description: >-
      The infrastructure comparison, as C(fleet_diff) returned it. C(none) says
      no earlier snapshot was handed back, which is not the same as nothing
      having moved.
    type: dict
    required: false
  expired_exceptions:
    description: The policy exceptions whose expiry has passed.
    type: list
    required: false
  unmeasured_scopes:
    description: The scopes this run could not read.
    type: list
    required: false
  previous_findings:
    description: >-
      The findings of the previous run, to say what each severity did rather
      than only where it stands.
    type: list
    required: false
"""

RETURN = r"""
_value:
  description: One count per thing that moved, and what each severity did.
  type: dict
"""

EXAMPLES = r"""
- name: What moved, in counts a person reads
  ansible.builtin.set_fact:
    bilan: >-
      {{ changements | stephrobert.scaleway.changes_summary(
           diff=comparaison,
           expired_exceptions=perimees,
           unmeasured_scopes=muettes,
           previous_findings=constats_gardes) }}
"""

#: Les niveaux, du plus silencieux au plus bruyant. L'ordre est celui de la
#: comparaison : agréger plusieurs verdicts revient à garder le plus haut.
NIVEAUX = ("baseline", "quiet", "changed", "action_required")


def _liste(valeur: object, quoi: str) -> list:
    if valeur is None:
        return []
    if not isinstance(valeur, (list, tuple)):
        raise AnsibleFilterError(f"{quoi} est une liste, pas un {type(valeur).__name__}")
    return list(valeur)


def _ouverts_par_severite(constats: list) -> dict[str, int]:
    """Combien de constats **ouverts** chaque sévérité porte.

    Les constats excusés n'y comptent pas : quelqu'un les a explicitement
    acceptés, et les faire peser dans le bilan reviendrait à nier l'exception
    qu'il a écrite.
    """
    compte: dict[str, int] = {}
    for constat in constats:
        if not isinstance(constat, dict) or (constat.get("status") or "open") != "open":
            continue
        severite = str(constat.get("severity") or "?")
        compte[severite] = compte.get(severite, 0) + 1
    return compte


def changes_summary(
    changes: object,
    diff: object = None,
    expired_exceptions: object = None,
    unmeasured_scopes: object = None,
    previous_findings: object = None,
) -> dict[str, object]:
    """Une ligne par chose qui a bougé, et rien de composite."""
    if not isinstance(changes, dict):
        raise AnsibleFilterError(
            f"le bilan se calcule sur un résultat d'`audit_changes`, "
            f"pas sur un {type(changes).__name__}"
        )
    if diff is not None and not isinstance(diff, dict):
        raise AnsibleFilterError(
            f"le diff est un résultat de `fleet_diff`, pas un {type(diff).__name__}"
        )

    perimees = _liste(expired_exceptions, "les exceptions périmées")
    muettes = _liste(unmeasured_scopes, "les portées muettes")
    gardes = previous_findings

    comptes = changes.get("counts") or {}
    persistants = [
        constat
        for constat in (changes.get("persisting") or [])
        if constat.get("severity") == "fail" and (constat.get("status") or "open") == "open"
    ]

    maintenant = _ouverts_par_severite(
        list(changes.get("new") or []) + list(changes.get("persisting") or [])
    )
    # **`None` et pas zéro.** Sans les constats du run précédent, on ne sait pas
    # ce qu'une sévérité a fait ; écrire `(+0)` affirmerait qu'elle n'a pas
    # bougé, ce qui est une phrase que rien ne soutient.
    avant = (
        _ouverts_par_severite(_liste(gardes, "les constats conservés"))
        if gardes is not None
        else None
    )

    severites = {
        severite: {
            "now": maintenant.get(severite, 0),
            "delta": (maintenant.get(severite, 0) - avant.get(severite, 0))
            if avant is not None
            else None,
        }
        for severite in sorted(set(maintenant) | set(avant or {}))
    }

    return {
        "baseline": bool(changes.get("baseline")),
        # `None` quand aucun instantané n'a été rendu : on n'a pas comparé, ce
        # qui n'est pas « rien n'a bougé ».
        "infrastructure_changes": (
            None
            if diff is None
            else len(diff.get("new") or [])
            + len(diff.get("removed") or [])
            + len(diff.get("changed") or [])
        ),
        "new_findings": int(comptes.get("new") or 0),
        # **Compté à part du delta de sévérité, et ce n'est pas la même chose.**
        # Un `fail` qui apparaît pendant qu'un autre se résout laisse le delta à
        # zéro : décider sur le delta ferait taire le constat neuf, masqué par
        # la bonne nouvelle du voisin.
        "new_failures": len(
            [
                constat
                for constat in (changes.get("new") or [])
                if constat.get("severity") == "fail" and (constat.get("status") or "open") == "open"
            ]
        ),
        "resolved_findings": int(comptes.get("resolved") or 0),
        "persistent_failures": len(persistants),
        "expired_exceptions": len(perimees),
        "unmeasured_scopes": len(muettes),
        # Séparé des résolus, et c'est tout l'objet de #234 : un constat dont la
        # zone n'a pas répondu n'est pas un constat réglé.
        "not_concluded": int(comptes.get("unmeasured") or 0),
        "scopes_not_compared": (None if diff is None else len(diff.get("scopes_not_compared") or {})),
        "severities": severites,
    }


def summary_verdict(bilan: object) -> str:
    """Ce que ce bilan demande, calculé et jamais passé en paramètre.

    **`action_required` compte la mesure impossible au même rang qu'un nouveau
    constat bloquant.** Une zone muette n'est pas une bonne nouvelle, et la
    présenter comme un parc calme est le vert sur zéro fichier examiné.

    Une exception périmée y compte aussi : son échéance est l'information, et le
    jour où elle passe est le seul moment où elle a une chance d'être vue.
    """
    if not isinstance(bilan, dict):
        raise AnsibleFilterError(
            f"le verdict se calcule sur un bilan, pas sur un {type(bilan).__name__}"
        )

    if (
        bilan.get("unmeasured_scopes")
        or bilan.get("not_concluded")
        or bilan.get("expired_exceptions")
        or bilan.get("scopes_not_compared")
    ):
        return "action_required"

    # Un `fail` neuf demande une action ; un `fail` qui persiste a déjà été
    # rapporté hier, et le remonter au même rang chaque matin est exactement le
    # bruit que cette version cherche à retirer.
    #
    # **Sur le compte des neufs, jamais sur le delta.** Un `fail` qui apparaît
    # pendant qu'un autre se résout laisse le delta à zéro, et décider sur le
    # delta ferait taire le constat neuf.
    if bilan.get("new_failures"):
        return "action_required"

    if bilan.get("baseline"):
        return "baseline"

    if (
        bilan.get("new_findings")
        or bilan.get("resolved_findings")
        or bilan.get("infrastructure_changes")
    ):
        return "changed"
    return "quiet"


def worst_level(niveaux: object) -> str:
    """Le plus haut de plusieurs niveaux, pour qu'aucun ne soit noyé.

    Agréger en prenant le plus bas laisserait une moitié calme masquer une
    moitié qui ne l'est pas, ce qui est la façon la plus simple de fabriquer un
    rapport rassurant.
    """
    vus = _liste(niveaux, "les niveaux")
    inconnus = [niveau for niveau in vus if niveau not in NIVEAUX]
    if inconnus:
        raise AnsibleFilterError(
            f"niveau(x) inconnu(s) : {', '.join(map(str, inconnus))}. "
            f"Les niveaux sont {', '.join(NIVEAUX)}."
        )
    return max(vus, key=NIVEAUX.index) if vus else "quiet"


class FilterModule:
    """Ce que la collection publie pour agréger ce qui a bougé."""

    def filters(self) -> dict[str, object]:
        return {
            "changes_summary": changes_summary,
            "summary_verdict": summary_verdict,
            "worst_level": worst_level,
        }
