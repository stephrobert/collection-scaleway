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
version_added: 0.2.0
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
# The module reads the resource, compares, and writes only what
# differs: run it twice and the second run reports no change.
#
# Check mode compares without writing, and `--diff` shows what would
# change. A parameter you do not pass is a parameter the module does
# not touch.

- name: Update a Scaleway Instance placement group
  stephrobert.scaleway.instance_placement_group:
    zone: fr-par-1
    placement_group_id: 11111111-2222-3333-4444-555555555555
    name: my-placement-group
  register: result
- name: Preview the change on a Scaleway Instance placement group without writing
  stephrobert.scaleway.instance_placement_group:
    zone: fr-par-1
    placement_group_id: 11111111-2222-3333-4444-555555555555
    name: my-placement-group
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
placement_group:
  description:
  - Get the specified placement group.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Placement group unique ID.
      returned: when the API returns it
      type: str
    name:
      description:
      - Placement group name.
      returned: when the API returns it
      type: str
    organization:
      description:
      - Placement group Organization ID.
      returned: when the API returns it
      type: str
    project:
      description:
      - Placement group Project ID.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Placement group tags.
      returned: when the API returns it
      type: list
      elements: str
    policy_mode:
      description:
      - Select the failure mode when the placement cannot be respected, either optional or
        enforced.
      returned: when the API returns it
      type: str
    policy_type:
      description:
      - Select the behavior of the placement group, either low_latency (group) or max_availability
        (spread).
      returned: when the API returns it
      type: str
    policy_respected:
      description:
      - 'True if the policy is respected, false otherwise.

        In the server endpoints the value is always false as it is deprecated.

        In the placement group endpoints the value is correct.'
      returned: when the API returns it
      type: bool
    zone:
      description:
      - Zone in which the placement group is located.
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
