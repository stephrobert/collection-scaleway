"""Comment un module de gestion décide qu'un champ a changé.

Le runtime comparait par égalité stricte, et il le disait lui-même dans sa
docstring : un champ que l'API réordonne ou normalise rend `changed` à chaque
exécution. Le module n'est alors plus idempotent, quoi qu'affiche `changed`, et
il devient inutilisable dans un handler.

```text
demandé            rendu par l'API
tags:              tags:
  - production       - web
  - web              - production

égalité stricte  -> changed, à chaque fois
comparaison SET  -> unchanged
```

**La stratégie vient du type quand le type la décide, et d'un override sinon.**
Le contrat ne dit rien de l'ordre ni de l'unicité : mesuré sur les deux
documents vendorisés, aucun tableau ne porte `uniqueItems`, et aucune
description ne parle d'ordre. Déduire `SET` de la forme d'un tableau serait
donc une devinette, et c'est exactement ce que la règle 3 du dépôt interdit.

Le défaut de repli est celui d'aujourd'hui, `ORDERED_LIST` pour un tableau :
adopter `SET` par défaut ferait taire un `changed` qui a peut-être raison, et
un module qui tait un changement réel est pire qu'un module qui en annonce un
de trop.
"""

from __future__ import annotations

from enum import Enum

from generator.ir.enums import ApiType


class ComparisonStrategy(Enum):
    """La façon dont un champ géré se compare à ce que l'API rend."""

    #: Égalité stricte. Un nom, un port, un booléen.
    SCALAR = "scalar"
    #: Deux listes égales élément par élément, dans l'ordre. Le repli d'un
    #: tableau, parce que le contrat ne dit pas si l'ordre porte du sens.
    ORDERED_LIST = "ordered_list"
    #: Mêmes éléments, mêmes multiplicités, ordre indifférent. Ne se pose que
    #: par override, avec sa raison.
    SET = "set"
    #: Deux dictionnaires égaux clé par clé, ce qui ne dépend déjà pas de
    #: l'ordre. Le nommer rend l'intention lisible plutôt qu'implicite.
    MAPPING = "mapping"
    #: Casse et espaces indifférents. Pour un champ dont l'API impose une forme.
    NORMALIZED_STRING = "normalized_string"
    #: L'API rend `{"id": "x"}` là où la requête prend `"x"`.
    OBJECT_ID = "object_id"
    #: Le pluriel du précédent : la requête prend `["x", "y"]`, la lecture rend
    #: `[{"id": "x", ...}, {"id": "y", ...}]`.
    #:
    #: **Ce n'est pas un choix humain, c'est une mesure du contrat.** Le schéma
    #: de lecture déclare un tableau d'objets portant un `id` là où le corps de
    #: la requête déclare un tableau. Comparer les deux directement rend
    #: « différent » à tous les coups, et le module réécrit à chaque exécution
    #: en annonçant `changed` : c'est le défaut de `lb_frontend.backend_id`,
    #: dans sa forme plurielle.
    ID_LIST = "id_list"
    #: L'API rend l'objet enrichi de champs que la requête ne porte pas : seules
    #: les clés demandées se comparent.
    NORMALIZED_OBJECT = "normalized_object"


#: Ce que le type de l'IR décide à lui seul.
#:
#: La table est **fermée par décision** : un type absent tombe sur `SCALAR`,
#: l'égalité stricte, qui est le comportement le plus prudent. Un type qui
#: mériterait autre chose se traite par override, avec sa raison, et le rapport
#: compte les paramètres de chaque stratégie pour que la dette reste visible.
PAR_TYPE: dict[ApiType, ComparisonStrategy] = {
    ApiType.ARRAY: ComparisonStrategy.ORDERED_LIST,
    ApiType.OBJECT: ComparisonStrategy.MAPPING,
    ApiType.MAP: ComparisonStrategy.MAPPING,
}

#: Les stratégies qu'aucun type ne peut décider, et qui n'arrivent que d'un
#: override. Les nommer permet au chargeur de refuser une valeur inventée.
PAR_DECISION_HUMAINE = frozenset(
    {
        ComparisonStrategy.SET,
        ComparisonStrategy.NORMALIZED_STRING,
        ComparisonStrategy.OBJECT_ID,
        ComparisonStrategy.NORMALIZED_OBJECT,
    }
)


def strategie_par_defaut(type_api: ApiType) -> ComparisonStrategy:
    """La stratégie que le type décide, sans rien deviner de plus."""
    return PAR_TYPE.get(type_api, ComparisonStrategy.SCALAR)


def depuis_le_nom(valeur: str) -> ComparisonStrategy:
    """Traduit la valeur écrite dans un override, ou refuse.

    Un nom inconnu est une faute de frappe, et une faute de frappe qui passerait
    produirait un override silencieusement inerte : le module comparerait
    strictement en croyant comparer autrement, et personne ne le verrait.
    """
    try:
        return ComparisonStrategy(valeur)
    except ValueError:
        connues = ", ".join(sorted(strategie.value for strategie in ComparisonStrategy))
        raise ValueError(
            f"stratégie de comparaison inconnue : {valeur!r}. Connues : {connues}"
        ) from None
