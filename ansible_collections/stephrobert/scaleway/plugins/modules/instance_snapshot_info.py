#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetSnapshot, ListSnapshots
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_snapshot_info
short_description: Gather information about Scaleway Instance snapshots
version_added: 0.1.0
description:
- Get details of a snapshot with the specified ID.
- List all snapshots of an Organization in a specified Availability Zone.
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
    - UUID of the snapshot you want to get.
    type: str
  base_volume_id:
    description:
    - List snapshots originating only from this volume.
    type: str
  name:
    description:
    - List snapshots of the requested name.
    type: str
  organization:
    description:
    - List snapshots only for this Organization ID.
    type: str
  project:
    description:
    - List snapshots only for this Project ID.
    type: str
  tags:
    description:
    - List snapshots that have the requested tag.
    type: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get a snapshot
  stephrobert.scaleway.instance_snapshot_info:
    zone: fr-par-1
    snapshot_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List snapshots
  stephrobert.scaleway.instance_snapshot_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
snapshot:
  description:
  - Get details of a snapshot with the specified ID.
  returned: when I(snapshot_id) is provided
  type: dict
snapshots:
  description:
  - List all snapshots of an Organization in a specified Availability Zone.
  returned: when I(snapshot_id) is omitted
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
    "snapshot_id": {"type": "str"},
    "base_volume_id": {"type": "str"},
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
        id="GetSnapshot",
        method="GET",
        path="/instance/v1/zones/{zone}/snapshots/{snapshot_id}",
        path_params=("zone", "snapshot_id"),
        query_params=(),
        payload_field="snapshot",
    ),
    list_operation=Operation(
        id="ListSnapshots",
        method="GET",
        path="/instance/v1/zones/{zone}/snapshots",
        path_params=("zone",),
        query_params=("organization", "project", "name", "tags", "base_volume_id"),
        payload_field="snapshots",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="snapshot_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
