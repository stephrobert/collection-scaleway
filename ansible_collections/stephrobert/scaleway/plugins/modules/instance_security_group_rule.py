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
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is int.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  dest_port_to:
    description:
    - End of the range of ports this rule applies to (inclusive). If 0 is provided, unset
      the parameter.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is int.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
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
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  position:
    description:
    - Position of this rule in the security group rules list.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is int.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
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
# The module reads the resource, compares, and writes only what
# differs: run it twice and the second run reports no change.
#
# Check mode compares without writing, and `--diff` shows what would
# change. A parameter you do not pass is a parameter the module does
# not touch.

- name: Update a Scaleway Instance security group rule
  stephrobert.scaleway.instance_security_group_rule:
    zone: fr-par-1
    security_group_id: 11111111-2222-3333-4444-555555555555
    security_group_rule_id: 11111111-2222-3333-4444-555555555555
    protocol: TCP
  register: result
- name: Preview the change on a Scaleway Instance security group rule without writing
  stephrobert.scaleway.instance_security_group_rule:
    zone: fr-par-1
    security_group_id: 11111111-2222-3333-4444-555555555555
    security_group_rule_id: 11111111-2222-3333-4444-555555555555
    protocol: TCP
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
rule:
  description:
  - Get details of a security group rule with the specified ID.
  returned: success
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
    "dest_port_from": {"type": "raw", "default": "__unchanged__"},
    "dest_port_to": {"type": "raw", "default": "__unchanged__"},
    "direction": {
        "type": "str",
        "choices": ["unknown_direction", "inbound", "outbound"],
    },
    "ip_range": {"type": "raw", "default": "__unchanged__"},
    "position": {"type": "raw", "default": "__unchanged__"},
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
    comparisons=(
        ("action", "scalar"),
        ("dest_port_from", "scalar"),
        ("dest_port_to", "scalar"),
        ("direction", "scalar"),
        ("ip_range", "scalar"),
        ("position", "scalar"),
        ("protocol", "scalar"),
    ),
    nullable_params=(
        ("dest_port_from", {"type": "int"}),
        ("dest_port_to", {"type": "int"}),
        ("ip_range", {"type": "str"}),
        ("position", {"type": "int"}),
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
