#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetSecurityGroupRule, UpdateSecurityGroupRule
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_security_group_rule
short_description: Manage a Scaleway Instance security group rule
version_added: 0.1.0
description:
- Update the properties of a rule from a specified security group.
- The module reads the resource first and writes only the fields that differ, so a second
  run reports no change.
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
  security_group_id:
    description:
    - UUID of the security group. (UUID format)
    type: str
    required: true
  security_group_rule_id:
    description:
    - UUID of the rule. (UUID format)
    type: str
    required: true
  action:
    description:
    - Action to apply when the rule matches a packet.
    type: str
    choices:
    - unknown_action
    - accept
    - drop
  dest_port_from:
    description:
    - Beginning of the range of ports this rule applies to (inclusive). If 0 is provided,
      unset the parameter.
    type: int
  dest_port_to:
    description:
    - End of the range of ports this rule applies to (inclusive). If 0 is provided, unset
      the parameter.
    type: int
  direction:
    description:
    - Direction the rule applies to.
    type: str
    choices:
    - unknown_direction
    - inbound
    - outbound
  ip_range:
    description:
    - Range of IP addresses these rules apply to. (IP network)
    type: str
  position:
    description:
    - Position of this rule in the security group rules list.
    type: int
  protocol:
    description:
    - Protocol family this rule applies to.
    type: str
    choices:
    - unknown_protocol
    - TCP
    - UDP
    - ICMP
    - ANY
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway instance security group rule
  stephrobert.scaleway.instance_security_group_rule:
    zone: <zone>
    security_group_id: <security_group_id>
    security_group_rule_id: <security_group_rule_id>
    protocol: <protocol>
  register: result
"""

RETURN = r"""
rule:
  description:
  - Get details of a security group rule with the specified ID.
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
    ManageModule,
    Operation,
    run_manage_module,
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
    "security_group_id": {"type": "str", "required": True},
    "security_group_rule_id": {"type": "str", "required": True},
    "action": {
        "type": "str",
        "choices": ["unknown_action", "accept", "drop"],
    },
    "dest_port_from": {"type": "int"},
    "dest_port_to": {"type": "int"},
    "direction": {
        "type": "str",
        "choices": ["unknown_direction", "inbound", "outbound"],
    },
    "ip_range": {"type": "str"},
    "position": {"type": "int"},
    "protocol": {
        "type": "str",
        "choices": ["unknown_protocol", "TCP", "UDP", "ICMP", "ANY"],
    },
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetSecurityGroupRule",
        method="GET",
        path="/instance/v1/zones/{zone}/security_groups/{security_group_id}/rules/{security_group_rule_id}",
        path_params=("zone", "security_group_id", "security_group_rule_id"),
        query_params=(),
        payload_field="rule",
    ),
    update_operation=Operation(
        id="UpdateSecurityGroupRule",
        method="PATCH",
        path="/instance/v1/zones/{zone}/security_groups/{security_group_id}/rules/{security_group_rule_id}",
        path_params=("zone", "security_group_id", "security_group_rule_id"),
        query_params=(),
        body_params=(
            "protocol",
            "direction",
            "action",
            "ip_range",
            "dest_port_from",
            "dest_port_to",
            "position",
        ),
        payload_field="rule",
    ),
    managed_params=(
        "protocol",
        "direction",
        "action",
        "ip_range",
        "dest_port_from",
        "dest_port_to",
        "position",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
