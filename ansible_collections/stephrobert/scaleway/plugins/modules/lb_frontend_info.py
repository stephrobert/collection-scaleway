#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetFrontend, ListFrontends
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_frontend_info
short_description: Gather information about Scaleway Load Balancer frontends
version_added: 0.1.0
description:
- Get the full details of a given frontend, specified by its frontend ID. The response contains
  the frontend's full configuration parameters including the backend it is attached to, the
  port it listens on, and any certificates it has.
- List all the frontends of a Load Balancer, specified by its Load Balancer ID. By default,
  results are returned in ascending order by the creation date of each frontend. The response
  is an array of frontend objects, containing full details of each one including the port
  they listen on and the backend they are attached to.
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
  lb_id:
    description:
    - Load Balancer ID.
    type: str
  name:
    description:
    - Name of the frontend to filter for.
    type: str
  order_by:
    description:
    - Sort order of frontends in the response.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - name_asc
    - name_desc
  page:
    description:
    - The page number to return, from the paginated results.
    type: int
  page_size:
    description:
    - Number of frontends to return.
    type: int
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get a frontend
  stephrobert.scaleway.lb_frontend_info:
    zone: fr-par-1
    frontend_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List frontends of a given Load Balancer
  stephrobert.scaleway.lb_frontend_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
frontends:
  description:
  - List all the frontends of a Load Balancer, specified by its Load Balancer ID. By default,
    results are returned in ascending order by the creation date of each frontend. The response
    is an array of frontend objects, containing full details of each one including the port
    they listen on and the backend they are attached to.
  returned: when I(frontend_id) is omitted
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
    "frontend_id": {"type": "str"},
    "lb_id": {"type": "str"},
    "name": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc", "name_asc", "name_desc"],
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
        id="GetFrontend",
        method="GET",
        path="/lb/v1/zones/{zone}/frontends/{frontend_id}",
        path_params=("zone", "frontend_id"),
        query_params=(),
    ),
    list_operation=Operation(
        id="ListFrontends",
        method="GET",
        path="/lb/v1/zones/{zone}/lbs/{lb_id}/frontends",
        path_params=("zone", "lb_id"),
        query_params=("name", "order_by", "page", "page_size"),
        payload_field="frontends",
        is_list=True,
    ),
    selector="frontend_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
