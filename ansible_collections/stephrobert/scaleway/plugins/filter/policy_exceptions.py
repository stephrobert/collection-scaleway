# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Les exceptions d'une politique, qui changent un statut sans effacer un constat.

Une politique réellement utilisée rencontre toujours le cas « oui, mais ce
bastion **doit** avoir une adresse publique ». Si la seule issue est de
supprimer la règle, on perd la règle pour tout le parc afin d'excuser une
machine, et le système perd sa valeur le jour où il en aurait le plus.

**Une exception ne supprime pas un constat : elle change son statut.** Il reste
observable, compté à part, et sort en `suppressed` avec l'exception qui le
couvre. Un constat effacé est un problème dont plus personne ne sait qu'il
existe, et c'est exactement ce qu'on cherche à éviter en écrivant l'exception
plutôt qu'en retirant la règle.

**Une échéance dépassée est un constat, pas un refus.** Refuser toute la
politique parce qu'une exception a expiré éteindrait l'audit entier pour une
ligne périmée. L'échéance est l'information : elle sort comme un constat à elle,
et le dépôt applique déjà ça à ses propres exemptions.

Le sélecteur est celui de #208, appliqué à des ressources plutôt qu'à des hôtes
d'inventaire. `group` n'y figure pas : un audit lit l'API, pas un inventaire, et
un groupe d'inventaire ne désigne rien de ce qu'il a lu.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ansible.errors import AnsibleFilterError

try:  # pragma: no cover - le chemin d'import diffère entre collection et tests
    from ansible_collections.stephrobert.scaleway.plugins.module_utils.selecteur import (
        SelecteurError,
        designer,
        valider,
    )
except ImportError:  # pragma: no cover
    from ..module_utils.selecteur import (  # type: ignore[no-redef]
        SelecteurError,
        designer,
        valider,
    )

DOCUMENTATION = r"""
name: audit_exceptions
short_description: Turn policy exceptions into statuses, never into deletions
description:
  - >-
    Marks the findings an exception covers as suppressed rather than removing
    them. A finding that was erased is a problem nobody knows about any more.
  - >-
    Refuses an exception without a reason, without an owner or without an
    expiry, because each of those turns an exception into a rule quietly
    switched off.
  - >-
    An expired exception becomes a finding of its own rather than a refusal.
    Refusing the whole policy over one stale line would turn off the audit.
options:
  _input:
    description: The findings, as C(audit_findings) returned them.
    type: list
    required: true
  exceptions:
    description: The exceptions the policy carries.
    type: list
    required: true
  resources:
    description: The normalised resources the findings speak about.
    type: list
    required: true
  now:
    description: The reference instant, in UTC.
    type: str
    required: true
"""

RETURN = r"""
_value:
  description: The findings with their status, and what the exceptions say.
  type: dict
"""

EXAMPLES = r"""
- name: Apply the policy's exceptions
  ansible.builtin.set_fact:
    juge: >-
      {{ constats | stephrobert.scaleway.audit_exceptions(
           exceptions=politique.exceptions | default([]),
           resources=faits,
           now=now(utc=true, fmt='%Y-%m-%dT%H:%M:%SZ')) }}
"""

#: Ce qu'une exception doit porter, et ce que chacun empêche.
#:
#: Sans `reason`, c'est une règle désactivée qui se cache. Sans `owner`,
#: personne à qui demander si elle vaut encore. Sans `expires_at`, ce n'est plus
#: une exception mais une modification de la politique, écrite ailleurs.
OBLIGATOIRES = ("rule", "reason", "owner", "expires_at")

#: Ce qu'un critère de sélecteur nomme dans la forme commune d'une ressource.
#: L'identité est la seule chose que le contrat promette, donc `id` y est ; il
#: n'a pas d'équivalent dans un inventaire, et c'est pourquoi la résolution ne
#: se partage pas avec `select_hosts`.
CHAMPS = {"name": "name", "tags": "tags", "id": "id"}

#: Les façons de désigner une ressource dans une exception, déduites de ce que
#: la résolution sait lire. Deux listes se contrediraient. `group` n'y est pas :
#: un audit lit l'API, pas un inventaire.
CRITERES = tuple(CHAMPS)

#: Le statut d'un constat. `open` est celui qu'on lit, `suppressed` celui qu'on
#: garde sous les yeux sans agir.
STATUTS = ("open", "suppressed")


def _instant(valeur: object, quoi: str) -> datetime:
    """Une date de politique, ramenée à UTC.

    **Une échéance sans fuseau est lue en UTC**, et ce n'est pas un détail
    d'implémentation : `expires_at: 2026-12-31` est ce qu'un humain écrit dans un
    fichier de politique, et l'instant de référence, lui, vient d'`Ansible` avec
    son `Z`. Comparer les deux sans les ramener au même repère lève une erreur de
    type, ce qui ferait échouer l'audit entier sur une ligne d'échéance.

    Choisir UTC plutôt que le fuseau de la machine qui lance est délibéré : le
    même fichier de politique doit rendre le même verdict partout, et un audit
    qui expire une heure plus tôt à Paris qu'à Londres serait un audit dont on
    ne peut pas comparer deux exécutions.
    """
    try:
        lu = datetime.fromisoformat(str(valeur).replace("Z", "+00:00"))
    except (TypeError, ValueError) as erreur:
        raise AnsibleFilterError(f"{quoi} n'est pas une date ISO 8601 : {valeur!r}") from erreur
    return lu if lu.tzinfo else lu.replace(tzinfo=timezone.utc)


