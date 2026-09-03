#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetImage, UpdateImage
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_image
short_description: Manage a Scaleway Instance image
version_added: 0.1.0
description:
- Update the properties of an image.
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
  image_id:
    description:
    - UUID of the image. (UUID format)
    type: str
    required: true
  arch:
    description:
    - Architecture of the image.
    type: str
    choices:
    - unknown_arch
    - x86_64
    - arm
    - arm64
  extra_volumes:
    description:
    - Additional snapshots of the image, with extra_volumeKey being the position of the snapshot
      in the image.
    type: dict
  name:
    description:
    - Name of the image.
    type: str
  public:
    description:
    - True to set the image as public.
    type: bool
  tags:
    description:
    - Tags of the image.
    type: list
    elements: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway instance image
  stephrobert.scaleway.instance_image:
    zone: <zone>
    image_id: <image_id>
    name: <name>
  register: result
"""

RETURN = r"""
image:
  description:
  - Get details of an image with the specified ID.
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
    "image_id": {"type": "str", "required": True},
    "arch": {
        "type": "str",
        "choices": ["unknown_arch", "x86_64", "arm", "arm64"],
    },
    "extra_volumes": {"type": "dict"},
    "name": {"type": "str"},
    "public": {"type": "bool"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetImage",
        method="GET",
        path="/instance/v1/zones/{zone}/images/{image_id}",
        path_params=("zone", "image_id"),
        query_params=(),
        payload_field="image",
    ),
    update_operation=Operation(
        id="UpdateImage",
        method="PATCH",
        path="/instance/v1/zones/{zone}/images/{image_id}",
        path_params=("zone", "image_id"),
        query_params=(),
        body_params=("name", "arch", "extra_volumes", "tags", "public"),
        payload_field="image",
    ),
    managed_params=("name", "arch", "extra_volumes", "tags", "public"),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
