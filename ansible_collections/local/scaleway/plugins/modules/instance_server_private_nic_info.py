#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetPrivateNIC, ListPrivateNICs
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_server_private_nic_info
short_description: Gather information about Scaleway Instance server private nics
version_added: 0.1.0
description:
- Get private NIC properties.
- 'List all private NICs of a specified Instance.

  Some private NICs, such as those in deleting, detaching, or in error state are

  not listed. We strongly recommend migrating to v2alpha1 to retrieve all private NICs.'
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
  private_nic_id:
    description:
    - Private NIC unique ID.
    type: str
  server_id:
    description:
    - Instance to which the private NIC is attached.
    type: str
    required: true
  tags:
    description:
    - Private NIC tags.
    type: str
extends_documentation_fragment:
- local.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get a private NIC
  local.scaleway.instance_server_private_nic_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    private_nic_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List all private NICs
  local.scaleway.instance_server_private_nic_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
private_nic:
  description:
  - Get private NIC properties.
  returned: when I(private_nic_id) is provided
  type: dict
private_nics:
  description:
  - 'List all private NICs of a specified Instance.

    Some private NICs, such as those in deleting, detaching, or in error state are

    not listed. We strongly recommend migrating to v2alpha1 to retrieve all private NICs.'
  returned: when I(private_nic_id) is omitted
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.local.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
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
    "private_nic_id": {"type": "str"},
    "server_id": {"type": "str", "required": True},
    "tags": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetPrivateNIC",
        method="GET",
        path="/instance/v1/zones/{zone}/servers/{server_id}/private_nics/{private_nic_id}",
        path_params=("zone", "server_id", "private_nic_id"),
        query_params=(),
        payload_field="private_nic",
    ),
    list_operation=Operation(
        id="ListPrivateNICs",
        method="GET",
        path="/instance/v1/zones/{zone}/servers/{server_id}/private_nics",
        path_params=("zone", "server_id"),
        query_params=("tags",),
        payload_field="private_nics",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="private_nic_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
