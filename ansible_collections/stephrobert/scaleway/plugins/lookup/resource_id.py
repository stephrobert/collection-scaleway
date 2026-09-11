# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
name: resource_id
short_description: Resolve a Scaleway resource name into its identifier
version_added: 0.6.0
author:
  - Stéphane Robert (@stephrobert)
requirements:
  - scaleway >= 2.9.0
description:
  - >-
    Half of the modules in this collection act on a sub-resource carrying its
    own identifier, which only the matching C(_info) module returns. This
    lookup returns that identifier from the name you already know, so a
    playbook does not have to call a module, register its result and dig a
    UUID out of it.
  - >-
    The resolution table is derived from the versioned API contracts, never
    written by hand. A resource that stops being listable, or that loses its
    C(name) field upstream, leaves the table at the next generation instead of
    staying a promise.
  - >-
    The name must match exactly. The Scaleway C(name) query filter matches by
    prefix, which the contract states itself for Instances: C(server1) returns
    both C(server100) and C(server1). The filter is sent to avoid paginating a
    whole fleet, and the exact comparison is always done locally.
notes:
  - >-
    Exactly one match returns the identifier. No exact match and several exact
    matches both fail, and the message names what was found. Returning the
    first of several candidates would make the playbook act on a resource
    nobody designated.
  - >-
    The credential options are declared here rather than inherited from the
    module documentation fragment. A module option carries no C(env) key, so
    its default would silently win over the environment, and a lookup meant
    for a local emulator would reach the real Scaleway API instead.
