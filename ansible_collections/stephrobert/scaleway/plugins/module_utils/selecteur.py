# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""La grammaire d'un sélecteur, écrite une fois.

Deux endroits posaient la même question à deux populations : `select_hosts`
désigne des hôtes d'inventaire, `audit_exceptions` désigne des ressources lues
par l'API. Les deux validaient la même grammaire, avec les mêmes refus et deux
jeux de messages qui avaient déjà commencé à diverger.

**Ce qui se partage et ce qui ne se partage pas.** La grammaire se partage :
un critère et un seul, une clé inconnue refusée, une combinaison d'étiquettes
nommée. La **résolution** ne se partage pas, et c'est correct : un groupe
d'inventaire n'est pas un pool, et un `id` de ressource n'a pas d'équivalent
dans un inventaire. Fondre les deux obligerait chaque appelant à porter les
critères de l'autre.

Les critères acceptés sont donc un paramètre, et c'est la seule chose que
l'appelant décide.
"""

from __future__ import annotations

#: Comment plusieurs étiquettes se combinent. `all` est le défaut parce qu'il
#: rend la sélection la plus étroite : pour une opération qui écrit, se tromper
#: du côté sûr veut dire toucher moins de ressources.
COMBINAISONS = ("all", "any")


class SelecteurError(ValueError):
    """Ce qu'un sélecteur mal formé lève, avant toute recherche.

    Une classe à elle, parce que les deux appelants la retraduisent chacun dans
    l'erreur que leur contexte attend : un filtre lève `AnsibleFilterError`, et
    un module lèverait autre chose. Le message, lui, est écrit une fois.
    """


def valider(
    selecteur: object, criteres: tuple[str, ...], *, quoi: str = "un sélecteur"
) -> tuple[str, object, str]:
    """Le critère posé, sa valeur, et la combinaison d'étiquettes voulue.

    Rend un triplet plutôt que le sélecteur tel quel : l'appelant a alors le
    critère sous la main et n'a plus à le redéduire, ce qui était le second
    endroit où les deux implémentations se répétaient.
    """
    if not isinstance(selecteur, dict):
        raise SelecteurError(
            f"{quoi} est un objet, pas {type(selecteur).__name__}. "
            f"Il porte exactement un de {', '.join(criteres)}."
        )

    inconnues = sorted(set(selecteur) - set(criteres) - {"match"})
    if inconnues:
        raise SelecteurError(
            f"clé(s) de sélecteur inconnue(s) : {', '.join(inconnues)}. "
            f"Les critères sont {', '.join(criteres)}. Une faute de frappe qui "
            "ne désignerait rien se lirait comme un parc vide."
        )

    poses = sorted(critere for critere in criteres if selecteur.get(critere))
    if not poses:
        raise SelecteurError(
            f"sélecteur vide : il faut un de {', '.join(criteres)}. Ne rien "
            "désigner est une décision qui se prend avant d'appeler, pas un "
            "sélecteur qui ne désigne rien."
        )
    if len(poses) > 1:
        raise SelecteurError(
            f"sélecteur qui porte {', '.join(poses)} à la fois. Deux critères "
            "posent deux questions, et la réponse dépendrait de l'ordre dans "
            "lequel on les lit."
        )

    critere = poses[0]
    mode = selecteur.get("match") or "all"
    if mode not in COMBINAISONS:
        raise SelecteurError(
            f"match={mode!r} n'est ni {' ni '.join(COMBINAISONS)}. Sans cette "
            "précision, `tags` ne dit pas s'il faut toutes les étiquettes ou "
            "une seule, et la sélection dépendrait de ce que le lecteur a "
            "supposé."
        )
    return critere, selecteur[critere], mode


def etiquettes_voulues(valeur: object) -> set[str]:
    """Les étiquettes d'un sélecteur, refusées si ce n'en est pas une liste."""
    if not isinstance(valeur, (list, tuple)) or not valeur:
        raise SelecteurError("`tags` est une liste non vide d'étiquettes")
    return {str(etiquette) for etiquette in valeur}


def correspond(voulues: set[str], portees: set[str], mode: str) -> bool:
    """Si ces étiquettes portées satisfont celles qu'on veut, dans ce mode."""
    return voulues <= portees if mode == "all" else bool(voulues & portees)
