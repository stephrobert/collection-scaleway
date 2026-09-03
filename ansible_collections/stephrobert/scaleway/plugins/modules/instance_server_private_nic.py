#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetPrivateNIC, UpdatePrivateNIC
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_server_private_nic
short_description: Manage a Scaleway Instance server private nic
version_added: 0.1.0
description:
- Update one or more parameter(s) of a specified private NIC.
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
  server_id:
    description:
    - UUID of the Instance the private NIC will be attached to.
    type: str
    required: true
  private_nic_id:
    description:
    - Private NIC unique ID.
    type: str
    required: true
  tags:
    description:
    - Tags used to select private NIC/s.
    type: list
    elements: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway instance server private nic
  stephrobert.scaleway.instance_server_private_nic:
    zone: <zone>
    server_id: <server_id>
    private_nic_id: <private_nic_id>
    tags: <tags>
  register: result
"""

RETURN = r"""
private_nic:
  description:
  - Get private NIC properties.
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
    "server_id": {"type": "str", "required": True},
    "private_nic_id": {"type": "str", "required": True},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetPrivateNIC",
        method="GET",
        path="/instance/v1/zones/{zone}/servers/{server_id}/private_nics/{private_nic_id}",
        path_params=("zone", "server_id", "private_nic_id"),
        query_params=(),
        payload_field="private_nic",
    ),
    update_operation=Operation(
        id="UpdatePrivateNIC",
        method="PATCH",
        path="/instance/v1/zones/{zone}/servers/{server_id}/private_nics/{private_nic_id}",
        path_params=("zone", "server_id", "private_nic_id"),
        query_params=(),
        body_params=("tags",),
    ),
    managed_params=("tags",),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