options:
  _terms:
    description:
      - The identifier parameter you are trying to fill, such as C(server_id).
      - Exactly one, because a lookup that resolved several at once could not
        say which scope belonged to which.
    required: true
    type: str
  name:
    description: Exact name of the resource to resolve.
    required: true
    type: str
  zone:
    description: Zone the resource lives in, for zoned resources.
    type: str
  region:
    description: Region the resource lives in, for regional resources.
    type: str
  profile:
    description: Name of the profile to read in the Scaleway configuration file.
    type: str
    env:
      - name: SCW_PROFILE
  config_file:
    description: Path to the Scaleway configuration file.
    type: path
    env:
      - name: SCW_CONFIG_PATH
  access_key:
    description: Scaleway API access key.
    type: str
    env:
      - name: SCW_ACCESS_KEY
  secret_key:
    description: Scaleway API secret key.
    type: str
    env:
      - name: SCW_SECRET_KEY
  api_url:
    description:
      - URL of the Scaleway API endpoint.
      - Point it at a local emulator to resolve names without credentials.
      - >-
        Falls back to the Scaleway configuration file, then to
        C(https://api.scaleway.com). It carries no default on purpose: a
        default is never unset, so it would always override the profile.
    type: str
    env:
      - name: SCW_API_URL
  api_allow_insecure:
    description: Reach the endpoint without verifying its TLS certificate.
    type: bool
  api_timeout:
    description: Seconds to wait for a single API call.
    type: int
  user_agent:
    description: Value of the User-Agent header sent to the API.
    type: str
  organization_id:
    description: Default Organization ID.
    type: str
    env:
      - name: SCW_DEFAULT_ORGANIZATION_ID
  project_id:
    description: Default Project ID.
    type: str
    env:
      - name: SCW_DEFAULT_PROJECT_ID
"""

EXAMPLES = r"""
- name: Reboot the machine named web-01 without knowing its identifier
  stephrobert.scaleway.instance_server_action:
    zone: fr-par-1
    server_id: >-
      {{ lookup('stephrobert.scaleway.resource_id', 'server_id',
                zone='fr-par-1', name='web-01') }}
    action: reboot
  delegate_to: localhost

- name: Update the backend named api of a named load balancer
  stephrobert.scaleway.lb_backend:
    zone: fr-par-1
    lb_id: "{{ load_balancer_id }}"
    backend_id: >-
      {{ lookup('stephrobert.scaleway.resource_id', 'backend_id',
                zone='fr-par-1', lb_id=load_balancer_id, name='api') }}
    forward_port: 8080
  delegate_to: localhost

- name: Resolve the load balancer itself, then a backend inside it
  ansible.builtin.set_fact:
    load_balancer_id: >-
      {{ lookup('stephrobert.scaleway.resource_id', 'lb_id',
                zone='fr-par-1', name='public') }}
"""

RETURN = r"""
_raw:
  description: The identifier of the single resource carrying that exact name.
  type: list
  elements: str
"""

from ansible.errors import AnsibleLookupError
from ansible.plugins.lookup import LookupBase

from ansible_collections.stephrobert.scaleway.plugins.module_utils.resolution import (
    RESOLUTIONS,
    UNRESOLVABLE,
)
from ansible_collections.stephrobert.scaleway.plugins.module_utils.scaleway import (
    ResolutionError,
    ScalewayApi,
    ScalewayApiError,
    ScalewayConfigurationError,
    resolve_resource_id,
)

#: Ce que ce plugin déclare, donc ce que `set_options` sait recevoir. Tout le
#: reste des arguments nommés est la **portée** de la recherche : elle dépend de
#: la ressource visée, donc elle ne peut pas se déclarer d'avance.
DECLAREES = frozenset(
    {
        "name",
        "zone",
        "region",
        "profile",
        "config_file",
        "access_key",
        "secret_key",
        "api_url",
        "api_allow_insecure",
        "api_timeout",
        "user_agent",
        "organization_id",
        "project_id",
    }
)

#: Ce que le runtime commun attend pour construire son client et borner son
#: attente. La liste est celle du plugin d'inventaire : deux constructions
#: divergentes du même client sont exactement ce que ce dépôt refuse.
VALEURS_DU_CLIENT = (
    "profile",
    "config_file",
    "access_key",
    "secret_key",
    "api_url",
    "api_allow_insecure",
    "api_timeout",
    "user_agent",
    "organization_id",
    "project_id",
)


class LookupModule(LookupBase):
    """Rend l'identifiant d'une ressource nommée, ou refuse en disant pourquoi.

    Le plugin ne décide rien : la table dit où chercher, et
    `resolve_resource_id` dit ce qu'on fait de ce qu'on trouve. Ce qui vit ici
    est la traduction entre les conventions d'Ansible et ces deux-là.
    """

    def run(self, terms, variables=None, **kwargs):
        if len(terms) != 1:
            raise AnsibleLookupError(
                f"resource_id attend exactement un identifiant à résoudre, "
                f"{len(terms)} reçu(s) : {list(terms)}. "
                "Deux identifiants dans un même appel ne pourraient pas dire "
                "quelle portée appartient auquel."
            )

        parametre = str(terms[0])
        lookup = self._table(parametre)

        declarees = {nom: valeur for nom, valeur in kwargs.items() if nom in DECLAREES}
        portee = {nom: valeur for nom, valeur in kwargs.items() if nom not in DECLAREES}
        self.set_options(var_options=variables, direct=declarees)

        nom = self.get_option("name")
        if not nom:
            raise AnsibleLookupError(
                f"resource_id exige `name` : c'est ce qu'on cherche. "
                f"Sans lui, {lookup.operation.id} listerait sans rien sélectionner."
            )

        # La portée d'appel rejoint la portée de la ressource : le runtime rend
        # le chemin depuis un seul dictionnaire, et n'a pas à savoir laquelle
        # des deux a fourni quoi.
        valeurs = dict(portee)
        for cadre in ("zone", "region"):
            if self.get_option(cadre):
                valeurs[cadre] = self.get_option(cadre)

        try:
            api = ScalewayApi.from_values(
                {nom_option: self.get_option(nom_option) for nom_option in VALEURS_DU_CLIENT}
            )
            return [resolve_resource_id(api, lookup, name=nom, values=valeurs)]
        except ScalewayConfigurationError as erreur:
            raise AnsibleLookupError(str(erreur)) from erreur
        except ResolutionError as erreur:
            raise AnsibleLookupError(str(erreur)) from erreur
        except ScalewayApiError as erreur:
            raise AnsibleLookupError(
                f"{lookup.operation.id} a échoué : {erreur.message}"
            ) from erreur

    def _table(self, parametre):
        """La façon de résoudre cet identifiant, ou le refus qui dit pourquoi pas.

        Les trois cas sont distincts, et les confondre coûterait cher :
        l'identifiant est résoluble, il ne l'est pas et le contrat dit pourquoi,
        ou il n'existe pas du tout. Rendre « inconnu » dans le deuxième cas
        enverrait chercher une faute de frappe dans un nom qui est correct.
        """
        if parametre in RESOLUTIONS:
            return RESOLUTIONS[parametre]

        if parametre in UNRESOLVABLE:
            raise AnsibleLookupError(
                f"{parametre} ne se résout pas par un nom : {UNRESOLVABLE[parametre]}. "
                "L'identifiant se lit sur le module d'information correspondant."
            )

        connus = ", ".join(sorted(RESOLUTIONS))
        raise AnsibleLookupError(
            f"{parametre} n'est pas un identifiant que les contrats permettent de "
            f"résoudre. Résolubles : {connus}."
        )
