#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetPrivateNetwork, ListPrivateNetworks
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_private_network_info
short_description: Gather information about Scaleway VPC private networks
version_added: 0.9.0
description:
- Retrieve information about an existing Private Network, specified by its Private Network
  ID. Its full details are returned in the response object.
- List existing Private Networks in the specified region. By default, the Private Networks
  returned in the list are ordered by creation date in ascending order, though this can be
  modified via the order_by field.
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
  private_network_id:
    description:
    - Private Network ID. (UUID format)
    type: str
  dhcp_enabled:
    description:
    - DHCP status to filter for. When true, only Private Networks with managed DHCP enabled
      will be returned.
    type: bool
  name:
    description:
    - Name to filter for. Only Private Networks with names containing this string will be
      returned.
    type: str
  object_storage_private_access_enabled:
    description:
    - Filter by whether Object Storage private access is enabled. When set, only matching
      Private Networks will be returned.
    type: bool
  order_by:
    description:
    - Sort order of the returned Private Networks.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - name_asc
    - name_desc
  private_network_ids:
    description:
    - Private Network IDs to filter for. Only Private Networks with one of these IDs will
      be returned.
    type: list
    elements: str
  tags:
    description:
    - Tags to filter for. Only Private Networks with one or more matching tags will be returned.
    type: list
    elements: str
  vpc_id:
    description:
    - VPC ID to filter for. Only Private Networks belonging to this VPC will be returned.
      (UUID format)
    type: str
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
#
# `private_network_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a Private Network
  stephrobert.scaleway.vpc_private_network_info:
    region: fr-par
    private_network_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List Private Networks
  stephrobert.scaleway.vpc_private_network_info:
    region: fr-par
  register: result
- name: Filter Scaleway VPC private networks by tags
  stephrobert.scaleway.vpc_private_network_info:
    region: fr-par
    tags:
    - production
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve information about an existing Private Network, specified by its Private Network
    ID. Its full details are returned in the response object.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(private_network_id) is provided
  type: dict
  contains:
    id:
      description:
      - Private Network ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the private network.
      returned: when the API returns it
      type: str
    name:
      description:
      - Private Network name.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Scaleway Organization the Private Network belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the Private Network belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region in which the Private Network is available.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags of the Private Network.
      returned: when the API returns it
      type: list
      elements: str
    created_at:
      description:
      - Date the Private Network was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the Private Network was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    subnets:
      description:
      - Private Network subnets.
      returned: when the API returns it
      type: list
      elements: dict
    vpc_id:
      description:
      - VPC the Private Network belongs to. (UUID format)
      returned: when the API returns it
      type: str
    dhcp_enabled:
      description:
      - Defines whether managed DHCP is enabled for this Private Network.
      returned: when the API returns it
      type: bool
    default_route_propagation_enabled:
      description:
      - Defines whether default v4 and v6 routes are propagated for this Private Network.
      returned: when the API returns it
      type: bool
    has_object_storage_private_access:
      description:
      - Defines whether this Private Network is enabled for Object Storage private access.
      returned: when the API returns it
      type: bool
private_networks:
  description:
  - List existing Private Networks in the specified region. By default, the Private Networks
    returned in the list are ordered by creation date in ascending order, though this can
    be modified via the order_by field.
  returned: when I(private_network_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - Private Network ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the private network.
      returned: when the API returns it
      type: str
    name:
      description:
      - Private Network name.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Scaleway Organization the Private Network belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the Private Network belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region in which the Private Network is available.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags of the Private Network.
      returned: when the API returns it
      type: list
      elements: str
    created_at:
      description:
      - Date the Private Network was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the Private Network was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    subnets:
      description:
      - Private Network subnets.
      returned: when the API returns it
      type: list
      elements: dict
    vpc_id:
      description:
      - VPC the Private Network belongs to. (UUID format)
      returned: when the API returns it
      type: str
    dhcp_enabled:
      description:
      - Defines whether managed DHCP is enabled for this Private Network.
      returned: when the API returns it
      type: bool
    default_route_propagation_enabled:
      description:
      - Defines whether default v4 and v6 routes are propagated for this Private Network.
      returned: when the API returns it
      type: bool
    has_object_storage_private_access:
      description:
      - Defines whether this Private Network is enabled for Object Storage private access.
      returned: when the API returns it
      type: bool
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
    "private_network_id": {"type": "str"},
    "dhcp_enabled": {"type": "bool"},
    "name": {"type": "str"},
    "object_storage_private_access_enabled": {"type": "bool"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc", "name_asc", "name_desc"],
    },
    "private_network_ids": {"type": "list", "elements": "str"},
    "tags": {"type": "list", "elements": "str"},
    "vpc_id": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetPrivateNetwork",
        method="GET",
        path="/vpc/v2/regions/{region}/private-networks/{private_network_id}",
        path_params=("region", "private_network_id"),
        query_params=(),
        retry="safe",
    ),
    list_operation=Operation(
        id="ListPrivateNetworks",
        method="GET",
        path="/vpc/v2/regions/{region}/private-networks",
        path_params=("region",),
        query_params=(
            "order_by",
            "name",
            "tags",
            "organization_id",
            "project_id",
            "private_network_ids",
            "vpc_id",
            "dhcp_enabled",
            "object_storage_private_access_enabled",
        ),
        payload_field="private_networks",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    ),
    selector="private_network_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
