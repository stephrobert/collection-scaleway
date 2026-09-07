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
version_added: 0.3.0
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
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  enable_default_security:
    description:
    - True to block SMTP on IPv4 and IPv6. This feature is read only, please open a support
      ticket if you need to make it configurable.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is bool.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
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
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  organization_default:
    description:
    - Please use project_default instead.
    - Deprecated by the Scaleway API contract.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is bool.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
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
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is bool.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  stateful:
    description:
    - True to set the security group as stateful.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is bool.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  tags:
    description:
    - Tags of the security group.
    type: list
    elements: str
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

- name: Update a Scaleway Instance security group
  stephrobert.scaleway.instance_security_group:
    zone: fr-par-1
    security_group_id: 11111111-2222-3333-4444-555555555555
    name: my-security-group
  register: result
- name: Preview the change on a Scaleway Instance security group without writing
  stephrobert.scaleway.instance_security_group:
    zone: fr-par-1
    security_group_id: 11111111-2222-3333-4444-555555555555
    name: my-security-group
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
security_group:
  description:
  - Get the details of a security group with the specified ID.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Security group unique ID.
      returned: when the API returns it
      type: str
    name:
      description:
      - Security group name.
      returned: when the API returns it
      type: str
    description:
      description:
      - Security group description.
      returned: when the API returns it
      type: str
    enable_default_security:
      description:
      - True if SMTP is blocked on IPv4 and IPv6. This feature is read only, please open a
        support ticket if you need to make it configurable.
      returned: when the API returns it
      type: bool
    inbound_default_policy:
      description:
      - Default inbound policy.
      returned: when the API returns it
      type: str
    outbound_default_policy:
      description:
      - Default outbound policy.
      returned: when the API returns it
      type: str
    organization:
      description:
      - Security group Organization ID.
      returned: when the API returns it
      type: str
    project:
      description:
      - Security group Project ID.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Security group tags.
      returned: when the API returns it
      type: list
      elements: str
    organization_default:
      description:
      - True if it is your default security group for this Organization ID.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: bool
    project_default:
      description:
      - True if it is your default security group for this Project ID.
      returned: when the API returns it
      type: bool
    creation_date:
      description:
      - Security group creation date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    modification_date:
      description:
      - Security group modification date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    servers:
      description:
      - List of Instances attached to this security group.
      returned: when the API returns it
      type: list
      elements: dict
    stateful:
      description:
      - Defines whether the security group is stateful.
      returned: when the API returns it
      type: bool
    state:
      description:
      - 'The state of the security group. Set to `syncing` (until the changes.

        Are applied) when the security group is updated (e.g., rules added, modified, or deleted)

        or when it is attached to or detached from a server''s public network interface.'
      returned: when the API returns it
      type: str
    zone:
      description:
      - Zone in which the security group is located.
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
    "description": {"type": "raw", "default": "__unchanged__"},
    "enable_default_security": {"type": "raw", "default": "__unchanged__"},
    "inbound_default_policy": {
        "type": "str",
        "choices": ["unknown_policy", "accept", "drop"],
    },
    "name": {"type": "raw", "default": "__unchanged__"},
    "organization_default": {"type": "raw", "default": "__unchanged__"},
    "outbound_default_policy": {
        "type": "str",
        "choices": ["unknown_policy", "accept", "drop"],
    },
    "project_default": {"type": "raw", "default": "__unchanged__"},
    "stateful": {"type": "raw", "default": "__unchanged__"},
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
    comparisons=(
        ("description", "scalar"),
        ("enable_default_security", "scalar"),
        ("inbound_default_policy", "scalar"),
        ("name", "scalar"),
        ("organization_default", "scalar"),
        ("outbound_default_policy", "scalar"),
        ("project_default", "scalar"),
        ("stateful", "scalar"),
        ("tags", "ordered_list"),
    ),
    nullable_params=(
        ("description", {"type": "str"}),
        ("enable_default_security", {"type": "bool"}),
        ("name", {"type": "str"}),
        ("organization_default", {"type": "bool"}),
        ("project_default", {"type": "bool"}),
        ("stateful", {"type": "bool"}),
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
