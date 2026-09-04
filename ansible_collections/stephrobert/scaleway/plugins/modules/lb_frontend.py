#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetFrontend, UpdateFrontend
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_frontend
short_description: Manage a Scaleway Lb frontend
version_added: 0.1.0
description:
- Update a given frontend, specified by its frontend ID. You can update configuration parameters
  including its name and the port it listens on. Note that the request type is PUT and not
  PATCH. You must set all parameters.
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
  frontend_id:
    description:
    - Frontend ID.
    type: str
    required: true
  backend_id:
    description:
    - Backend ID (ID of the backend the frontend should pass traffic to).
    type: str
    required: true
  certificate_id:
    description:
    - Certificate ID, deprecated in favor of certificate_ids array.
    - Deprecated by the Scaleway API contract.
    type: str
  certificate_ids:
    description:
    - List of SSL/TLS certificate IDs to bind to the frontend.
    type: list
    elements: str
  connection_rate_limit:
    description:
    - Rate limit for new connections established on this frontend. Use 0 value to disable,
      else value is connections per second.
    type: int
  enable_access_logs:
    description:
    - Defines whether to enable access logs on the frontend.
    type: bool
  enable_http3:
    description:
    - Defines whether to enable HTTP/3 protocol on the frontend.
    type: bool
  inbound_port:
    description:
    - Port the frontend should listen on.
    type: int
    required: true
  name:
    description:
    - Frontend name.
    type: str
    required: true
  timeout_client:
    description:
    - Maximum allowed inactivity time on the client side. (in milliseconds)
    type: float
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway lb frontend
  stephrobert.scaleway.lb_frontend:
    zone: <zone>
    frontend_id: <frontend_id>
    backend_id: <backend_id>
    inbound_port: <inbound_port>
    name: <name>
  register: result
"""

RETURN = r"""
resource:
  description:
  - Get the full details of a given frontend, specified by its frontend ID. The response contains
    the frontend's full configuration parameters including the backend it is attached to,
    the port it listens on, and any certificates it has.
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
    "frontend_id": {"type": "str", "required": True},
    "backend_id": {"type": "str", "required": True},
    "certificate_id": {"type": "str"},
    "certificate_ids": {"type": "list", "elements": "str"},
    "connection_rate_limit": {"type": "int"},
    "enable_access_logs": {"type": "bool"},
    "enable_http3": {"type": "bool"},
    "inbound_port": {"type": "int", "required": True},
    "name": {"type": "str", "required": True},
    "timeout_client": {"type": "float"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetFrontend",
        method="GET",
        path="/lb/v1/zones/{zone}/frontends/{frontend_id}",
        path_params=("zone", "frontend_id"),
        query_params=(),
    ),
    update_operation=Operation(
        id="UpdateFrontend",
        method="PUT",
        path="/lb/v1/zones/{zone}/frontends/{frontend_id}",
        path_params=("zone", "frontend_id"),
        query_params=(),
        body_params=(
            "name",
            "inbound_port",
            "backend_id",
            "timeout_client",
            "certificate_id",
            "certificate_ids",
            "enable_http3",
            "connection_rate_limit",
            "enable_access_logs",
        ),
    ),
    managed_params=(
        "name",
        "inbound_port",
        "backend_id",
        "timeout_client",
        "certificate_id",
        "certificate_ids",
        "enable_http3",
        "connection_rate_limit",
        "enable_access_logs",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
