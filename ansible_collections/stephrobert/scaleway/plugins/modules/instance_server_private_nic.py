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
short_description: Manage a Scaleway Instance server private NIC
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
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is list of str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
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

- name: Update a Scaleway Instance server private NIC
  stephrobert.scaleway.instance_server_private_nic:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    private_nic_id: 11111111-2222-3333-4444-555555555555
    tags:
    - production
  register: result
- name: Preview the change on a Scaleway Instance server private NIC without writing
  stephrobert.scaleway.instance_server_private_nic:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    private_nic_id: 11111111-2222-3333-4444-555555555555
    tags:
    - production
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
private_nic:
  description:
  - Get private NIC properties.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Private NIC unique ID.
      returned: when the API returns it
      type: str
    server_id:
      description:
      - Instance to which the private NIC is attached.
      returned: when the API returns it
      type: str
    private_network_id:
      description:
      - Private Network the private NIC is attached to.
      returned: when the API returns it
      type: str
    mac_address:
      description:
      - Private NIC MAC address.
      returned: when the API returns it
      type: str
    state:
      description:
      - Private NIC state.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Private NIC tags.
      returned: when the API returns it
      type: list
      elements: str
    creation_date:
      description:
      - Private NIC creation date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    zone:
      description:
      - The zone in which the Private NIC is located.
      returned: when the API returns it
      type: str
    ipam_ip_ids:
      description:
      - The list of IPAM IPs associated with this private NIC. (UUID format)
      returned: when the API returns it
      type: list
      elements: str
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
    "tags": {"type": "raw", "default": "__unchanged__"},
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
    comparisons=(
        ("tags", "ordered_list"),
    ),
    nullable_params=(
        ("tags", {"type": "list", "elements": "str"}),
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
