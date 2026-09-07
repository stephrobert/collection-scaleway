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
short_description: Gather information about Scaleway Load Balancers
version_added: 0.4.0
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
  tags:
    description:
    - Filter by tag, only Load Balancers with one or more matching tags will be returned.
    type: list
    elements: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.
#
# `lb_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a Load Balancer
  stephrobert.scaleway.lb_load_balancer_info:
    zone: fr-par-1
    lb_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List Load Balancers
  stephrobert.scaleway.lb_load_balancer_info:
    zone: fr-par-1
  register: result
- name: Filter Scaleway Load Balancers by tags
  stephrobert.scaleway.lb_load_balancer_info:
    zone: fr-par-1
    tags:
    - production
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve information about an existing Load Balancer, specified by its Load Balancer ID.
    Its full details, including name, status and IP address, are returned in the response
    object.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(lb_id) is provided
  type: dict
  contains:
    id:
      description:
      - Underlying Instance ID.
      returned: when the API returns it
      type: str
    name:
      description:
      - Load Balancer name.
      returned: when the API returns it
      type: str
    description:
      description:
      - Load Balancer description.
      returned: when the API returns it
      type: str
    status:
      description:
      - Load Balancer status.
      returned: when the API returns it
      type: str
    instances:
      description:
      - List of underlying Instances.
      returned: when the API returns it
      type: list
      elements: dict
    organization_id:
      description:
      - Scaleway Organization ID.
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project ID.
      returned: when the API returns it
      type: str
    ip:
      description:
      - List of IP addresses attached to the Load Balancer.
      returned: when the API returns it
      type: list
      elements: dict
    tags:
      description:
      - Load Balancer tags.
      returned: when the API returns it
      type: list
      elements: str
    frontend_count:
      description:
      - Number of frontends the Load Balancer has.
      returned: when the API returns it
      type: int
    backend_count:
      description:
      - Number of backends the Load Balancer has.
      returned: when the API returns it
      type: int
    type:
      description:
      - Load Balancer offer type.
      returned: when the API returns it
      type: str
    subscriber:
      description:
      - Subscriber information.
      returned: when the API returns it
      type: dict
    ssl_compatibility_level:
      description:
      - Determines the minimal SSL version which needs to be supported on client side.
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date on which the Load Balancer was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the Load Balancer was last updated. (RFC 3339 format)
      returned: when the API returns it
      type: str
    private_network_count:
      description:
      - Number of Private Networks attached to the Load Balancer.
      returned: when the API returns it
      type: int
    route_count:
      description:
      - Number of routes configured on the Load Balancer.
      returned: when the API returns it
      type: int
    region:
      description:
      - The region the Load Balancer is in.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: str
    zone:
      description:
      - The zone the Load Balancer is in.
      returned: when the API returns it
      type: str
lbs:
  description:
  - List all Load Balancers in the specified zone, for a Scaleway Organization or Scaleway
    Project. By default, the Load Balancers returned in the list are ordered by creation date
    in ascending order, though this can be modified via the `order_by` field.
  returned: when I(lb_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - Underlying Instance ID.
      returned: when the API returns it
      type: str
    name:
      description:
      - Load Balancer name.
      returned: when the API returns it
      type: str
    description:
      description:
      - Load Balancer description.
      returned: when the API returns it
      type: str
    status:
      description:
      - Load Balancer status.
      returned: when the API returns it
      type: str
    instances:
      description:
      - List of underlying Instances.
      returned: when the API returns it
      type: list
      elements: dict
    organization_id:
      description:
      - Scaleway Organization ID.
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project ID.
      returned: when the API returns it
      type: str
    ip:
      description:
      - List of IP addresses attached to the Load Balancer.
      returned: when the API returns it
      type: list
      elements: dict
    tags:
      description:
      - Load Balancer tags.
      returned: when the API returns it
      type: list
      elements: str
    frontend_count:
      description:
      - Number of frontends the Load Balancer has.
      returned: when the API returns it
      type: int
    backend_count:
      description:
      - Number of backends the Load Balancer has.
      returned: when the API returns it
      type: int
    type:
      description:
      - Load Balancer offer type.
      returned: when the API returns it
      type: str
    subscriber:
      description:
      - Subscriber information.
      returned: when the API returns it
      type: dict
    ssl_compatibility_level:
      description:
      - Determines the minimal SSL version which needs to be supported on client side.
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date on which the Load Balancer was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the Load Balancer was last updated. (RFC 3339 format)
      returned: when the API returns it
      type: str
    private_network_count:
      description:
      - Number of Private Networks attached to the Load Balancer.
      returned: when the API returns it
      type: int
    route_count:
      description:
      - Number of routes configured on the Load Balancer.
      returned: when the API returns it
      type: int
    region:
      description:
      - The region the Load Balancer is in.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: str
    zone:
      description:
      - The zone the Load Balancer is in.
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
    "lb_id": {"type": "str"},
    "lb_ids": {"type": "list", "elements": "str"},
    "name": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc", "name_asc", "name_desc"],
    },
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
        query_params=("name", "order_by", "organization_id", "project_id", "tags", "lb_ids"),
        payload_field="lbs",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
    ),
    selector="lb_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
