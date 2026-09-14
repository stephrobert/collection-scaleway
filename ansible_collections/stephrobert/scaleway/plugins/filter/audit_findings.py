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


def _regle_etiquettes(machine: dict, parametres: dict, _maintenant: datetime) -> str | None:
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


def _regle_zones(machine: dict, parametres: dict, _maintenant: datetime) -> str | None:
    zones = parametres.get("zones")
    if not zones:
        raise AnsibleFilterError("`allowed_zones` attend `zones`, la liste des zones permises")

    zone = machine.get("zone")
    return None if zone in zones else f"zone: {zone}"


def _regle_adresse_publique(machine: dict, _parametres: dict, _maintenant: datetime) -> str | None:
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


def _regle_maintenance_prevue(machine: dict, parametres: dict, maintenant: datetime) -> str | None:
    """Une maintenance planifiée par le fournisseur, sur cette machine.

    Mesuré le 14 septembre 2026 : le champ vaut `[]` sur une machine saine, donc
    l'absence de maintenance est une liste vide et non un champ manquant. Une
    liste vide est bien « rien de prévu » ; `None` serait « on ne sait pas », et
    ce n'est pas la même réponse.

    `within_days` restreint aux échéances proches, parce qu'une maintenance dans
    six mois n'appelle pas la même chose qu'une maintenance demain.
    """
    prevues = machine.get("planned_maintenance")
    if prevues is None:
        return "no maintenance window was read for this resource"
    if not prevues:
        return None

    jours = parametres.get("within_days")
    if not jours:
        return f"{len(prevues)} planned maintenance window(s)"

    proches = []
    for fenetre in prevues:
        debut = (fenetre or {}).get("start_date") if isinstance(fenetre, dict) else None
        if not debut:
            # Une fenêtre sans date n'est pas une fenêtre lointaine : elle est
            # illisible, et la taire la ferait passer pour absente.
            proches.append("a window with no start date")
            continue
        reste = (_horodatage(debut, "la date de maintenance") - maintenant).days
        if reste <= int(jours):
            proches.append(f"in {reste} day(s)")
    return f"planned maintenance: {', '.join(proches)}" if proches else None


def _regle_fin_de_service(machine: dict, _parametres: dict, _maintenant: datetime) -> str | None:
    """Le type commercial de cette machine cesse d'être offert.

    Ce n'est pas une panne, c'est une échéance : la machine tourne et continuera
    de tourner, mais elle ne se recrée pas, et le jour où elle disparaît le
    remplacement n'existe plus. C'est exactement le genre de chose que personne
    ne découvre au bon moment.
    """
    fin = machine.get("end_of_service")
    if fin is None:
        return "end of service was not read for this resource"
    return "its commercial type is end of service" if fin else None


def _regle_actions_attendues(machine: dict, parametres: dict, _maintenant: datetime) -> str | None:
    """Ce qu'on croit pouvoir faire de cette machine, et qui n'est pas permis.

    L'API dit ce qu'elle accepte **dans l'état courant**, et c'est une
    information d'exploitation : une machine qu'on ne peut plus redémarrer ne se
    signale autrement qu'au moment où l'on essaie, en pleine opération.

    Mesuré : une machine arrêtée rend `["stop_in_place", "backup"]`, donc
    `poweron` n'y est pas. La règle nomme ce qu'elle attend plutôt que de
    supposer une liste universelle.
    """
    attendues = parametres.get("actions")
    if not attendues:
        raise AnsibleFilterError(
            "`required_actions` attend `actions`, la liste des actions qu'on "
            "veut pouvoir déclencher. Sans elle, la règle devrait supposer ce "
            "qu'un parc attend de ses machines, et ce dépôt ne tranche pas ça "
            "pour autrui."
        )

    permises = machine.get("allowed_actions")
    if permises is None:
        return "allowed actions were not read for this resource"
    manquantes = sorted(set(attendues) - set(permises))
    return f"cannot: {', '.join(manquantes)}" if manquantes else None


def _regle_mise_a_jour_offerte(machine: dict, _parametres: dict, _maintenant: datetime) -> str | None:
    """Le fournisseur offre une mise à jour de cette ressource.

    **Elle signale, elle ne met pas à jour.** `UpgradeCluster` existe et ce rôle
    ne l'appelle pas : détecter puis diagnostiquer, jamais détecter puis
    modifier. La proposition de remédiation est un autre sujet, et c'est une
    proposition.
    """
    offerte = machine.get("upgrade_available")
    if offerte is None:
        return "upgrade availability was not read for this resource"
    return "an upgrade is available" if offerte else None


