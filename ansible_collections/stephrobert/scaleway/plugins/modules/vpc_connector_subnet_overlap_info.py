#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : ListSubnetOverlaps
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_connector_subnet_overlap_info
short_description: Gather information about Scaleway VPC connector subnet overlaps
version_added: 0.9.0
description:
- List subnet overlaps between the VPCs on both sides of a connector, or for a specific subnet
  if specified.
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
  order_by:
    description:
    - Sort order of the returned Subnet overlaps.
    type: str
    choices:
    - subnet_asc
    - subnet_desc
    - target_subnet_asc
    - target_subnet_desc
  vpc_connector_id:
    description:
    - VPC Peering connector ID. (UUID format)
    type: str
    required: true
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

- name: List subnet overlaps
  stephrobert.scaleway.vpc_connector_subnet_overlap_info:
    region: fr-par
    vpc_connector_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
subnet_overlaps:
  description:
  - List subnet overlaps between the VPCs on both sides of a connector, or for a specific
    subnet if specified.
  returned: success
  type: list
  elements: dict
  contains:
    subnet_id:
      description:
      - (UUID format)
      returned: when the API returns it
      type: str
    subnet:
      description:
      - (IP network)
      returned: when the API returns it
      type: str
    target_subnet_id:
      description:
      - (UUID format)
      returned: when the API returns it
      type: str
    target_subnet:
      description:
      - (IP network)
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
    "region": {
        "type": "str",
        "required": True,
        "choices": ["fr-par", "it-mil", "nl-ams", "pl-waw"],
    },
    "order_by": {
        "type": "str",
        "choices": ["subnet_asc", "subnet_desc", "target_subnet_asc", "target_subnet_desc"],
    },
    "vpc_connector_id": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    list_operation=Operation(
        id="ListSubnetOverlaps",
        method="GET",
        path="/vpc/v2/regions/{region}/vpc-connectors/{vpc_connector_id}/subnet-overlaps",
        path_params=("region", "vpc_connector_id"),
        query_params=("order_by",),
        payload_field="subnet_overlaps",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
