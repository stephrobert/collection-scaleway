"""Ce qu'un module déclare savoir faire, dans la section qu'Ansible normalise.

Le README de la collection met en avant le check mode, `--diff` et
l'idempotence. Un lecteur de Galaxy ne pouvait pas le vérifier depuis la page
d'un module : Ansible a une place normée pour ça, `attributes`, et aucun module
généré ne la portait (#133). Il fallait donc croire le README, ce que le critère
de ce dépôt interdit précisément.

```yaml
attributes:
  check_mode:
    description: ...
    support: full
  diff_mode:
    description: ...
    support: none
```

**Ces valeurs sont des propriétés mesurées du runtime, pas des intentions.**
C'est le point qui rend cette section dangereuse : `check_mode: full` sur un
module qui agit en check mode est un faux vert de la même famille que celui
corrigé en 0.4.0, en pire, parce que c'est une promesse formelle que des outils
lisent. Chaque valeur ci-dessous est donc reliée au comportement réel par un
test de `tests/unit/collection/test_attributs.py`, classe par classe, et
`scripts/docs_quality.py` refuse une page qui annoncerait autre chose que ce que
sa classe permet.

**Pourquoi aucun `version_added` sur ces attributs.** Ils décrivent un
comportement présent depuis la première version de chaque module : le check mode
n'est pas ajouté ici, il est enfin **déclaré**. Dater la déclaration ferait
croire à un support nouveau, ce qui serait la seconde façon de mentir sur une
date après celle qu'ADR-013 vient de corriger.
"""

from __future__ import annotations

from dataclasses import dataclass

from generator.ir.enums import OperationKind

#: Les niveaux de support qu'Ansible reconnaît. `partial` et `N/A` n'ont pas
#: d'emploi ici aujourd'hui, et les nommer quand même dit ce que le vocabulaire
#: permet plutôt que de laisser croire qu'il n'y a que deux réponses.
SUPPORTS: frozenset[str] = frozenset({"full", "partial", "none", "N/A"})


@dataclass(frozen=True)
class Attribut:
    """Un attribut publié : son niveau de support, et ce qu'il annonce.

    La description est **publiée**, donc en anglais. Elle dit ce que le module
    fait, pas ce que l'attribut signifie en général : un lecteur qui arrive sur
    la page cherche la première, et trouve la seconde dans la documentation
    d'Ansible.
    """

    support: str
    description: str

    def to_documentation(self) -> dict[str, str]:
        return {"description": self.description, "support": self.support}


#: Ce que chaque classe de module tient, mesuré dans le runtime.
#:
#: * **INFO** ne modifie rien : le check mode ne change pas son comportement,
#:   et il n'y a aucun changement à montrer ;
#: * **ACTION** n'envoie rien en check mode et annonce ce qui serait déclenché.
#:   Il ne construit même pas son client d'API, ce qu'un test prouve. Il ne
#:   rend pas de diff : un déclenchement n'a pas d'avant et d'après comparables ;
#: * **MANAGE** lit, compare, et n'écrit que la différence. En check mode il
#:   compare et sort, et il rend `before`/`after` des deux côtés.
PAR_CLASSE: dict[OperationKind, dict[str, Attribut]] = {
    OperationKind.INFO: {
        "check_mode": Attribut(
            support="full",
            description=(
                "This module only reads, so check mode changes nothing about how it runs."
            ),
        ),
        "diff_mode": Attribut(
            support="none",
            description="This module changes nothing, so it has no difference to report.",
        ),
    },
    OperationKind.ACTION: {
        "check_mode": Attribut(
            support="full",
            description=(
                "In check mode the module reports the action it would trigger and "
                "sends nothing, without even building an API client."
            ),
        ),
        "diff_mode": Attribut(
            support="none",
            description=(
                "An action is a trigger rather than a state, so there is no before "
                "and after to compare."
            ),
        ),
    },
    OperationKind.MANAGE: {
        "check_mode": Attribut(
            support="full",
            description=(
                "In check mode the module reads the resource and compares it, then "
                "reports what it would write without writing it."
            ),
        ),
        "diff_mode": Attribut(
            support="full",
            description=(
                "The module reports the fields that differ, read through the same "
                "projection the comparison uses."
            ),
        ),
    },
}


def pour(kind: OperationKind) -> dict[str, dict[str, str]]:
    """Le bloc `attributes` d'un module de cette classe.

    Une classe absente de la table rend un bloc vide plutôt qu'un bloc
    inventé : une page sans `attributes` n'apprend rien, une page qui affirme un
    support non mesuré trompe.
    """
    return {nom: attribut.to_documentation() for nom, attribut in PAR_CLASSE.get(kind, {}).items()}
