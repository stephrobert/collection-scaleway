# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Désigner ce sur quoi on opère, d'une seule façon.

Quatre grammaires coexistaient pour une seule question : un groupe d'inventaire
pour les enchaînements, un nom pour le lookup, un identifiant pour les modules
(#208). Un rôle appelé depuis le playbook de quelqu'un d'autre doit accepter la
même réponse que les autres, sinon chacun réinvente son sélecteur et
l'utilisateur apprend trois fois la même chose.

**Les refus ne sont pas inventés ici, ils sont unifiés.** Chacun existait déjà,
mesuré, et prouvé par une mutation :

* **une ambiguïté se refuse, elle ne se tranche pas.** Rendre le premier d'une
  liste ferait agir un playbook sur une ressource que personne n'a désignée
  (ADR-019) ;
* **un nom se compare exactement.** Le filtre `name` de l'API correspond par
  préfixe, donc `server1` rend aussi `server100` ; ici la comparaison est
  locale et exacte ;
* **une clé inconnue se refuse.** `tag:` au lieu de `tags:` ne doit pas
  sélectionner zéro machine en silence : une sélection vide et une faute de
  frappe se ressemblent trop pour qu'on les confonde.

**Le piège que cette forme ouvre, et qu'elle ferme.** `tags: [production, web]`
ne dit pas s'il faut toutes les étiquettes ou une seule. Le défaut est `all`,
c'est à dire la sélection la plus étroite : pour une opération qui écrit, se
tromper du côté sûr veut dire toucher moins de machines, jamais plus.
"""

from __future__ import annotations

from ansible.errors import AnsibleFilterError

try:  # pragma: no cover - le chemin d'import diffère entre collection et tests
    from ansible_collections.stephrobert.scaleway.plugins.module_utils.selecteur import (
        SelecteurError,
        correspond,
        etiquettes_voulues,
        valider,
    )
except ImportError:  # pragma: no cover
    from ..module_utils.selecteur import (  # type: ignore[no-redef]
        SelecteurError,
        correspond,
        etiquettes_voulues,
        valider,
    )

DOCUMENTATION = r"""
name: select_hosts
short_description: Resolve a selector into inventory host names
description:
  - Turns C(group), C(name) or C(tags) into the list of inventory hosts it
    designates, so every operation accepts the same way of saying what to act
    on.
  - Refuses an ambiguity rather than settling it, refuses an unknown key rather
    than selecting nothing, and compares names exactly.
options:
  _input:
    description:
      - The selector. Exactly one of C(group), C(name) or C(tags), plus
        C(match) when C(tags) is used.
    type: dict
    required: true
  groups:
    description: Ansible's own C(groups), passed through.
    type: dict
    required: true
  hostvars:
    description: Ansible's own C(hostvars), passed through.
    type: dict
    required: true
"""

RETURN = r"""
_value:
  description: The inventory host names the selector designates, sorted.
  type: list
  elements: str
"""

EXAMPLES = r"""
- name: Every production machine, by tag
  ansible.builtin.set_fact:
    cibles: >-
      {{ {'tags': ['production', 'web']}
         | stephrobert.scaleway.select_hosts(groups=groups, hostvars=hostvars) }}
"""

#: Les trois façons de désigner, et rien d'autre. Une clé hors de cette liste
#: est une faute de frappe, et une faute de frappe qui sélectionne zéro machine
#: se lit comme un parc vide.
CRITERES = ("group", "name", "tags")


def _par_groupe(nom: str, groups: dict) -> list[str]:
    return sorted(groups.get(nom, []))


def _par_nom(cherche: str, machines: dict) -> list[str]:
    """La comparaison est exacte, et une ambiguïté se refuse.

    Le filtre `name` de l'API Scaleway correspond par préfixe, ce que le
    contrat énonce pour les Instances : `server1` rend aussi `server100`. Ici
    la comparaison porte sur l'inventaire, donc localement, et elle est exacte.
    """
    trouves = sorted(
        hote for hote, variables in machines.items() if variables.get("scaleway_name") == cherche
    )
    if len(trouves) > 1:
        raise AnsibleFilterError(
            f"le nom `{cherche}` désigne {len(trouves)} machines : "
            f"{', '.join(trouves)}. Rendre la première ferait agir sur une "
            "ressource que personne n'a désignée (ADR-019)."
        )
    return trouves


def _par_etiquettes(etiquettes: object, mode: str, machines: dict) -> list[str]:
    """La recherche, la grammaire étant déjà validée."""
    voulues = etiquettes_voulues(etiquettes)
    return sorted(
        hote
        for hote, variables in machines.items()
        if correspond(voulues, set(variables.get("scaleway_tags") or []), mode)
    )


def select_hosts(selecteur: object, groups: object, hostvars: object) -> list[str]:
    """Les machines de l'inventaire que ce sélecteur désigne."""
    try:
        critere, valeur, mode = valider(selecteur, CRITERES)
    except SelecteurError as erreur:
        # La grammaire est commune, l'erreur que le contexte attend ne l'est
        # pas : un filtre lève `AnsibleFilterError`, et c'est ce qu'Ansible
        # sait rapporter avec le nom du filtre fautif.
        raise AnsibleFilterError(str(erreur)) from erreur

    machines = dict(hostvars or {})
    if critere == "group":
        return _par_groupe(str(valeur), dict(groups or {}))
    if critere == "name":
        return _par_nom(str(valeur), machines)
    try:
        return _par_etiquettes(valeur, mode, machines)
    except SelecteurError as erreur:
        raise AnsibleFilterError(str(erreur)) from erreur


class FilterModule:
    """Ce que la collection publie comme filtres."""

    def filters(self) -> dict[str, object]:
        return {"select_hosts": select_hosts}
