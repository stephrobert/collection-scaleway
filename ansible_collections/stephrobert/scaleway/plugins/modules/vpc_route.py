#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetRoute, UpdateRoute
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_route
short_description: Manage a Scaleway VPC route
version_added: 0.9.0
description:
- Update parameters of the specified Route.
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
  route_id:
    description:
    - Route ID. (UUID format)
    type: str
    required: true
  description:
    description:
    - Route description.
    - 'To clear this field, write `description: ""`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  destination:
    description:
    - Destination of the Route. (IP network)
    - 'To clear this field, write `destination: ""`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  nexthop_private_network_id:
    description:
    - ID of the nexthop private network. (UUID format)
    - 'To clear this field, write `nexthop_private_network_id: ""`; omit the option to leave
      the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  nexthop_resource_id:
    description:
    - ID of the nexthop resource. (UUID format)
    - 'To clear this field, write `nexthop_resource_id: ""`; omit the option to leave the
      current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  nexthop_vpc_connector_id:
    description:
    - ID of the nexthop VPC connector. (UUID format)
    - 'To clear this field, write `nexthop_vpc_connector_id: ""`; omit the option to leave
      the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  tags:
    description:
    - Tags of the Route.
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

- name: Update a Scaleway VPC route
  stephrobert.scaleway.vpc_route:
    region: fr-par
    route_id: 11111111-2222-3333-4444-555555555555
    description: Managed by Ansible
  register: result
- name: Preview the change on a Scaleway VPC route without writing
  stephrobert.scaleway.vpc_route:
    region: fr-par
    route_id: 11111111-2222-3333-4444-555555555555
    description: Managed by Ansible
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
resource:
  description:
  - Retrieve details of an existing Route, specified by its Route ID.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Route ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the route.
      returned: when the API returns it
      type: str
    description:
      description:
      - Route description.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags of the Route.
      returned: when the API returns it
      type: list
      elements: str
    vpc_id:
      description:
      - VPC the Route belongs to. (UUID format)
      returned: when the API returns it
      type: str
    destination:
      description:
      - Destination of the Route. (IP network)
      returned: when the API returns it
      type: str
    nexthop_resource_id:
      description:
      - ID of the nexthop resource. (UUID format)
      returned: when the API returns it
      type: str
    nexthop_private_network_id:
      description:
      - ID of the nexthop private network. (UUID format)
      returned: when the API returns it
      type: str
    nexthop_vpc_connector_id:
      description:
      - ID of the nexthop VPC connector. (UUID format)
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date the Route was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the Route was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    is_read_only:
      description:
      - Defines whether the route can be modified or deleted by the user.
      returned: when the API returns it
      type: bool
    type:
      description:
      - Type of the Route.
      returned: when the API returns it
      type: str
    region:
      description:
      - Region of the Route.
      returned: when the API returns it
      type: str
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
    "route_id": {"type": "str", "required": True},
    "description": {"type": "str"},
    "destination": {"type": "str"},
    "nexthop_private_network_id": {"type": "str"},
    "nexthop_resource_id": {"type": "str"},
    "nexthop_vpc_connector_id": {"type": "str"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetRoute",
        method="GET",
        path="/vpc/v2/regions/{region}/routes/{route_id}",
        path_params=("region", "route_id"),
        query_params=(),
        retry="safe",
    ),
    update_operation=Operation(
        id="UpdateRoute",
        method="PATCH",
        path="/vpc/v2/regions/{region}/routes/{route_id}",
        path_params=("region", "route_id"),
        query_params=(),
        body_params=(
            "description",
            "tags",
            "destination",
            "nexthop_resource_id",
            "nexthop_private_network_id",
            "nexthop_vpc_connector_id",
        ),
        retry="limited",
    ),
    managed_params=(
        "description",
        "tags",
        "destination",
        "nexthop_resource_id",
        "nexthop_private_network_id",
        "nexthop_vpc_connector_id",
    ),
    comparisons=(
        ("description", "scalar"),
        ("destination", "scalar"),
        ("nexthop_private_network_id", "scalar"),
        ("nexthop_resource_id", "scalar"),
        ("nexthop_vpc_connector_id", "scalar"),
        ("tags", "ordered_list"),
    ),
    nullable_params=(
        "description",
        "destination",
        "nexthop_private_network_id",
        "nexthop_resource_id",
        "nexthop_vpc_connector_id",
        "tags",
    ),
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
