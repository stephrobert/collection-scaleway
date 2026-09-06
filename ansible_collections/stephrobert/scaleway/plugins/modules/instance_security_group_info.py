#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetSecurityGroup, ListSecurityGroups
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_security_group_info
short_description: Gather information about Scaleway Instance security groups
version_added: 0.1.0
description:
- Get the details of a security group with the specified ID.
- List all existing security groups.
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
    - UUID of the security group you want to get.
    type: str
  name:
    description:
    - Name of the security group.
    type: str
  organization:
    description:
    - Security group Organization ID.
    type: str
  project:
    description:
    - Security group Project ID.
    type: str
  project_default:
    description:
    - Filter security groups with this value for project_default.
    type: bool
  tags:
    description:
    - List security groups with these exact tags (to filter with several tags, use commas
      to separate them).
    type: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.
#
# `security_group_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a security group
  stephrobert.scaleway.instance_security_group_info:
    zone: fr-par-1
    security_group_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List security groups
  stephrobert.scaleway.instance_security_group_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
security_group:
  description:
  - Get the details of a security group with the specified ID.
  returned: when I(security_group_id) is provided
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
security_groups:
  description:
  - List all existing security groups.
  returned: when I(security_group_id) is omitted
  type: list
  elements: dict
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
    "security_group_id": {"type": "str"},
    "name": {"type": "str"},
    "organization": {"type": "str"},
    "project": {"type": "str"},
    "project_default": {"type": "bool"},
    "tags": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetSecurityGroup",
        method="GET",
        path="/instance/v1/zones/{zone}/security_groups/{security_group_id}",
        path_params=("zone", "security_group_id"),
        query_params=(),
        payload_field="security_group",
    ),
    list_operation=Operation(
        id="ListSecurityGroups",
        method="GET",
        path="/instance/v1/zones/{zone}/security_groups",
        path_params=("zone",),
        query_params=("name", "organization", "project", "tags", "project_default"),
        payload_field="security_groups",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="security_group_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
