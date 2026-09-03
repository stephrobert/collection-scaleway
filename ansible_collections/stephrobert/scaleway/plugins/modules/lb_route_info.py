#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetRoute, ListRoutes
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_route_info
short_description: Gather information about Scaleway Load Balancer routes
version_added: 0.1.0
description:
- Retrieve information about an existing route, specified by its route ID. Its full details,
  origin frontend, target backend and match condition, are returned in the response object.
- List all routes for a given frontend. The response is an array of routes, each one with
  a specified backend to direct to if a certain condition is matched (based on the value of
  the SNI field or HTTP Host header).
author:
- Stéphane Robert (@stephrobert)
options:
  zone:
    description:
    - The zone you want to target
    type: str
    required: true
    choices:
    - fr-par-1
    - fr-par-2
    - nl-ams-1
    - nl-ams-2
    - nl-ams-3
    - pl-waw-1
    - pl-waw-2
    - pl-waw-3
  route_id:
    description:
    - Route ID.
    type: str
  frontend_id:
    description:
    - Frontend ID to filter for, only Routes from this Frontend will be returned.
    type: str
  order_by:
    description:
    - Sort order of routes in the response.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
  page:
    description:
    - The page number to return, from the paginated results.
    type: int
  page_size:
    description:
    - The number of route objects to return.
    type: int
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get a route
  stephrobert.scaleway.lb_route_info:
    zone: fr-par-1
    route_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List all routes
  stephrobert.scaleway.lb_route_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
routes:
  description:
  - List all routes for a given frontend. The response is an array of routes, each one with
    a specified backend to direct to if a certain condition is matched (based on the value
    of the SNI field or HTTP Host header).
  returned: when I(route_id) is omitted
  type: list
  elements: dict
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
    "zone": {
        "type": "str",
        "required": True,
        "choices": [
            "fr-par-1",
            "fr-par-2",
            "nl-ams-1",
            "nl-ams-2",
            "nl-ams-3",
            "pl-waw-1",
            "pl-waw-2",
            "pl-waw-3",
        ],
    },
    "route_id": {"type": "str"},
    "frontend_id": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc"],
    },
    "page": {"type": "int"},
    "page_size": {"type": "int"},
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
        path="/lb/v1/zones/{zone}/routes/{route_id}",
        path_params=("zone", "route_id"),
        query_params=(),
    ),
    list_operation=Operation(
        id="ListRoutes",
        method="GET",
        path="/lb/v1/zones/{zone}/routes",
        path_params=("zone",),
        query_params=("order_by", "page_size", "page", "frontend_id"),
        payload_field="routes",
        is_list=True,
    ),
    selector="route_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
