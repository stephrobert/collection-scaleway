#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : ListSubnets
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_subnet_info
short_description: Gather information about Scaleway VPC subnets
version_added: 0.9.0
description:
- List any Private Network's subnets. See ListPrivateNetworks to list a specific Private Network's
  subnets.
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
    - Sort order of the returned subnets.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
  subnet_ids:
    description:
    - Subnet IDs to filter for. Only subnets matching the specified IDs will be returned.
    type: list
    elements: str
  vpc_id:
    description:
    - VPC ID to filter for. Only subnets belonging to this VPC will be returned. (UUID format)
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

- name: List subnets
  stephrobert.scaleway.vpc_subnet_info:
    region: fr-par
  register: result
- name: Filter Scaleway VPC subnets by subnet_ids
  stephrobert.scaleway.vpc_subnet_info:
    region: fr-par
    subnet_ids: []
  register: result
"""

RETURN = r"""
subnets:
  description:
  - List any Private Network's subnets. See ListPrivateNetworks to list a specific Private
    Network's subnets.
  returned: success
  type: list
  elements: dict
  contains:
    id:
      description:
      - ID of the subnet. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the subnet.
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Subnet creation date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Subnet last modification date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    subnet:
      description:
      - Subnet CIDR. (IP network)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the subnet belongs to. (UUID format)
      returned: when the API returns it
      type: str
    private_network_id:
      description:
      - Private Network the subnet belongs to. (UUID format)
      returned: when the API returns it
      type: str
    vpc_id:
      description:
      - VPC the subnet belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region in which the Subnet can be used.
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
        "choices": ["created_at_asc", "created_at_desc"],
    },
    "subnet_ids": {"type": "list", "elements": "str"},
    "vpc_id": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    list_operation=Operation(
        id="ListSubnets",
        method="GET",
        path="/vpc/v2/regions/{region}/subnets",
        path_params=("region",),
        query_params=("order_by", "organization_id", "project_id", "subnet_ids", "vpc_id"),
        payload_field="subnets",
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
