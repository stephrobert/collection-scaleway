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
version_added: 0.2.0
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
# The module reads the resource, compares, and writes only what
# differs: run it twice and the second run reports no change.
#
# Check mode compares without writing, and `--diff` shows what would
# change. A parameter you do not pass is a parameter the module does
# not touch.

- name: Update a Scaleway Instance volume
  stephrobert.scaleway.instance_volume:
    zone: fr-par-1
    volume_id: 11111111-2222-3333-4444-555555555555
    name: my-volume
  register: result
- name: Preview the change on a Scaleway Instance volume without writing
  stephrobert.scaleway.instance_volume:
    zone: fr-par-1
    volume_id: 11111111-2222-3333-4444-555555555555
    name: my-volume
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
volume:
  description:
  - Get details of a volume with the specified ID.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Volume unique ID.
      returned: when the API returns it
      type: str
    name:
      description:
      - Volume name.
      returned: when the API returns it
      type: str
    export_uri:
      description:
      - Show the volume NBD export URI (deprecated, will always be empty).
      returned: when the API returns it
      type: str
    size:
      description:
      - Volume disk size. (in bytes)
      returned: when the API returns it
      type: int
    volume_type:
      description:
      - Volume type.
      returned: when the API returns it
      type: str
    creation_date:
      description:
      - Volume creation date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    modification_date:
      description:
      - Volume modification date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    organization:
      description:
      - Volume Organization ID.
      returned: when the API returns it
      type: str
    project:
      description:
      - Volume Project ID.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Volume tags.
      returned: when the API returns it
      type: list
      elements: str
    server:
      description:
      - Instance attached to the volume.
      returned: when the API returns it
      type: dict
    state:
      description:
      - Volume state.
      returned: when the API returns it
      type: str
    zone:
      description:
      - Zone in which the volume is located.
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
