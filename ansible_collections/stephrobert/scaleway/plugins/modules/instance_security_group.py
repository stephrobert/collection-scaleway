#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetSecurityGroup, UpdateSecurityGroup
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_security_group
short_description: Manage a Scaleway Instance security group
version_added: 0.1.0
description:
- Update the properties of security group.
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
  description:
    description:
    - Description of the security group.
    type: str
  enable_default_security:
    description:
    - True to block SMTP on IPv4 and IPv6. This feature is read only, please open a support
      ticket if you need to make it configurable.
    type: bool
  inbound_default_policy:
    description:
    - Default inbound policy.
    type: str
    choices:
    - unknown_policy
    - accept
    - drop
  name:
    description:
    - Name of the security group.
    type: str
  organization_default:
    description:
    - Please use project_default instead.
    - Deprecated by the Scaleway API contract.
    type: bool
  outbound_default_policy:
    description:
    - Default outbound policy.
    type: str
    choices:
    - unknown_policy
    - accept
    - drop
  project_default:
    description:
    - True use this security group for future Instances created in this project.
    type: bool
  stateful:
    description:
    - True to set the security group as stateful.
    type: bool
  tags:
    description:
    - Tags of the security group.
    type: list
    elements: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway instance security group
  stephrobert.scaleway.instance_security_group:
    zone: <zone>
    security_group_id: <security_group_id>
    name: <name>
  register: result
"""

RETURN = r"""
security_group:
  description:
  - Get the details of a security group with the specified ID.
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
    "description": {"type": "str"},
    "enable_default_security": {"type": "bool"},
    "inbound_default_policy": {
        "type": "str",
        "choices": ["unknown_policy", "accept", "drop"],
    },
    "name": {"type": "str"},
    "organization_default": {"type": "bool"},
    "outbound_default_policy": {
        "type": "str",
        "choices": ["unknown_policy", "accept", "drop"],
    },
    "project_default": {"type": "bool"},
    "stateful": {"type": "bool"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetSecurityGroup",
        method="GET",
        path="/instance/v1/zones/{zone}/security_groups/{security_group_id}",
        path_params=("zone", "security_group_id"),
        query_params=(),
        payload_field="security_group",
    ),
    update_operation=Operation(
        id="UpdateSecurityGroup",
        method="PATCH",
        path="/instance/v1/zones/{zone}/security_groups/{security_group_id}",
        path_params=("zone", "security_group_id"),
        query_params=(),
        body_params=(
            "name",
            "description",
            "enable_default_security",
            "inbound_default_policy",
            "tags",
            "organization_default",
            "project_default",
            "outbound_default_policy",
            "stateful",
        ),
        payload_field="security_group",
    ),
    managed_params=(
        "name",
        "description",
        "enable_default_security",
        "inbound_default_policy",
        "tags",
        "organization_default",
        "project_default",
        "outbound_default_policy",
        "stateful",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
