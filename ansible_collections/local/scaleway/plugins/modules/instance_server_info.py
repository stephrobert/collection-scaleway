#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetServer, ListServers
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_server_info
short_description: Gather information about Scaleway Instance servers
version_added: 0.1.0
description:
- Get the details of a specified Instance.
- List all Instances in a specified Availability Zone, e.g. `fr-par-1`.
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
    - UUID of the Instance you want to get.
    type: str
  commercial_type:
    description:
    - List Instances of this commercial type.
    type: str
  name:
    description:
    - Filter Instances by name (eg. "server1" will return "server100" and "server1" but not
      "foo").
    type: str
  order:
    description:
    - Define the order of the returned servers.
    type: str
    choices:
    - creation_date_desc
    - creation_date_asc
    - modification_date_desc
    - modification_date_asc
  organization:
    description:
    - List only Instances of this Organization ID.
    type: str
  private_ip:
    description:
    - List Instances by private_ip. (IP address)
    - Deprecated by the Scaleway API contract.
    type: str
  private_network:
    description:
    - List Instances in this Private Network.
    type: str
  private_networks:
    description:
    - List Instances from the given Private Networks (use commas to separate them).
    type: str
  private_nic_mac_address:
    description:
    - List Instances associated with the given private NIC MAC address.
    type: str
  project:
    description:
    - List only Instances of this Project ID.
    type: str
  servers:
    description:
    - List Instances from these server ids (use commas to separate them).
    type: str
  state:
    description:
    - List Instances in this state.
    type: str
    choices:
    - running
    - stopped
    - stopped in place
    - starting
    - stopping
    - locked
  tags:
    description:
    - List Instances with these exact tags (to filter with several tags, use commas to separate
      them).
    type: str
  with_ip:
    description:
    - List Instances by IP (both private_ip and public_ip are supported). (IP address)
    type: str
  without_ip:
    description:
    - List Instances that are not attached to a public IP.
    type: bool
extends_documentation_fragment:
- local.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get an Instance
  local.scaleway.instance_server_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List all Instances
  local.scaleway.instance_server_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
server:
  description:
  - Get the details of a specified Instance.
  returned: when I(server_id) is provided
  type: dict
servers:
  description:
  - List all Instances in a specified Availability Zone, e.g. `fr-par-1`.
  returned: when I(server_id) is omitted
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
    "server_id": {"type": "str"},
    "commercial_type": {"type": "str"},
    "name": {"type": "str"},
    "order": {
        "type": "str",
        "choices": [
            "creation_date_desc",
            "creation_date_asc",
            "modification_date_desc",
            "modification_date_asc",
        ],
    },
    "organization": {"type": "str"},
    "private_ip": {"type": "str"},
    "private_network": {"type": "str"},
    "private_networks": {"type": "str"},
    "private_nic_mac_address": {"type": "str"},
    "project": {"type": "str"},
    "servers": {"type": "str"},
    "state": {
        "type": "str",
        "choices": ["running", "stopped", "stopped in place", "starting", "stopping", "locked"],
    },
    "tags": {"type": "str"},
    "with_ip": {"type": "str"},
    "without_ip": {"type": "bool"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetServer",
        method="GET",
        path="/instance/v1/zones/{zone}/servers/{server_id}",
        path_params=("zone", "server_id"),
        query_params=(),
        payload_field="server",
    ),
    list_operation=Operation(
        id="ListServers",
        method="GET",
        path="/instance/v1/zones/{zone}/servers",
        path_params=("zone",),
        query_params=(
            "organization",
            "project",
            "name",
            "private_ip",
            "without_ip",
            "with_ip",
            "commercial_type",
            "state",
            "tags",
            "private_network",
            "order",
            "private_networks",
            "private_nic_mac_address",
            "servers",
        ),
        payload_field="servers",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="server_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
