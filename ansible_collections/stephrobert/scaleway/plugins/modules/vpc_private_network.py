#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetPrivateNetwork, UpdatePrivateNetwork
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_private_network
short_description: Manage a Scaleway VPC private network
version_added: 0.9.0
description:
- Update parameters (such as name or tags) of an existing Private Network, specified by its
  Private Network ID.
- The module reads the resource first and writes only the fields that differ, so a second
  run reports no change.
author:
- Stéphane Robert (@stephrobert)
options:
  region:
    description:
    - The region you want to target
    type: str
    required: true
    choices:
    - fr-par
    - it-mil
    - nl-ams
    - pl-waw
  private_network_id:
    description:
    - Private Network ID. (UUID format)
    type: str
    required: true
  default_route_propagation_enabled:
    description:
    - Defines whether default v4 and v6 routes are propagated for this Private Network.
    - 'The contract marks this field clearable, but bool has no empty value, so the API cannot
      clear it. Setting it to null is refused: this API reads null as "field not provided"
      and would change nothing.'
    type: bool
  name:
    description:
    - Name for the Private Network.
    - 'To clear this field, write `name: ""`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  tags:
    description:
    - Tags for the Private Network.
    - 'To clear this field, write `tags: []`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: list
    elements: str
attributes:
  check_mode:
    description: In check mode the module reads the resource and compares it, then reports
      what it would write without writing it.
    support: full
  diff_mode:
    description: The module reports the fields that differ, read through the same projection
      the comparison uses.
    support: full
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# The module reads the resource, compares, and writes only what
# differs: run it twice and the second run reports no change.
#
# Check mode compares without writing, and `--diff` shows what would
# change. A parameter you do not pass is a parameter the module does
# not touch.

- name: Update a Scaleway VPC private network
  stephrobert.scaleway.vpc_private_network:
    region: fr-par
    private_network_id: 11111111-2222-3333-4444-555555555555
    name: my-private-network
  register: result
- name: Preview the change on a Scaleway VPC private network without writing
  stephrobert.scaleway.vpc_private_network:
    region: fr-par
    private_network_id: 11111111-2222-3333-4444-555555555555
    name: my-private-network
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
resource:
  description:
  - Retrieve information about an existing Private Network, specified by its Private Network
    ID. Its full details are returned in the response object.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Private Network ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the private network.
      returned: when the API returns it
      type: str
    name:
      description:
      - Private Network name.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Scaleway Organization the Private Network belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the Private Network belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region in which the Private Network is available.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags of the Private Network.
      returned: when the API returns it
      type: list
      elements: str
    created_at:
      description:
      - Date the Private Network was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the Private Network was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    subnets:
      description:
      - Private Network subnets.
      returned: when the API returns it
      type: list
      elements: dict
    vpc_id:
      description:
      - VPC the Private Network belongs to. (UUID format)
      returned: when the API returns it
      type: str
    dhcp_enabled:
      description:
      - Defines whether managed DHCP is enabled for this Private Network.
      returned: when the API returns it
      type: bool
    default_route_propagation_enabled:
      description:
      - Defines whether default v4 and v6 routes are propagated for this Private Network.
      returned: when the API returns it
      type: bool
    has_object_storage_private_access:
      description:
      - Defines whether this Private Network is enabled for Object Storage private access.
      returned: when the API returns it
      type: bool
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
    ManageModule,
    Operation,
    poser_les_temoins,
    run_manage_module,
    scaleway_argument_spec,
)

#: Options propres au module, traduites depuis le contrat.
MODULE_ARGUMENT_SPEC = {
    "region": {
        "type": "str",
        "required": True,
        "choices": ["fr-par", "it-mil", "nl-ams", "pl-waw"],
    },
    "private_network_id": {"type": "str", "required": True},
    "default_route_propagation_enabled": {"type": "bool"},
    "name": {"type": "str"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetPrivateNetwork",
        method="GET",
        path="/vpc/v2/regions/{region}/private-networks/{private_network_id}",
        path_params=("region", "private_network_id"),
        query_params=(),
        retry="safe",
    ),
    update_operation=Operation(
        id="UpdatePrivateNetwork",
        method="PATCH",
        path="/vpc/v2/regions/{region}/private-networks/{private_network_id}",
        path_params=("region", "private_network_id"),
        query_params=(),
        body_params=("name", "tags", "default_route_propagation_enabled"),
        retry="limited",
    ),
    managed_params=("name", "tags", "default_route_propagation_enabled"),
    comparisons=(
        ("default_route_propagation_enabled", "scalar"),
        ("name", "scalar"),
        ("tags", "ordered_list"),
    ),
    nullable_params=("default_route_propagation_enabled", "name", "tags"),
)

#: Ce que le contrat déclare effaçable. Ansible n'appelle un `fallback`
#: que sur une clé absente de l'invocation : le témoin note le nom sans
#: rien injecter, ce qui sépare `champ: null` de `champ` omis.
OMISSIONS = poser_les_temoins(ARGUMENT_SPEC, MODULE.nullable_params)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE, OMISSIONS)


if __name__ == "__main__":
    main()
