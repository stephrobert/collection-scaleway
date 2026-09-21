#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetIngressRule, ListIngressRules
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_ingress_rule_info
short_description: Gather information about Scaleway VPC ingress rules
version_added: 0.9.0
description:
- Retrieve details of an existing ingress rule, specified by its ingress rule ID.
- List existing ingress rules in the specified region.
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
  rule_id:
    description:
    - ID of the ingress rule to return. (UUID format)
    type: str
  is_ipv6:
    description:
    - Whether to return only IPv4 or IPv6 ingress rules.
    type: bool
  nexthop_private_network_id:
    description:
    - Next hop Private Network ID to filter for. Only ingress rules with this Private Network
      as next hop will be returned. (UUID format)
    type: str
  nexthop_resource_ip:
    description:
    - Next hop IP to filter for. (IP address)
    type: str
  order_by:
    description:
    - Sort order of the returned ingress rules.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - source_asc
    - source_desc
    - prefix_len_asc
    - prefix_len_desc
  tags:
    description:
    - Tags to filter for. Only ingress rules with one or more matching tags will be returned.
    type: list
    elements: str
  vpc_id:
    description:
    - ID of the VPC to filter for. (UUID format)
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
# `rule_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get an ingress rule
  stephrobert.scaleway.vpc_ingress_rule_info:
    region: fr-par
    rule_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List ingress rules
  stephrobert.scaleway.vpc_ingress_rule_info:
    region: fr-par
  register: result
- name: Filter Scaleway VPC ingress rules by tags
  stephrobert.scaleway.vpc_ingress_rule_info:
    region: fr-par
    tags:
    - production
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve details of an existing ingress rule, specified by its ingress rule ID.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(rule_id) is provided
  type: dict
  contains:
    id:
      description:
      - ID of the ingress rule. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the ingress rule.
      returned: when the API returns it
      type: str
    vpc_id:
      description:
      - ID of the VPC this rule belongs to. (UUID format)
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date the ingress rule was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the ingress rule was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    is_ipv6:
      description:
      - Whether this rule applies to IPv4 or IPv6 traffic.
      returned: when the API returns it
      type: bool
    source:
      description:
      - Source network to apply this rule on. (IP network)
      returned: when the API returns it
      type: str
    nexthop_resource_ip:
      description:
      - IP of the local resource to redirect ingress traffic to. (IP address)
      returned: when the API returns it
      type: str
    nexthop_private_network_id:
      description:
      - ID of the Private Network the destination resource is in. (UUID format)
      returned: when the API returns it
      type: str
    description:
      description:
      - Description of this ingress rule.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags of this ingress rule.
      returned: when the API returns it
      type: list
      elements: str
    organization_id:
      description:
      - Scaleway Organization the ingress rule belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the ingress rule belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region of the ingress rule.
      returned: when the API returns it
      type: str
rules:
  description:
  - List existing ingress rules in the specified region.
  returned: when I(rule_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - ID of the ingress rule. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the ingress rule.
      returned: when the API returns it
      type: str
    vpc_id:
      description:
      - ID of the VPC this rule belongs to. (UUID format)
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date the ingress rule was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the ingress rule was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    is_ipv6:
      description:
      - Whether this rule applies to IPv4 or IPv6 traffic.
      returned: when the API returns it
      type: bool
    source:
      description:
      - Source network to apply this rule on. (IP network)
      returned: when the API returns it
      type: str
    nexthop_resource_ip:
      description:
      - IP of the local resource to redirect ingress traffic to. (IP address)
      returned: when the API returns it
      type: str
    nexthop_private_network_id:
      description:
      - ID of the Private Network the destination resource is in. (UUID format)
      returned: when the API returns it
      type: str
    description:
      description:
      - Description of this ingress rule.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags of this ingress rule.
      returned: when the API returns it
      type: list
      elements: str
    organization_id:
      description:
      - Scaleway Organization the ingress rule belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the ingress rule belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region of the ingress rule.
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
    "rule_id": {"type": "str"},
    "is_ipv6": {"type": "bool"},
    "nexthop_private_network_id": {"type": "str"},
    "nexthop_resource_ip": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": [
            "created_at_asc",
            "created_at_desc",
            "source_asc",
            "source_desc",
            "prefix_len_asc",
            "prefix_len_desc",
        ],
    },
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
        id="GetIngressRule",
        method="GET",
        path="/vpc/v2/regions/{region}/ingress-rules/{rule_id}",
        path_params=("region", "rule_id"),
        query_params=(),
        retry="safe",
    ),
    list_operation=Operation(
        id="ListIngressRules",
        method="GET",
        path="/vpc/v2/regions/{region}/ingress-rules",
        path_params=("region",),
        query_params=(
            "order_by",
            "vpc_id",
            "nexthop_resource_ip",
            "nexthop_private_network_id",
            "is_ipv6",
            "tags",
            "organization_id",
            "project_id",
        ),
        payload_field="rules",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    ),
    selector="rule_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
