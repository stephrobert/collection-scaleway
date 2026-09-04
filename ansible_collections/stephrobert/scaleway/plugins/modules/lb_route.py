#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetRoute, UpdateRoute
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_route
short_description: Manage a Scaleway Lb route
version_added: 0.1.0
description:
- Update the configuration of an existing route, specified by its route ID.
- 'The module reads the resource first and writes the whole body, because this operation replaces
  the resource: fields you do not set keep the value the API returns. A second run reports
  no change.'
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
    required: true
  backend_id:
    description:
    - ID of the target backend for the route.
    type: str
  match:
    description:
    - Object defining the match condition for a route to be applied. If an incoming client
      session matches the specified condition (i.e. it has a matching SNI value or HTTP Host
      header value), it will be passed to the target backend.
    type: dict
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway lb route
  stephrobert.scaleway.lb_route:
    zone: <zone>
    route_id: <route_id>
    backend_id: <backend_id>
  register: result
"""

RETURN = r"""
resource:
  description:
  - Retrieve information about an existing route, specified by its route ID. Its full details,
    origin frontend, target backend and match condition, are returned in the response object.
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
    ManageModule,
    Operation,
    run_manage_module,
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
    "route_id": {"type": "str", "required": True},
    "backend_id": {"type": "str"},
    "match": {"type": "dict"},
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
        path="/lb/v1/zones/{zone}/routes/{route_id}",
        path_params=("zone", "route_id"),
        query_params=(),
    ),
    update_operation=Operation(
        id="UpdateRoute",
        method="PUT",
        path="/lb/v1/zones/{zone}/routes/{route_id}",
        path_params=("zone", "route_id"),
        query_params=(),
        body_params=("backend_id", "match"),
    ),
    managed_params=("backend_id", "match"),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
