#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetSnapshot, UpdateSnapshot
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_snapshot
short_description: Manage a Scaleway Instance snapshot
version_added: 0.1.0
description:
- Update the properties of a snapshot.
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
  snapshot_id:
    description:
    - UUID of the snapshot. (UUID format)
    type: str
    required: true
  name:
    description:
    - Name of the snapshot.
    type: str
  tags:
    description:
    - Tags of the snapshot.
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

- name: Update a Scaleway instance snapshot
  stephrobert.scaleway.instance_snapshot:
    zone: fr-par-1
    snapshot_id: 11111111-2222-3333-4444-555555555555
    name: my-snapshot
  register: result
"""

RETURN = r"""
snapshot:
  description:
  - Get details of a snapshot with the specified ID.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Snapshot ID.
      returned: when the API returns it
      type: str
    name:
      description:
      - Snapshot name.
      returned: when the API returns it
      type: str
    organization:
      description:
      - Snapshot Organization ID.
      returned: when the API returns it
      type: str
    project:
      description:
      - Snapshot Project ID.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Snapshot tags.
      returned: when the API returns it
      type: list
      elements: str
    volume_type:
      description:
      - Snapshot volume type.
      returned: when the API returns it
      type: str
    size:
      description:
      - Snapshot size. (in bytes)
      returned: when the API returns it
      type: int
    state:
      description:
      - Snapshot state.
      returned: when the API returns it
      type: str
    base_volume:
      description:
      - Volume on which the snapshot is based on.
      returned: when the API returns it
      type: dict
    creation_date:
      description:
      - Snapshot creation date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    modification_date:
      description:
      - Snapshot modification date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    zone:
      description:
      - Snapshot zone.
      returned: when the API returns it
      type: str
    error_reason:
      description:
      - Reason for the failed snapshot import.
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
    "snapshot_id": {"type": "str", "required": True},
    "name": {"type": "str"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetSnapshot",
        method="GET",
        path="/instance/v1/zones/{zone}/snapshots/{snapshot_id}",
        path_params=("zone", "snapshot_id"),
        query_params=(),
        payload_field="snapshot",
    ),
    update_operation=Operation(
        id="UpdateSnapshot",
        method="PATCH",
        path="/instance/v1/zones/{zone}/snapshots/{snapshot_id}",
        path_params=("zone", "snapshot_id"),
        query_params=(),
        body_params=("name", "tags"),
        payload_field="snapshot",
    ),
    managed_params=("name", "tags"),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
