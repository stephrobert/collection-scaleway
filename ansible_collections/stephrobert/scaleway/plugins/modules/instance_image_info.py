#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetImage, ListImages
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_image_info
short_description: Gather information about Scaleway Instance images
version_added: 0.1.0
description:
- Get details of an image with the specified ID.
- List all existing Instance images.
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
    - UUID of the image you want to get.
    type: str
  arch:
    description:
    - Filter images by CPU architecture.
    type: str
  name:
    description:
    - Filter images by name.
    type: str
  organization:
    description:
    - List only images of this Organization ID.
    type: str
  project:
    description:
    - List only images of this Project ID.
    type: str
  public:
    description:
    - Filter images on their public flag.
    type: bool
  tags:
    description:
    - List images with these exact tags.
    type: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.
#
# `image_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get an Instance image
  stephrobert.scaleway.instance_image_info:
    zone: fr-par-1
    image_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List Instance images
  stephrobert.scaleway.instance_image_info:
    zone: fr-par-1
  register: result
- name: Filter Scaleway Instance images by tags
  stephrobert.scaleway.instance_image_info:
    zone: fr-par-1
    tags:
    - production
  register: result
"""

RETURN = r"""
image:
  description:
  - Get details of an image with the specified ID.
  returned: when I(image_id) is provided
  type: dict
  contains:
    id:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    name:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    arch:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    creation_date:
      description:
      - (RFC 3339 format)
      returned: when the API returns it
      type: str
    modification_date:
      description:
      - (RFC 3339 format)
      returned: when the API returns it
      type: str
    default_bootscript:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    extra_volumes:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    from_server:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    organization:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    public:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: bool
    root_volume:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    state:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    project:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: list
      elements: str
    zone:
      description:
      - The zone you want to target
      returned: when the API returns it
      type: str
images:
  description:
  - List all existing Instance images.
  returned: when I(image_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    name:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    arch:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    creation_date:
      description:
      - (RFC 3339 format)
      returned: when the API returns it
      type: str
    modification_date:
      description:
      - (RFC 3339 format)
      returned: when the API returns it
      type: str
    default_bootscript:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    extra_volumes:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    from_server:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    organization:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    public:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: bool
    root_volume:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    state:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    project:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Not documented by the Scaleway API contract.
      returned: when the API returns it
      type: list
      elements: str
    zone:
      description:
      - The zone you want to target
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
    "image_id": {"type": "str"},
    "arch": {"type": "str"},
    "name": {"type": "str"},
    "organization": {"type": "str"},
    "project": {"type": "str"},
    "public": {"type": "bool"},
    "tags": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetImage",
        method="GET",
        path="/instance/v1/zones/{zone}/images/{image_id}",
        path_params=("zone", "image_id"),
        query_params=(),
        payload_field="image",
    ),
    list_operation=Operation(
        id="ListImages",
        method="GET",
        path="/instance/v1/zones/{zone}/images",
        path_params=("zone",),
        query_params=("organization", "name", "public", "arch", "project", "tags"),
        payload_field="images",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="image_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
