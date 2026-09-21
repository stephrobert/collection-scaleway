#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetAcl
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_acl_info
short_description: Gather information about Scaleway VPC ACLs
version_added: 0.9.0
description:
- Retrieve a list of ACL rules for a VPC, specified by its VPC ID.
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
  is_ipv6:
    description:
    - Defines whether this set of ACL rules is for IPv6 (false = IPv4). Each Network ACL can
      have rules for only one IP type.
    type: bool
    required: true
  vpc_id:
    description:
    - ID of the Network ACL's VPC. (UUID format)
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

- name: Get ACL Rules for VPC
  stephrobert.scaleway.vpc_acl_info:
    region: fr-par
    is_ipv6: true
    vpc_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
rules:
  description:
  - Retrieve a list of ACL rules for a VPC, specified by its VPC ID.
  returned: success
  type: list
  elements: dict
  contains:
    protocol:
      description:
      - Protocol to which this rule applies.
      returned: when the API returns it
      type: str
    source:
      description:
      - Source IP range to which this rule applies (CIDR notation with subnet mask). (IP network)
      returned: when the API returns it
      type: str
    src_port_low:
      description:
      - Starting port of the source port range to which this rule applies (inclusive).
      returned: when the API returns it
      type: int
    src_port_high:
      description:
      - Ending port of the source port range to which this rule applies (inclusive).
      returned: when the API returns it
      type: int
    destination:
      description:
      - Destination IP range to which this rule applies (CIDR notation with subnet mask).
        (IP network)
      returned: when the API returns it
      type: str
    dst_port_low:
      description:
      - Starting port of the destination port range to which this rule applies (inclusive).
      returned: when the API returns it
      type: int
    dst_port_high:
      description:
      - Ending port of the destination port range to which this rule applies (inclusive).
      returned: when the API returns it
      type: int
    action:
      description:
      - Policy to apply to the packet.
      returned: when the API returns it
      type: str
    description:
      description:
      - Rule description.
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
    "is_ipv6": {"type": "bool", "required": True},
    "vpc_id": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    list_operation=Operation(
        id="GetAcl",
        method="GET",
        path="/vpc/v2/regions/{region}/vpcs/{vpc_id}/acl-rules",
        path_params=("region", "vpc_id"),
        query_params=("is_ipv6",),
        payload_field="rules",
        is_list=True,
        retry="safe",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
