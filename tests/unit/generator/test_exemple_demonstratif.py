"""Un exemple copiable n'est pas encore un exemple qui démontre.

Le dépôt mesure que tous ses exemples publiés sont **copiables tels quels** :
c'est une propriété syntaxique, et elle est tenue. Un audit externe du
15 septembre 2026 a montré ce qu'elle ne dit pas.

```yaml
- name: Acls
  stephrobert.scaleway.k8s_cluster_acl_action:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
```

`AddClusterACLRules` **sans aucune ACL** est acceptée par l'API, ne change rien,
et l'exemple était parfaitement copiable. Quelqu'un le copie et n'apprend pas ce
que le module fait.

Le générateur avait raison de le produire : le `requestBody` du contrat est
`required: true`, mais la propriété `acls` elle-même ne porte aucune mention
`required`, et le parser traduit ce qu'il lit. C'est la décision qui manquait,
et une décision se prend dans un override.

Ce contrôle est l'invariant qui en découle, et il vaut pour les produits à
venir : **une action dont le corps porte des paramètres ne publie pas un exemple
qui n'en fournit aucun** (#275).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.collection import load_collection
from generator.ansible.models import build_module_specs
from generator.ir.enums import OperationKind
from generator.plan import build_plan
from generator.source.base import VendoredSpecSource

SPECS = Path(__file__).resolve().parents[2].parent / "specs" / "scaleway"

#: Les paramètres qu'une action porte sans rien démontrer : ils disent **où**
#: elle s'applique, pas **ce** qu'elle fait. Un exemple qui ne porte qu'eux
#: déclenche une opération vide.
#:
#: Dérivés du chemin de l'opération plutôt que listés : `region`, `zone` et les
#: identifiants de ressource y figurent parce que le contrat les y met, et une
#: liste écrite ici oublierait le premier produit nommant les siens autrement.


def _produits() -> list[tuple[str, str]]:
    return sorted(VendoredSpecSource(root=SPECS).available())


def _actions() -> list[tuple[str, object, tuple[str, ...], frozenset[str]]]:
    """Chaque module d'action livré, les paramètres de son chemin, et son corps."""
    trouvees = []
    collection = load_collection()
    for produit, version in _produits():
        plan = build_plan(produit, version, spec_root=SPECS)
        specs, _ = build_module_specs(plan, collection)
        for spec in specs:
            if spec.kind is not OperationKind.ACTION:
                continue
            operation = spec.action_operation
            # `body_params` est la liste que le runtime enverra dans le corps :
            # la recalculer depuis l'IR donnerait une seconde source, libre de
            # diverger de celle que le module utilise vraiment.
            trouvees.append(
                (spec.name, spec, tuple(operation.path_params), frozenset(operation.body_params))
            )
    return trouvees


CAS = _actions()


@pytest.mark.parametrize(
    ("nom", "spec", "chemin", "corps_declare"), CAS, ids=[nom for nom, _, _, _ in CAS]
)
def test_une_action_publie_un_exemple_qui_demontre(
    nom: str, spec: object, chemin: tuple[str, ...], corps_declare: frozenset[str]
) -> None:
    """Un exemple qui ne porte que le chemin déclenche une opération vide.

    Il est copiable, il est syntaxiquement juste, et il n'apprend rien : c'est
    exactement ce que le compteur « copiable » ne voit pas.

    **Une action sans aucun paramètre de corps est hors de ce contrôle**, et
    c'est légitime : `RebootNode` redémarre, le chemin dit tout, et il n'y a
    rien à démontrer de plus.

    **Le corps, et non tout ce qui n'est pas le chemin.** C'est ce que l'énoncé
    annonçait depuis le début, et ce que le calcul ne faisait pas : il comptait
    aussi les filtres de requête. Tant qu'aucune action n'en portait, les deux
    lectures donnaient le même verdict ; `EnableObjectStoragePrivateAccess` est
    la première à les séparer, avec un `private_network_ids` optionnel qui
    **restreint** une action que le chemin décrit entièrement. Exiger qu'un
    exemple le porte reviendrait à demander une démonstration de ce que
    l'opération fait déjà sans lui.

    Mesuré avant de restreindre : toutes les actions des produits déjà livrés
    portent leurs paramètres dans le corps, donc aucune ne sort du contrôle par
    cette précision. `tests/falsify/specs.json` le tient par une mutation.
    """
    options = {option.name for option in spec.options}  # type: ignore[attr-defined]
    corps = (options & corps_declare) - set(chemin) - {"region", "zone"}
    if not corps:
        return

    for exemple in spec.examples:  # type: ignore[attr-defined]
        portes = (set(exemple.parameters) & corps_declare) - set(chemin) - {"region", "zone"}
        assert portes, (
            f"`{nom}` publie un exemple qui ne porte que son chemin, alors "
            f"qu'il accepte {sorted(corps)}. Une opération déclenchée sans "
            "aucun de ses paramètres est acceptée, ne change rien, et l'exemple "
            "se copie sans rien apprendre. Rendre un paramètre obligatoire dans "
            "un override, avec sa raison."
        )
