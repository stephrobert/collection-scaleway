#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetVolume, UpdateVolume
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_volume
short_description: Manage a Scaleway Instance volume
version_added: 0.1.0
description:
- Replace the name and/or size properties of a volume specified by its ID, with the specified
  value(s).
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
  volume_id:
    description:
    - UUID of the volume.
    type: str
    required: true
  name:
    description:
    - Volume name.
    type: str
  size:
    description:
    - Volume disk size, must be a multiple of 512. (in bytes)
    type: int
  tags:
    description:
    - Tags of the volume.
    type: list
    elements: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway instance volume
  stephrobert.scaleway.instance_volume:
    zone: <zone>
    volume_id: <volume_id>
    name: <name>
  register: result
"""

RETURN = r"""
volume:
  description:
  - Get details of a volume with the specified ID.
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
    "volume_id": {"type": "str", "required": True},
    "name": {"type": "str"},
    "size": {"type": "int"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetVolume",
        method="GET",
        path="/instance/v1/zones/{zone}/volumes/{volume_id}",
        path_params=("zone", "volume_id"),
        query_params=(),
        payload_field="volume",
    ),
    update_operation=Operation(
        id="UpdateVolume",
        method="PATCH",
        path="/instance/v1/zones/{zone}/volumes/{volume_id}",
        path_params=("zone", "volume_id"),
        query_params=(),
        body_params=("name", "tags", "size"),
        payload_field="volume",
    ),
    managed_params=("name", "tags", "size"),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
