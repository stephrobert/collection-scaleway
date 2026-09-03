#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetBackend, ListBackends
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_backend_info
short_description: Gather information about Scaleway Load Balancer backends
version_added: 0.1.0
description:
- Get the full details of a given backend, specified by its backend ID. The response contains
  the backend's full configuration parameters including protocol, port and forwarding algorithm.
- List all the backends of a Load Balancer, specified by its Load Balancer ID. By default,
  results are returned in ascending order by the creation date of each backend. The response
  is an array of backend objects, containing full details of each one including their configuration
  parameters such as protocol, port and forwarding algorithm.
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
  backend_id:
    description:
    - Backend ID.
    type: str
  lb_id:
    description:
    - Load Balancer ID.
    type: str
  name:
    description:
    - Name of the backend to filter for.
    type: str
  order_by:
    description:
    - Sort order of backends in the response.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - name_asc
    - name_desc
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get a backend of a given Load Balancer
  stephrobert.scaleway.lb_backend_info:
    zone: fr-par-1
    backend_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List the backends of a given Load Balancer
  stephrobert.scaleway.lb_backend_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
backends:
  description:
  - List all the backends of a Load Balancer, specified by its Load Balancer ID. By default,
    results are returned in ascending order by the creation date of each backend. The response
    is an array of backend objects, containing full details of each one including their configuration
    parameters such as protocol, port and forwarding algorithm.
  returned: when I(backend_id) is omitted
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
    "backend_id": {"type": "str"},
    "lb_id": {"type": "str"},
    "name": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc", "name_asc", "name_desc"],
    },
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetBackend",
        method="GET",
        path="/lb/v1/zones/{zone}/backends/{backend_id}",
        path_params=("zone", "backend_id"),
        query_params=(),
    ),
    list_operation=Operation(
        id="ListBackends",
        method="GET",
        path="/lb/v1/zones/{zone}/lbs/{lb_id}/backends",
        path_params=("zone", "lb_id"),
        query_params=("name", "order_by"),
        payload_field="backends",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
    ),
    selector="backend_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
