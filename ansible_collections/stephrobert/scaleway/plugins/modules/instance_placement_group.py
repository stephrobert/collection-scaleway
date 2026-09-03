#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetPlacementGroup, UpdatePlacementGroup
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_placement_group
short_description: Manage a Scaleway Instance placement group
version_added: 0.1.0
description:
- Update one or more parameter of the specified placement group.
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
  placement_group_id:
    description:
    - UUID of the placement group.
    type: str
    required: true
  name:
    description:
    - Name of the placement group.
    type: str
  policy_mode:
    description:
    - Operating mode of the placement group.
    type: str
    choices:
    - optional
    - enforced
  policy_type:
    description:
    - Policy type of the placement group.
    type: str
    choices:
    - max_availability
    - low_latency
  tags:
    description:
    - Tags of the placement group.
    type: list
    elements: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway instance placement group
  stephrobert.scaleway.instance_placement_group:
    zone: <zone>
    placement_group_id: <placement_group_id>
    name: <name>
  register: result
"""

RETURN = r"""
placement_group:
  description:
  - Get the specified placement group.
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
    "placement_group_id": {"type": "str", "required": True},
    "name": {"type": "str"},
    "policy_mode": {
        "type": "str",
        "choices": ["optional", "enforced"],
    },
    "policy_type": {
        "type": "str",
        "choices": ["max_availability", "low_latency"],
    },
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetPlacementGroup",
        method="GET",
        path="/instance/v1/zones/{zone}/placement_groups/{placement_group_id}",
        path_params=("zone", "placement_group_id"),
        query_params=(),
        payload_field="placement_group",
    ),
    update_operation=Operation(
        id="UpdatePlacementGroup",
        method="PATCH",
        path="/instance/v1/zones/{zone}/placement_groups/{placement_group_id}",
        path_params=("zone", "placement_group_id"),
        query_params=(),
        body_params=("name", "tags", "policy_mode", "policy_type"),
        payload_field="placement_group",
    ),
    managed_params=("name", "tags", "policy_mode", "policy_type"),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
