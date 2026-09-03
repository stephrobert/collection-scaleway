#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetLb, ListLbs
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_load_balancer_info
short_description: Gather information about Scaleway Load Balancer load balancers
version_added: 0.1.0
description:
- Retrieve information about an existing Load Balancer, specified by its Load Balancer ID.
  Its full details, including name, status and IP address, are returned in the response object.
- List all Load Balancers in the specified zone, for a Scaleway Organization or Scaleway Project.
  By default, the Load Balancers returned in the list are ordered by creation date in ascending
  order, though this can be modified via the `order_by` field.
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
  lb_id:
    description:
    - Load Balancer ID.
    type: str
  lb_ids:
    description:
    - Filter by lb_ids, only Load Balancers with these IDs will be returned.
    type: list
    elements: str
  name:
    description:
    - Load Balancer name to filter for.
    type: str
  order_by:
    description:
    - Sort order of Load Balancers in the response.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - name_asc
    - name_desc
  page:
    description:
    - Page number to return, from the paginated results.
    type: int
  page_size:
    description:
    - Number of Load Balancers to return.
    type: int
  tags:
    description:
    - Filter by tag, only Load Balancers with one or more matching tags will be returned.
    type: list
    elements: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get a Load Balancer
  stephrobert.scaleway.lb_load_balancer_info:
    zone: fr-par-1
    lb_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List Load Balancers
  stephrobert.scaleway.lb_load_balancer_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
lbs:
  description:
  - List all Load Balancers in the specified zone, for a Scaleway Organization or Scaleway
    Project. By default, the Load Balancers returned in the list are ordered by creation date
    in ascending order, though this can be modified via the `order_by` field.
  returned: when I(lb_id) is omitted
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
    "lb_id": {"type": "str"},
    "lb_ids": {"type": "list", "elements": "str"},
    "name": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc", "name_asc", "name_desc"],
    },
    "page": {"type": "int"},
    "page_size": {"type": "int"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetLb",
        method="GET",
        path="/lb/v1/zones/{zone}/lbs/{lb_id}",
        path_params=("zone", "lb_id"),
        query_params=(),
    ),
    list_operation=Operation(
        id="ListLbs",
        method="GET",
        path="/lb/v1/zones/{zone}/lbs",
        path_params=("zone",),
        query_params=(
            "name",
            "order_by",
            "page_size",
            "page",
            "organization_id",
            "project_id",
            "tags",
            "lb_ids",
        ),
        payload_field="lbs",
        is_list=True,
    ),
    selector="lb_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
