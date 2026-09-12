# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Juger un parc contre une politique, et refuser de juger sur rien.

`rolling_reboot` sert quand on en a besoin ; un audit se lance tous les jours,
et c'est toute la différence entre un outil utile et un outil qu'on intègre à
ses opérations (#209).

**Les règles sont des données, pas du code.** Un audit dont les règles sont
gravées dans son playbook n'est pas un audit : c'est l'opinion de son auteur,
exécutable, et la première équipe qui n'a pas les mêmes étiquettes obligatoires
doit le forker. La sévérité en fait partie : l'adresse publique d'un bastion est
normale et celle d'une base ne l'est pas, et ce dépôt n'a pas à trancher ça pour
autrui.

**Une règle ne nomme jamais le champ d'un produit.** Elle lit la forme commune
que `resource_facts` produit : `last_change` plutôt que `modification_date`,
`public_addresses` plutôt que `public_ips`. C'est ce qui lui permet de valoir
pour un produit qu'elle ne connaît pas, et c'est pourquoi ajouter un produit
ajoute un normaliseur et pas une ligne dans une règle (#210).

**Aucune règle ne s'écrit sur une supposition de ce que l'API rend.** Chaque
champ de la forme commune vient d'un champ mesuré sur `instance_server_info`. Deux règles que l'issue proposait ne sont pas écrites,
et leur absence est déclarée dans `SANS_SOURCE` plutôt que tue : une adresse
réservée inutilisée et un load balancer sans backend sain n'ont pu être mesurés
sur aucune cible disponible.

**Un verdict sur ce qu'on n'a pas lu n'est pas un verdict.** Le rôle passe les
machines qu'il a effectivement obtenues ; les zones muettes ressortent dans le
résultat d'opération, jamais en conformité.
"""

from __future__ import annotations

from datetime import datetime

from ansible.errors import AnsibleFilterError

DOCUMENTATION = r"""
name: audit_findings
short_description: Judge a fleet against a policy, rule by rule
description:
  - Returns one finding per rule a resource breaks, each naming the rule, its
    severity and what was read.
  - Refuses a rule nothing can settle, a severity that is not one, and a policy
    with no rule at all, because a policy that checks nothing produces a green
    report on nothing.
options:
  _input:
    description: The machines to judge, as the reading module returned them.
    type: list
    required: true
  policy:
    description: The rules and their severities.
    type: dict
    required: true
  now:
    description: The instant durations are measured from, ISO 8601.
    type: str
    required: true
"""

RETURN = r"""
_value:
  description: One finding per rule a resource breaks.
  type: list
  elements: dict
"""

EXAMPLES = r"""
- name: Judge what the zones answered
  ansible.builtin.set_fact:
    constats: >-
      {{ machines | stephrobert.scaleway.audit_findings(
           policy=scaleway_fleet_audit_policy,
           now=now(utc=true, fmt='%Y-%m-%dT%H:%M:%SZ')) }}
"""

#: Les deux verdicts qu'une règle peut porter. `warn` dit « regarde », `fail`
#: dit « ça ne va pas ». Les confondre reviendrait à n'en avoir qu'un.
SEVERITES = ("warn", "fail")

#: Ce que l'issue proposait et qui n'est pas écrit, avec la raison. Les taire
#: laisserait croire que l'audit couvre ce qu'il ne regarde pas.
SANS_SOURCE = {
    "unused_reserved_ip": (
        "demande la forme d'une adresse réservée détachée, et **aucun parc "
        "disponible n'en porte** : ni celui du quickstart, ni la plateforme "
        "d'exemple. L'obstacle n'est pas l'émulateur, qui sert la route : "
        "mesuré, `POST /instance/v1/zones/{zone}/ips` rend 201 avec une "
        "adresse. Ce qui fermerait la ligne est donc du travail ici, pas en "
        "amont : que le parc fictif en réserve une, et la règle se mesure."
    ),
    "healthy_backend": (
        "demande la forme que `lb_backend_stat_info` rend, et **aucun parc "
        "disponible ne porte de load balancer**. L'obstacle n'est pas non plus "
        "l'émulateur : sur `backend-stats` il rend `not_found` sur la "
        "ressource, pas `not_emulated` sur la route, et il distingue les deux "
        "explicitement. Ce qui fermerait la ligne : un load balancer dans le "
        "parc fictif, puis la mesure de ce que la route rend."
    ),
}


def _horodatage(valeur: str, quoi: str) -> datetime:
    try:
        return datetime.fromisoformat(str(valeur).replace("Z", "+00:00"))
    except ValueError as erreur:
        raise AnsibleFilterError(f"{quoi} n'est pas une date ISO 8601 : {valeur!r}") from erreur


def _regle_etiquettes(machine: dict, parametres: dict) -> str | None:
    """Les étiquettes obligatoires, cherchées comme des clés `clé=valeur`.

    C'est la forme que ce parc emploie (`role=web`, `env=lab`), et la règle dit
    quelle clé elle cherche plutôt que de deviner une convention.
    """
    cles = parametres.get("keys")
    if not cles:
        raise AnsibleFilterError("`required_tags` attend `keys`, la liste des clés exigées")

    portees = {str(etiquette).split("=", 1)[0] for etiquette in (machine.get("tags") or [])}
    manquantes = sorted(set(cles) - portees)
    return f"missing tag: {', '.join(manquantes)}" if manquantes else None


def _regle_zones(machine: dict, parametres: dict) -> str | None:
    zones = parametres.get("zones")
    if not zones:
        raise AnsibleFilterError("`allowed_zones` attend `zones`, la liste des zones permises")

    zone = machine.get("zone")
    return None if zone in zones else f"zone: {zone}"


def _regle_adresse_publique(machine: dict, _parametres: dict) -> str | None:
    """Une adresse publique n'est pas un défaut : c'est une chose à regarder.

    D'où la sévérité dans la politique. Un bastion en a une par construction,
    une base de données pas.
    """
    adresses = machine.get("public_addresses") or []
    return f"public address: {', '.join(adresses)}" if adresses else None


def _regle_arretee_depuis(machine: dict, parametres: dict, maintenant: datetime) -> str | None:
    jours = parametres.get("days")
    if not jours:
        raise AnsibleFilterError("`stopped_since` attend `days`, le nombre de jours toléré")

    if not str(machine.get("state", "")).startswith("stopped"):
        return None
    depuis = machine.get("last_change")
    if not depuis:
        # Ne pas savoir n'est pas savoir que ça va : la machine ressort comme
        # non jugeable plutôt que comme conforme.
        return "stopped, and no date to measure it from"

    ecoules = (maintenant - _horodatage(depuis, "la date de modification")).days
    return f"stopped for {ecoules} day(s)" if ecoules >= int(jours) else None


#: Les règles écrites, et le champ que chacune lit. Ce que la politique nomme
#: hors de cette table est refusé : une règle qu'aucun fait ne peut trancher
#: rendrait « conforme » pour la seule raison que personne ne l'évalue.
REGLES = {
    "required_tags": _regle_etiquettes,
    "allowed_zones": _regle_zones,
    "public_ip": _regle_adresse_publique,
    "stopped_since": _regle_arretee_depuis,
}


def audit_findings(machines: object, policy: object, now: str) -> list[dict[str, str]]:
    """Un constat par règle qu'une ressource enfreint."""
    if not isinstance(policy, dict) or not policy.get("rules"):
        raise AnsibleFilterError(
            "politique sans règle : un audit qui ne vérifie rien rend un rapport "
            "vert sur rien, et le chemin le plus court vers un rapport vert "
            "serait de vider le fichier."
        )

    regles = policy["rules"]
    inconnues = sorted(set(regles) - set(REGLES))
    if inconnues:
        detail = "; ".join(f"{nom} : {SANS_SOURCE[nom]}" for nom in inconnues if nom in SANS_SOURCE)
        raise AnsibleFilterError(
            f"règle(s) qu'aucun fait ne peut trancher : {', '.join(inconnues)}. "
            f"Les règles écrites sont {', '.join(sorted(REGLES))}."
            + (f" Ce qui manque, et pourquoi : {detail}" if detail else "")
        )

    maintenant = _horodatage(now, "l'instant de référence")
    constats: list[dict[str, str]] = []

    for nom in sorted(regles):
        parametres = regles[nom] or {}
        severite = parametres.get("severity")
        if severite not in SEVERITES:
            raise AnsibleFilterError(
                f"la règle `{nom}` porte severity={severite!r}, qui n'est ni "
                f"{' ni '.join(SEVERITES)}. La sévérité est une donnée, parce "
                "que l'adresse publique d'un bastion est normale et celle d'une "
                "base ne l'est pas."
            )

        for machine in machines or []:
            fonction = REGLES[nom]
            detail = (
                fonction(machine, parametres, maintenant)
                if nom == "stopped_since"
                else fonction(machine, parametres)
            )
            if detail:
                constats.append(
                    {
                        # `name` et pas `resource` : c'est ce dont le constat
                        # parle, et c'est le champ que le contrat de résultat
                        # attend. Porter les deux serait une redondance de plus
                        # à tenir d'accord.
                        "name": f"instance/{machine.get('name', '?')}",
                        "rule": nom,
                        "severity": severite,
                        "detail": detail,
                    }
                )

    return sorted(constats, key=lambda constat: (constat["name"], constat["rule"]))


def audit_refusals(constats: object) -> list[dict[str, str]]:
    """Un refus par ressource, avec les règles qu'elle enfreint pour raison.

    **Le contrat de résultat compte des ressources examinées, pas des constats.**
    `examined` y vaut la somme de ce qui a changé, de ce qui était conforme et
    de ce qui est refusé : passer les constats ferait compter deux fois une
    machine qui enfreint deux règles. Sur un parc où chacune n'en enfreint
    qu'une, le total tombe juste par coïncidence, et c'est la forme même d'un
    faux vert.

    La raison porte les règles plutôt que les détails : c'est ce qui se relit
    dans un compte rendu, et les détails restent dans les constats.
    """
    par_ressource: dict[str, list[str]] = {}
    for constat in constats or []:
        par_ressource.setdefault(constat["name"], []).append(constat["rule"])

    return [
        {"name": nom, "reason": ", ".join(sorted(set(regles)))}
        for nom, regles in sorted(par_ressource.items())
    ]


class FilterModule:
    """Ce que la collection publie comme filtres."""

    def filters(self) -> dict[str, object]:
        return {"audit_findings": audit_findings, "audit_refusals": audit_refusals}
