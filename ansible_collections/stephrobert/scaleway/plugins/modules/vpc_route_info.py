#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetRoute
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_route_info
short_description: Gather information about Scaleway VPC routes
version_added: 0.9.0
description:
- Retrieve details of an existing Route, specified by its Route ID.
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
attributes:
  check_mode:
    description: This module only reads, so check mode changes nothing about how it runs.
    support: full
  diff_mode:
    description: This module changes nothing, so it has no difference to report.
    support: none
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.

- name: Get a Route
  stephrobert.scaleway.vpc_route_info:
    region: fr-par
    route_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve details of an existing Route, specified by its Route ID.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
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
    InfoModule,
    Operation,
    run_info_module,
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
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetRoute",
        method="GET",
        path="/vpc/v2/regions/{region}/routes/{route_id}",
        path_params=("region", "route_id"),
        query_params=(),
        retry="safe",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
