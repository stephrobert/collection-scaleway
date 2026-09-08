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
short_description: Gather information about Scaleway Instance server private NICs
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
# `private_nic_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a private NIC
  stephrobert.scaleway.instance_server_private_nic_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    private_nic_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List all private NICs
  stephrobert.scaleway.instance_server_private_nic_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: Filter Scaleway Instance server private NICs by tags
  stephrobert.scaleway.instance_server_private_nic_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    tags:
    - production
  register: result
"""

RETURN = r"""
private_nic:
  description:
  - Get private NIC properties.
  returned: when I(private_nic_id) is provided
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
private_nics:
  description:
  - 'List all private NICs of a specified Instance.

    Some private NICs, such as those in deleting, detaching, or in error state are

    not listed. We strongly recommend migrating to v2alpha1 to retrieve all private NICs.'
  returned: when I(private_nic_id) is omitted
  type: list
  elements: dict
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
