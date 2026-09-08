#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetVolume, ListVolumes
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_volume_info
short_description: Gather information about Scaleway Instance volumes
version_added: 0.1.0
description:
- Get details of a volume with the specified ID.
- List volumes in the specified Availability Zone. You can filter the output by volume type.
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
    - UUID of the volume you want to get.
    type: str
  name:
    description:
    - Filter volume by name (for eg. "vol" will return "myvolume" but not "data").
    type: str
  organization:
    description:
    - Filter volume by Organization ID.
    type: str
  project:
    description:
    - Filter volume by Project ID.
    type: str
  tags:
    description:
    - Filter volumes with these exact tags (to filter with several tags, use commas to separate
      them).
    type: str
  volume_type:
    description:
    - Filter by volume type.
    type: str
    choices:
    - l_ssd
    - b_ssd
    - unified
    - scratch
    - sbs_volume
    - sbs_snapshot
attributes:
  check_mode:
    description: This module only reads, so check mode changes nothing about how it runs.
    support: full
  diff_mode:
    description: This module changes nothing, so it has no difference to report.
    support: none
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.
#
# `volume_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a volume
  stephrobert.scaleway.instance_volume_info:
    zone: fr-par-1
    volume_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List volumes
  stephrobert.scaleway.instance_volume_info:
    zone: fr-par-1
  register: result
- name: Filter Scaleway Instance volumes by tags
  stephrobert.scaleway.instance_volume_info:
    zone: fr-par-1
    tags:
    - production
  register: result
"""

RETURN = r"""
volume:
  description:
  - Get details of a volume with the specified ID.
  returned: when I(volume_id) is provided
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
      - Deprecated by the Scaleway API contract.
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
volumes:
  description:
  - List volumes in the specified Availability Zone. You can filter the output by volume type.
  returned: when I(volume_id) is omitted
  type: list
  elements: dict
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
      - Deprecated by the Scaleway API contract.
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
    "volume_id": {"type": "str"},
    "name": {"type": "str"},
    "organization": {"type": "str"},
    "project": {"type": "str"},
    "tags": {"type": "str"},
    "volume_type": {
        "type": "str",
        "choices": ["l_ssd", "b_ssd", "unified", "scratch", "sbs_volume", "sbs_snapshot"],
    },
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetVolume",
        method="GET",
        path="/instance/v1/zones/{zone}/volumes/{volume_id}",
        path_params=("zone", "volume_id"),
        query_params=(),
        payload_field="volume",
        retry="safe",
    ),
    list_operation=Operation(
        id="ListVolumes",
        method="GET",
        path="/instance/v1/zones/{zone}/volumes",
        path_params=("zone",),
        query_params=("volume_type", "organization", "project", "tags", "name"),
        payload_field="volumes",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
        retry="safe",
    ),
    selector="volume_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
