#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : ListLbPrivateNetworks
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_load_balancer_private_network_info
short_description: Gather information about Scaleway Load Balancer private networks
version_added: 0.2.0
description:
- List the Private Networks attached to a given Load Balancer, specified by its Load Balancer
  ID. The response is an array of Private Network objects, giving information including the
  status, configuration, name and creation date of each Private Network.
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
    - nl-ams-1
    - nl-ams-2
    - nl-ams-3
    - pl-waw-1
    - pl-waw-2
    - pl-waw-3
  lb_id:
    description:
    - Load Balancer ID.
    type: str
    required: true
  order_by:
    description:
    - Sort order of Private Network objects in the response.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.

- name: List Private Networks attached to a Load Balancer
  stephrobert.scaleway.lb_load_balancer_private_network_info:
    zone: fr-par-1
    lb_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
private_network:
  description:
  - List the Private Networks attached to a given Load Balancer, specified by its Load Balancer
    ID. The response is an array of Private Network objects, giving information including
    the status, configuration, name and creation date of each Private Network.
  returned: success
  type: list
  elements: dict
  contains:
    lb:
      description:
      - Load Balancer object which is attached to the Private Network.
      returned: when the API returns it
      type: dict
    ipam_ids:
      description:
      - IPAM IDs of the booked IP addresses. (UUID format)
      returned: when the API returns it
      type: list
      elements: str
    static_config:
      description:
      - Object containing an array of a local IP address for the Load Balancer on this Private
        Network.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    dhcp_config:
      description:
      - Object containing DHCP-assigned IP addresses.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    private_network_id:
      description:
      - Private Network ID.
      returned: when the API returns it
      type: str
    status:
      description:
      - Status of Private Network connection.
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date on which the Private Network was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the PN was last updated. (RFC 3339 format)
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
            "nl-ams-1",
            "nl-ams-2",
            "nl-ams-3",
            "pl-waw-1",
            "pl-waw-2",
            "pl-waw-3",
        ],
    },
    "lb_id": {"type": "str", "required": True},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc"],
    },
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    list_operation=Operation(
        id="ListLbPrivateNetworks",
        method="GET",
        path="/lb/v1/zones/{zone}/lbs/{lb_id}/private-networks",
        path_params=("zone", "lb_id"),
        query_params=("order_by",),
        payload_field="private_network",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
