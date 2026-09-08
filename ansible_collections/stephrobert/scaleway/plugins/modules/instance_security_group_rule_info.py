#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetSecurityGroupRule, ListSecurityGroupRules
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_security_group_rule_info
short_description: Gather information about Scaleway Instance security group rules
version_added: 0.1.0
description:
- Get details of a security group rule with the specified ID.
- List the rules of the a specified security group ID.
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
    - fr-par-3
    - nl-ams-1
    - nl-ams-2
    - nl-ams-3
    - pl-waw-1
    - pl-waw-2
    - pl-waw-3
    - it-mil-1
  security_group_rule_id:
    description:
    - UUID of the rule. (UUID format)
    type: str
  security_group_id:
    description:
    - UUID of the security group.
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
#
# `security_group_rule_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get rule
  stephrobert.scaleway.instance_security_group_rule_info:
    zone: fr-par-1
    security_group_id: 11111111-2222-3333-4444-555555555555
    security_group_rule_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List rules
  stephrobert.scaleway.instance_security_group_rule_info:
    zone: fr-par-1
    security_group_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
rule:
  description:
  - Get details of a security group rule with the specified ID.
  returned: when I(security_group_rule_id) is provided
  type: dict
  contains:
    id:
      description:
      - Unique ID of the security group rule.
      returned: when the API returns it
      type: str
    protocol:
      description:
      - Protocol family this rule applies to.
      returned: when the API returns it
      type: str
    direction:
      description:
      - Direction the rule applies to.
      returned: when the API returns it
      type: str
    action:
      description:
      - Action to apply when the rule matches a packet.
      returned: when the API returns it
      type: str
    ip_range:
      description:
      - (IP network)
      returned: when the API returns it
      type: str
    dest_port_from:
      description:
      - Beginning of the range of ports this rule applies to (inclusive). This value will
        be set to null if protocol is ICMP or ANY.
      returned: when the API returns it
      type: int
    dest_port_to:
      description:
      - End of the range of ports this rule applies to (inclusive). This value will be set
        to null if protocol is ICMP or ANY, or if it is equal to dest_port_from.
      returned: when the API returns it
      type: int
    position:
      description:
      - Position of this rule in the security group rules list. If several rules are passed
        with the same position, the resulting order is undefined.
      returned: when the API returns it
      type: int
    editable:
      description:
      - Indicates if this rule is editable. Rules with the value false will be ignored.
      returned: when the API returns it
      type: bool
    zone:
      description:
      - The zone you want to target
      returned: when the API returns it
      type: str
rules:
  description:
  - List the rules of the a specified security group ID.
  returned: when I(security_group_rule_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - Unique ID of the security group rule.
      returned: when the API returns it
      type: str
    protocol:
      description:
      - Protocol family this rule applies to.
      returned: when the API returns it
      type: str
    direction:
      description:
      - Direction the rule applies to.
      returned: when the API returns it
      type: str
    action:
      description:
      - Action to apply when the rule matches a packet.
      returned: when the API returns it
      type: str
    ip_range:
      description:
      - (IP network)
      returned: when the API returns it
      type: str
    dest_port_from:
      description:
      - Beginning of the range of ports this rule applies to (inclusive). This value will
        be set to null if protocol is ICMP or ANY.
      returned: when the API returns it
      type: int
    dest_port_to:
      description:
      - End of the range of ports this rule applies to (inclusive). This value will be set
        to null if protocol is ICMP or ANY, or if it is equal to dest_port_from.
      returned: when the API returns it
      type: int
    position:
      description:
      - Position of this rule in the security group rules list. If several rules are passed
        with the same position, the resulting order is undefined.
      returned: when the API returns it
      type: int
    editable:
      description:
      - Indicates if this rule is editable. Rules with the value false will be ignored.
      returned: when the API returns it
      type: bool
    zone:
      description:
      - The zone you want to target
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
            "fr-par-3",
            "nl-ams-1",
            "nl-ams-2",
            "nl-ams-3",
            "pl-waw-1",
            "pl-waw-2",
            "pl-waw-3",
            "it-mil-1",
        ],
    },
    "security_group_rule_id": {"type": "str"},
    "security_group_id": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetSecurityGroupRule",
        method="GET",
        path="/instance/v1/zones/{zone}/security_groups/{security_group_id}/rules/{security_group_rule_id}",
        path_params=("zone", "security_group_id", "security_group_rule_id"),
        query_params=(),
        payload_field="rule",
    ),
    list_operation=Operation(
        id="ListSecurityGroupRules",
        method="GET",
        path="/instance/v1/zones/{zone}/security_groups/{security_group_id}/rules",
        path_params=("zone", "security_group_id"),
        query_params=(),
        payload_field="rules",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="security_group_rule_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
