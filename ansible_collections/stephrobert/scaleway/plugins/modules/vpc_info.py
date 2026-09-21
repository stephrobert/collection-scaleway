#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetVPC, ListVPCs
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_info
short_description: Gather information about Scaleway VPCs
version_added: 0.9.0
description:
- Retrieve details of an existing VPC, specified by its VPC ID.
- List existing VPCs in the specified region.
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
  vpc_id:
    description:
    - VPC ID. (UUID format)
    type: str
  is_default:
    description:
    - Defines whether to filter only for VPCs which are the default one for their Project.
    type: bool
  name:
    description:
    - Name to filter for. Only VPCs with names containing this string will be returned.
    type: str
  object_storage_private_access_enabled:
    description:
    - Defines whether to filter only for VPCs with Object Storage private access enabled.
    type: bool
  order_by:
    description:
    - Sort order of the returned VPCs.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - name_asc
    - name_desc
  routing_enabled:
    description:
    - Defines whether to filter only for VPCs which route traffic between their Private Networks.
    type: bool
  tags:
    description:
    - Tags to filter for. Only VPCs with one or more matching tags will be returned.
    type: list
    elements: str
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
# `vpc_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a VPC
  stephrobert.scaleway.vpc_info:
    region: fr-par
    vpc_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List VPCs
  stephrobert.scaleway.vpc_info:
    region: fr-par
  register: result
- name: Filter Scaleway VPCs by tags
  stephrobert.scaleway.vpc_info:
    region: fr-par
    tags:
    - production
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve details of an existing VPC, specified by its VPC ID.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(vpc_id) is provided
  type: dict
  contains:
    id:
      description:
      - VPC ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the VPC.
      returned: when the API returns it
      type: str
    name:
      description:
      - VPC name.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Scaleway Organization the VPC belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the VPC belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region of the VPC.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags for the VPC.
      returned: when the API returns it
      type: list
      elements: str
    is_default:
      description:
      - Defines whether the VPC is the default one for its Project.
      returned: when the API returns it
      type: bool
    created_at:
      description:
      - Date the VPC was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the VPC was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    private_network_count:
      description:
      - Number of Private Networks within this VPC.
      returned: when the API returns it
      type: int
    routing_enabled:
      description:
      - Defines whether the VPC routes traffic between its Private Networks.
      returned: when the API returns it
      type: bool
    custom_routes_propagation_enabled:
      description:
      - Defines whether the VPC advertises custom routes between its Private Networks.
      returned: when the API returns it
      type: bool
    transitivity_enabled:
      description:
      - Defines whether the VPC allows packets from peered VPCs to transit through.
      returned: when the API returns it
      type: bool
    object_storage_private_access_enabled:
      description:
      - Defines whether the Object Storage private access is enabled for the VPC.
      returned: when the API returns it
      type: bool
vpcs:
  description:
  - List existing VPCs in the specified region.
  returned: when I(vpc_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - VPC ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the VPC.
      returned: when the API returns it
      type: str
    name:
      description:
      - VPC name.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Scaleway Organization the VPC belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the VPC belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region of the VPC.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags for the VPC.
      returned: when the API returns it
      type: list
      elements: str
    is_default:
      description:
      - Defines whether the VPC is the default one for its Project.
      returned: when the API returns it
      type: bool
    created_at:
      description:
      - Date the VPC was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the VPC was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    private_network_count:
      description:
      - Number of Private Networks within this VPC.
      returned: when the API returns it
      type: int
    routing_enabled:
      description:
      - Defines whether the VPC routes traffic between its Private Networks.
      returned: when the API returns it
      type: bool
    custom_routes_propagation_enabled:
      description:
      - Defines whether the VPC advertises custom routes between its Private Networks.
      returned: when the API returns it
      type: bool
    transitivity_enabled:
      description:
      - Defines whether the VPC allows packets from peered VPCs to transit through.
      returned: when the API returns it
      type: bool
    object_storage_private_access_enabled:
      description:
      - Defines whether the Object Storage private access is enabled for the VPC.
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
    "vpc_id": {"type": "str"},
    "is_default": {"type": "bool"},
    "name": {"type": "str"},
    "object_storage_private_access_enabled": {"type": "bool"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc", "name_asc", "name_desc"],
    },
    "routing_enabled": {"type": "bool"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetVPC",
        method="GET",
        path="/vpc/v2/regions/{region}/vpcs/{vpc_id}",
        path_params=("region", "vpc_id"),
        query_params=(),
        retry="safe",
    ),
    list_operation=Operation(
        id="ListVPCs",
        method="GET",
        path="/vpc/v2/regions/{region}/vpcs",
        path_params=("region",),
        query_params=(
            "order_by",
            "name",
            "tags",
            "organization_id",
            "project_id",
            "is_default",
            "routing_enabled",
            "object_storage_private_access_enabled",
        ),
        payload_field="vpcs",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    ),
    selector="vpc_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