def _regle_echeance(machine: dict, parametres: dict, maintenant: datetime) -> str | None:
    """Ce qui expire, et dans combien de temps.

    Une seule règle pour deux objets : un certificat de load balancer porte sa
    propre échéance, un cluster porte celle de la version qu'il fait tourner.
    C'est la même question posée deux fois, et lui donner deux noms obligerait à
    écrire deux règles pour une chose.

    **Une échéance absente n'est pas une échéance lointaine.** Un certificat dont
    la date ne se lit pas, ou un cluster dont la version n'est pas au catalogue,
    sortent comme non jugeables plutôt que comme conformes.
    """
    jours = parametres.get("days")
    if not jours:
        raise AnsibleFilterError(
            "`expires_within` attend `days`, le nombre de jours d'avance voulu"
        )

    echeance = machine.get("expires_at")
    if not echeance:
        return "nothing says when this expires, so nothing says it does not"

    # **Tronqué vers zéro, pas vers le bas.** `timedelta.days` plancherait :
    # une échéance passée depuis treize jours et dix heures sortirait « expired
    # 14 day(s) ago », ce qui est faux d'un jour et toujours du mauvais côté.
    ecart = (_horodatage(echeance, "la date d'expiration") - maintenant).total_seconds()
    reste = int(ecart // 86400) if ecart >= 0 else -int(-ecart // 86400)
    if reste < 0:
        return f"expired {-reste} day(s) ago, on {echeance}"
    return f"expires in {reste} day(s), on {echeance}" if reste <= int(jours) else None


def _regle_retard_de_version(machine: dict, parametres: dict, _maintenant: datetime) -> str | None:
    """De combien de mineures cette ressource est en retard sur ce qui est offert.

    **Le retard se compte, il ne s'estime pas** : le catalogue des versions est
    lu, et le rapprochement est fait à la couture plutôt que dans cette règle.

    Un retard inconnu ressort comme non jugeable. Une version absente du
    catalogue, ou d'une autre majeure que la dernière offerte, n'est pas « à
    jour » : c'est une question à laquelle ce compte-là ne répond pas.
    """
    maximum = parametres.get("max_minor_behind")
    if maximum is None:
        raise AnsibleFilterError(
            "`version_drift` attend `max_minor_behind`, le nombre de versions "
            "mineures de retard toléré"
        )

    retard = machine.get("versions_behind")
    if retard is None:
        version = machine.get("version") or "unknown"
        return f"running {version}, and nothing read says how far behind that is"
    return (
        f"{retard} minor version(s) behind, running {machine.get('version')}"
        if retard > int(maximum)
        else None
    )


#: Ce qu'une condition de santé doit valoir pour que la ressource aille bien.
#: Mesuré sur la réponse réelle du 14 septembre 2026, où l'API rend des chaînes
#: `"True"` et `"False"` plutôt que des booléens.
SANTE_ATTENDUE = {
    "Ready": "True",
    "DiskPressure": "False",
    "MemoryPressure": "False",
    "PIDPressure": "False",
    "NetworkUnavailable": "False",
}


def _regle_conditions_de_sante(machine: dict, parametres: dict, _maintenant: datetime) -> str | None:
    """Les conditions de santé que cette ressource rapporte.

    **`conditions` est mesuré et non contracté.** `scaleway.k8s.v1.Node` ne le
    déclare pas, ni `public_ip_v4` ni `public_ip_v6` ; la réponse réelle du
    14 septembre 2026 les rend tous les trois. Le jour où l'API cesserait de
    rendre `conditions`, aucun golden ne rougirait.

    C'est pourquoi **son absence vaut « non mesuré », jamais « sain »** : une
    règle qui lirait l'absence comme une bonne nouvelle annoncerait un parc en
    bonne santé sur zéro champ lu, et le rapport serait parfaitement plausible.
    """
    attendues = parametres.get("conditions") or SANTE_ATTENDUE
    conditions = machine.get("health_conditions")
    if not conditions:
        return (
            "no health conditions were read, which is not the same as being "
            "healthy"
        )
    if not isinstance(conditions, dict):
        return f"health conditions are a {type(conditions).__name__}, not a mapping"

    mauvaises = [
        f"{nom}={conditions.get(nom)}"
        for nom, voulue in attendues.items()
        # Une condition que la ressource ne rapporte pas est ignorée : le jeu
        # varie d'une version à l'autre, et exiger la présence ferait rougir un
        # parc sain le jour où l'amont en retire une.
        if nom in conditions and str(conditions[nom]) != str(voulue)
    ]
    return f"unhealthy: {', '.join(sorted(mauvaises))}" if mauvaises else None


#: Les règles écrites, et le champ que chacune juge. Ce que la politique nomme
#: hors de cette table est refusé : une règle qu'aucun fait ne peut trancher
#: rendrait « conforme » pour la seule raison que personne ne l'évalue.
#:
#: Le champ entre dans l'identité du constat, et il n'est pas décoratif : deux
#: règles peuvent juger la même ressource sur deux choses différentes, et une
#: identité qui les confondrait ferait disparaître l'une quand l'autre est
#: corrigée.
REGLES = {
    "required_tags": (_regle_etiquettes, "tags"),
    "allowed_zones": (_regle_zones, "zone"),
    "public_ip": (_regle_adresse_publique, "public_addresses"),
    "stopped_since": (_regle_arretee_depuis, "state"),
    # Celles de #252, chacune sur un champ **déjà traversé et lu par
    # personne**. Ce ne sont pas des modules à écrire : la plomberie existait,
    # et le moteur de règles n'en exploitait qu'une poignée de champs.
    "planned_maintenance": (_regle_maintenance_prevue, "planned_maintenance"),
    "end_of_service": (_regle_fin_de_service, "end_of_service"),
    "required_actions": (_regle_actions_attendues, "allowed_actions"),
    "upgrade_available": (_regle_mise_a_jour_offerte, "upgrade_available"),
    "expires_within": (_regle_echeance, "expires_at"),
    "version_drift": (_regle_retard_de_version, "versions_behind"),
    "unhealthy_conditions": (_regle_conditions_de_sante, "health_conditions"),
}


def finding_id(regle: str, ressource: dict) -> str:
    """L'identité d'un constat, recalculée à chaque run et stable entre deux.

    **Rien d'aléatoire, rien d'horodaté** : sinon tout serait neuf chaque matin,
    et « nouveau, persistant, résolu » ne voudrait rien dire.

    **Sur l'identifiant, jamais sur le nom.** Mesuré sur le compte réel : deux
    machines acceptent le même nom dans la même zone, et l'API rend alors deux
    identifiants distincts. Une identité assise sur le nom collerait le constat
    d'une machine sur une autre, et le rapport du lendemain annoncerait « résolu »
    pour celle qui ne l'est pas (ADR-021).

    Une règle renommée produit d'autres identifiants, et c'est voulu : ce n'est
    plus la même règle, donc ce n'est plus le même constat.

    **Le champ jugé n'y entre pas, et c'est une décision.** La forme proposée
    portait `règle:produit:identifiant:champ`, mais `REGLES` associe à chaque
    règle exactement un champ : le champ se déduit donc de la règle et ne
    distingue rien de plus. `/falsify` l'a dit avant nous, en laissant le test
    vert quand la mutation le retirait. Un composant qu'aucune mutation ne peut
    faire rougir est une affirmation que rien ne vérifie.

    L'invariant qui rend ça vrai : **une règle juge un champ**. Le jour où une
    règle en jugerait deux, elle devient deux règles, et un test le tient.
    """
    identifiant = ressource.get("id")
    kind = ressource.get("kind")
    if not identifiant or not kind:
        raise AnsibleFilterError(
            f"la ressource jugée par `{regle}` n'a ni `kind` ni `id` utilisable : "
            f"{ressource.get('name') or '<sans nom>'}. Un constat sans identité "
            "ne peut pas être reconnu d'un run à l'autre, et il ressortirait "
            "comme neuf puis comme résolu à chaque exécution."
        )
    return f"{regle}:{kind}:{identifiant}"


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

        fonction, champ = REGLES[nom]
        for machine in machines or []:
            # **Un produit qui ne porte pas ce champ n'est pas jugé conforme :
            # il n'est pas jugé.** Un cluster n'a pas d'action permise, une
            # machine n'a pas de version à rattraper. Les compter comme
            # conformes gonflerait le `PASS` de ressources que personne n'a
            # regardées, ce qui est le vert sur zéro champ lu (#252).
            if champ not in machine:
                continue
            # **L'instant va à toutes les règles, pas à une seule.** La
            # première version le passait au seul `stopped_since`, et chaque
            # règle datée qui s'ajoutait allongeait la condition : une liste de
            # noms dans un `if` est un endroit où l'on finit par en oublier un,
            # et la règle oubliée compare alors une date à rien.
            detail = fonction(machine, parametres, maintenant)
            if detail:
                constats.append(
                    {
                        # **L'identité, et elle seule, sert à comparer deux
                        # runs.** Le reste est fait pour être lu.
                        "id": finding_id(nom, machine),
                        # `name` et pas `resource` : c'est ce dont le constat
                        # parle, et c'est le champ que le contrat de résultat
                        # attend. Porter les deux serait une redondance de plus
                        # à tenir d'accord.
                        #
                        # Il reste le nom, donc lisible et non unique : c'est
                        # pourquoi il ne sert pas d'identité.
                        "name": f"{machine.get('kind', '?')}/{machine.get('name', '?')}",
                        # **La zone, parce que sans elle un constat disparu est
                        # indiscernable d'un constat résolu.** Comparer deux runs
                        # demande de savoir si la zone qui portait le constat a
                        # répondu cette fois ; sans cette information, la seule
                        # réponse honnête serait « on ne sait pas » pour tout le
                        # parc, et le rapport ne dirait plus rien (#234).
                        "zone": machine.get("zone"),
                        "rule": nom,
                        "field": champ,
                        "severity": severite,
                        "detail": detail,
                    }
                )

    # Trié sur l'identité : elle est unique, là où deux machines homonymes
    # rendraient l'ordre dépendant de celui de la lecture.
    return sorted(constats, key=lambda constat: constat["id"])


def rules_without_target(policy: object, products: object) -> list[str]:
    """Les règles qu'aucun produit lu ne peut trancher, nommées avec ce qu'il faut lire.

    **Une règle qui ne juge rien est un silence, pas une conformité.** Écrire
    `unhealthy_conditions` dans sa politique en ne lisant que des Instances
    produit un rapport vert où personne n'a rien vérifié, et rien dans ce
    rapport ne le dit.

    Le rôle refuse donc plutôt que de lire de lui-même les produits qui
    manquent : chaque produit lu est une famille d'appels d'API sur un compte
    facturé, et ce n'est pas une décision que ce rôle prend à la place de qui le
    lance. Il la nomme.

    Rend les règles concernées, chacune avec les produits qui portent son champ.
    """
    from ansible_collections.stephrobert.scaleway.plugins.filter.resource_facts import (
        CHAMPS,
        SUPPLEMENTS,
    )

    if not isinstance(policy, dict):
        raise AnsibleFilterError(
            f"une politique est un dictionnaire, pas {type(policy).__name__}"
        )
    if not isinstance(products, (list, tuple)):
        raise AnsibleFilterError(
            f"les produits lus sont une liste, pas {type(products).__name__}"
        )

    lus = [str(produit) for produit in products]
    orphelines = []
    for nom in sorted((policy.get("rules") or {})):
        if nom not in REGLES:
            # Une règle inconnue est refusée ailleurs, par `audit_findings`, et
            # avec un message qui lui est propre. La signaler deux fois ferait
            # deux messages pour une faute.
            continue
        champ = REGLES[nom][1]
        if champ in CHAMPS:
            # Un champ de la forme commune : tout produit lu le porte, donc la
            # règle a une cible dès qu'on lit quelque chose.
            continue
        porteurs = sorted(
            produit for produit, extras in SUPPLEMENTS.items() if champ in extras
        )
        if not set(porteurs) & set(lus):
            orphelines.append(
                f"`{nom}` juge `{champ}`, que seul(s) {', '.join(porteurs)} "
                f"porte(nt) ; ce run lit {', '.join(lus) or 'rien'}"
            )
    return orphelines


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
    # **Groupé sur l'identité de la ressource, pas sur son nom.** Deux machines
    # homonymes non conformes se fondraient en un seul refus, et le compte des
    # ressources examinées tomberait juste d'une unité de trop.
    par_ressource: dict[tuple[str, str], list[str]] = {}
    for constat in constats or []:
        cle = (_ressource_de(constat["id"]), constat["name"])
        par_ressource.setdefault(cle, []).append(constat["rule"])

    # La clé porte l'identité pour regrouper et trier, le nom pour être lu :
    # seule la seconde moitié ressort.
    return [
        {"name": cle[1], "reason": ", ".join(sorted(set(regles)))}
        for cle, regles in sorted(par_ressource.items())
    ]


def _ressource_de(identite: str) -> str:
    """La ressource que cette identité désigne, sans la règle qui l'a jugée.

    L'identité est `règle:produit:identifiant` ; ce qui désigne la ressource est
    ce qui suit la règle. Le découpage est ici plutôt que recopié à trois
    endroits, parce que trois copies d'une convention finissent par diverger.
    """
    morceaux = identite.split(":", 1)
    return morceaux[1] if len(morceaux) == 2 else identite


class FilterModule:
    """Ce que la collection publie comme filtres."""

    def filters(self) -> dict[str, object]:
        return {
            "audit_findings": audit_findings,
            "rules_without_target": rules_without_target,
            "audit_refusals": audit_refusals,
            "finding_id": finding_id,
        }
