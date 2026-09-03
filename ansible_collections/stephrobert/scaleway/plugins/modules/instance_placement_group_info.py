#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetPlacementGroup, ListPlacementGroups
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_placement_group_info
short_description: Gather information about Scaleway Instance placement groups
version_added: 0.1.0
description:
- Get the specified placement group.
- List all placement groups in a specified Availability Zone.
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
  placement_group_id:
    description:
    - UUID of the placement group you want to get.
    type: str
  name:
    description:
    - Filter placement groups by name (for eg. "cluster1" will return "cluster100" and "cluster1"
      but not "foo").
    type: str
  organization:
    description:
    - List only placement groups of this Organization ID.
    type: str
  project:
    description:
    - List only placement groups of this Project ID.
    type: str
  tags:
    description:
    - List placement groups with these exact tags (to filter with several tags, use commas
      to separate them).
    type: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get a placement group
  stephrobert.scaleway.instance_placement_group_info:
    zone: fr-par-1
    placement_group_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List placement groups
  stephrobert.scaleway.instance_placement_group_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
placement_group:
  description:
  - Get the specified placement group.
  returned: when I(placement_group_id) is provided
  type: dict
placement_groups:
  description:
  - List all placement groups in a specified Availability Zone.
  returned: when I(placement_group_id) is omitted
  type: list
  elements: dict
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
    "placement_group_id": {"type": "str"},
    "name": {"type": "str"},
    "organization": {"type": "str"},
    "project": {"type": "str"},
    "tags": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetPlacementGroup",
        method="GET",
        path="/instance/v1/zones/{zone}/placement_groups/{placement_group_id}",
        path_params=("zone", "placement_group_id"),
        query_params=(),
        payload_field="placement_group",
    ),
    list_operation=Operation(
        id="ListPlacementGroups",
        method="GET",
        path="/instance/v1/zones/{zone}/placement_groups",
        path_params=("zone",),
        query_params=("organization", "project", "tags", "name"),
        payload_field="placement_groups",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="placement_group_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