def _valider(exception: object, rang: int) -> dict:
    """Ce qu'une exception doit porter pour en être une."""
    if not isinstance(exception, dict):
        raise AnsibleFilterError(
            f"l'exception {rang} est un {type(exception).__name__}, pas un objet"
        )

    manquants = [champ for champ in OBLIGATOIRES if not exception.get(champ)]
    if manquants:
        raise AnsibleFilterError(
            f"l'exception {rang} ne porte pas {', '.join(manquants)}. Une "
            "exception sans raison est une règle désactivée qui se cache, sans "
            "propriétaire il n'y a personne à qui demander si elle vaut encore, "
            "et sans échéance ce n'est plus une exception mais une modification "
            "de la politique."
        )

    selecteur = exception.get("selector")
    if not isinstance(selecteur, dict):
        raise AnsibleFilterError(
            f"l'exception {rang} n'a pas de `selector` : elle couvrirait alors "
            "tout le parc, ce qui est une règle retirée et non une exception."
        )

    # **La grammaire vient d'ailleurs, le rang vient d'ici.** Le message commun
    # dit ce qui ne va pas ; le préfixe dit de quelle exception il s'agit, et
    # c'est ce qu'une politique qui en porte plusieurs rend indispensable.
    try:
        valider(selecteur, CRITERES, quoi=f"le `selector` de l'exception {rang}")
    except SelecteurError as erreur:
        raise AnsibleFilterError(f"l'exception {rang} : {erreur}") from erreur

    _instant(exception["expires_at"], f"l'échéance de l'exception {rang}")
    return exception


def _designees(selecteur: dict, ressources: list[dict], rang: int) -> list[str]:
    """Les identifiants que ce sélecteur désigne, ou un refus s'il est ambigu."""
    try:
        return [
            ressource["id"]
            for ressource in designer(
                selecteur,
                ressources,
                champs=CHAMPS,
                quoi=f"l'exception {rang}",
            )
        ]
    except SelecteurError as erreur:
        raise AnsibleFilterError(str(erreur)) from erreur


def _ressource_du_constat(constat: dict) -> str:
    """L'identifiant que l'identité du constat porte, sans la règle.

    L'identité est `règle:produit:identifiant`, et ce qui désigne la ressource
    en est la fin. Lire le constat plutôt que rejoindre les ressources évite un
    second chemin vers la même information.
    """
    morceaux = str(constat.get("id", "")).split(":")
    return morceaux[-1] if morceaux else ""


def audit_exceptions(
    constats: object, exceptions: object, resources: object, now: str
) -> dict[str, object]:
    """Les constats avec leur statut, et ce que les exceptions disent d'elles-mêmes."""
    if not isinstance(constats, (list, tuple)):
        raise AnsibleFilterError(f"les constats sont une liste, pas {type(constats).__name__}")
    if not isinstance(resources, (list, tuple)):
        raise AnsibleFilterError(f"les ressources sont une liste, pas {type(resources).__name__}")
    if exceptions is None:
        exceptions = []
    if not isinstance(exceptions, (list, tuple)):
        raise AnsibleFilterError(f"les exceptions sont une liste, pas {type(exceptions).__name__}")

    maintenant = _instant(now, "l'instant de référence")
    ressources = list(resources)

    couvertures: dict[str, str] = {}
    expirees: list[dict[str, str]] = []
    sans_cible: list[dict[str, str]] = []

    for rang, brute in enumerate(exceptions, start=1):
        exception = _valider(brute, rang)
        designees = _designees(exception["selector"], ressources, rang)

        if not designees:
            # Signalée, pas refusée : une exception pour une machine détruite est
            # du ménage à faire, pas une erreur de politique.
            sans_cible.append(
                {
                    "rule": exception["rule"],
                    "owner": exception["owner"],
                    "reason": exception["reason"],
                    "detail": "matches no resource that was read",
                }
            )
            continue

        if _instant(exception["expires_at"], f"l'échéance de l'exception {rang}") < maintenant:
            expirees.append(
                {
                    "id": f"expired_exception:{exception['rule']}:{exception['owner']}",
                    "name": f"exception/{exception['rule']}",
                    "rule": "expired_exception",
                    "field": "expires_at",
                    "severity": "fail",
                    # **La même forme qu'un constat de parc**, parce que les
                    # rendus les affichent ensemble : un rendu qui devrait
                    # traiter deux formes finirait par n'en traiter qu'une, et
                    # c'est l'exception périmée qui disparaîtrait du rapport.
                    "status": "open",
                    "detail": (
                        f"expired on {exception['expires_at']}, owned by "
                        f"{exception['owner']}: {exception['reason']}"
                    ),
                }
            )
            continue

        for identifiant in designees:
            couvertures[f"{exception['rule']}:{identifiant}"] = (
                f"{exception['owner']} until {exception['expires_at']}"
            )

    juges: list[dict[str, object]] = []
    for constat in constats:
        cle = f"{constat.get('rule')}:{_ressource_du_constat(constat)}"
        couverture = couvertures.get(cle)
        juges.append(
            {
                **constat,
                "status": "suppressed" if couverture else "open",
                **({"suppressed_by": couverture} if couverture else {}),
            }
        )

    return {
        "findings": juges,
        "open": sum(1 for c in juges if c["status"] == "open"),
        "suppressed": sum(1 for c in juges if c["status"] == "suppressed"),
        # Les constats des exceptions elles-mêmes, à côté de ceux du parc : une
        # exception périmée est un problème de politique, pas un problème de
        # machine, et les mélanger ferait chercher au mauvais endroit.
        "expired_exceptions": expirees,
        "exceptions_without_target": sans_cible,
    }


class FilterModule:
    """Ce que la collection publie pour les exceptions."""

    def filters(self) -> dict[str, object]:
        return {"audit_exceptions": audit_exceptions}
