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
version_added: 0.4.0
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
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.
#
# `route_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a route
  stephrobert.scaleway.lb_route_info:
    zone: fr-par-1
    route_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List all routes
  stephrobert.scaleway.lb_route_info:
    zone: fr-par-1
  register: result
- name: Filter Scaleway Load Balancer routes by frontend_id
  stephrobert.scaleway.lb_route_info:
    zone: fr-par-1
    frontend_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve information about an existing route, specified by its route ID. Its full details,
    origin frontend, target backend and match condition, are returned in the response object.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(route_id) is provided
  type: dict
  contains:
    id:
      description:
      - Route ID.
      returned: when the API returns it
      type: str
    frontend_id:
      description:
      - ID of the source frontend.
      returned: when the API returns it
      type: str
    backend_id:
      description:
      - ID of the target backend.
      returned: when the API returns it
      type: str
    match:
      description:
      - Object defining the match condition for a route to be applied. If an incoming client
        session matches the specified condition (i.e. it has a matching SNI value or HTTP
        Host header value), it will be passed to the target backend.
      returned: when the API returns it
      type: dict
    created_at:
      description:
      - Date on which the route was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the route was last updated. (RFC 3339 format)
      returned: when the API returns it
      type: str
routes:
  description:
  - List all routes for a given frontend. The response is an array of routes, each one with
    a specified backend to direct to if a certain condition is matched (based on the value
    of the SNI field or HTTP Host header).
  returned: when I(route_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - Route ID.
      returned: when the API returns it
      type: str
    frontend_id:
      description:
      - ID of the source frontend.
      returned: when the API returns it
      type: str
    backend_id:
      description:
      - ID of the target backend.
      returned: when the API returns it
      type: str
    match:
      description:
      - Object defining the match condition for a route to be applied. If an incoming client
        session matches the specified condition (i.e. it has a matching SNI value or HTTP
        Host header value), it will be passed to the target backend.
      returned: when the API returns it
      type: dict
    created_at:
      description:
      - Date on which the route was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the route was last updated. (RFC 3339 format)
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
        query_params=("order_by", "frontend_id"),
        payload_field="routes",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
    ),
    selector="route_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
