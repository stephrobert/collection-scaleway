"""Ce qu'une opération autorise à rejouer, et ce qu'elle interdit.

Le runtime n'avait aucune politique de réessai : une requête, une réponse. Sur
un cloud, ça rend un playbook fragile pour rien, parce qu'un `503` de trente
secondes fait échouer un déploiement entier.

**Un `Retry(total=5)` global serait pire que rien.** Il rejouerait le POST qui
redémarre une machine, et un redémarrage joué deux fois n'est pas un
redémarrage. La politique appartient donc à l'opération, comme la stratégie de
comparaison appartient au champ.

```text
GET                 rejouable : la requête ne change rien
PATCH d'un MANAGE   rejouable sur 429 : le serveur dit n'avoir rien traité
POST d'action       jamais : la répétition se voit
```

**Ce que le contrat ne dit pas, on ne l'invente pas.** Aucun document Scaleway
ne déclare l'idempotence d'une opération, ni ne porte de clé d'idempotence.
La politique se déduit donc de deux faits que le contrat **dit** : la méthode
HTTP, dont RFC 9110 fixe la sûreté, et la classe que le classifieur a établie.
Rien d'autre.
"""

from __future__ import annotations

from enum import Enum

from generator.ir.enums import HTTPMethod, OperationKind


class RetryPolicy(Enum):
    """Ce qu'une opération autorise à rejouer quand l'appel échoue."""

    #: La requête ne change rien : la rejouer est sans conséquence. RFC 9110
    #: fixe `GET` et `HEAD` comme sûres, et c'est le contrat le plus fort dont
    #: on dispose ici.
    SAFE = "safe"
    #: La requête écrit. Elle se rejoue quand l'API dit **n'avoir rien traité**,
    #: et pas quand la réponse est ambiguë : après un `502`, l'écriture a
    #: peut-être eu lieu, et le module préfère échouer bruyamment plutôt que
    #: rendre un état qu'il n'a pas observé.
    LIMITED = "limited"
    #: La requête déclenche quelque chose dont la répétition se voit. Un
    #: redémarrage joué deux fois n'est pas un redémarrage.
    NEVER = "never"


#: Les méthodes que RFC 9110 déclare sûres : elles ne demandent aucun
#: changement d'état, donc les rejouer ne peut rien casser.
#:
#: `HEAD` en est une aussi, et n'y figure pas : l'IR ne la porte pas, parce
#: qu'aucun contrat vendorisé n'en déclare. L'ajouter ici serait décrire une
#: méthode que ce générateur ne peut pas rencontrer.
_SURES: frozenset[HTTPMethod] = frozenset({HTTPMethod.GET})


def politique_par_defaut(methode: HTTPMethod, classe: OperationKind) -> RetryPolicy:
    """Ce que la méthode et la classe décident, sans rien deviner de plus.

    **L'ordre compte.** Une action se reconnaît à sa classe, pas à sa méthode :
    `ServerAction` est un `POST` comme le serait une création, et c'est le
    classifieur qui sait la différence. Tester la méthode d'abord rendrait
    `LIMITED` pour une action, donc rejouable sur un `429`, ce qui est
    exactement ce qu'on refuse.
    """
    if classe is OperationKind.ACTION:
        return RetryPolicy.NEVER
    if methode in _SURES:
        return RetryPolicy.SAFE
    return RetryPolicy.LIMITED


def depuis_le_nom(valeur: str) -> RetryPolicy:
    """Traduit la valeur écrite dans un override, ou refuse.

    Un nom inconnu est une faute de frappe, et une faute de frappe qui passerait
    produirait un override silencieusement inerte : l'opération garderait la
    politique déduite en laissant croire qu'elle en a une autre.
    """
    try:
        return RetryPolicy(valeur)
    except ValueError:
        connues = ", ".join(sorted(politique.value for politique in RetryPolicy))
        raise ValueError(
            f"politique de réessai inconnue : {valeur!r}. Connues : {connues}"
        ) from None
