#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetIp, ListIPs
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_ip_info
short_description: Gather information about Scaleway Load Balancer IPs
version_added: 0.1.0
description:
- Retrieve the full details of a Load Balancer flexible IP address.
- List the Load Balancer flexible IP addresses held in the account (filtered by Organization
  ID or Project ID). It is also possible to search for a specific IP address.
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
  ip_id:
    description:
    - IP address ID.
    type: str
  ip_address:
    description:
    - IP address to filter for.
    type: str
  ip_type:
    description:
    - IP type to filter for.
    type: str
    choices:
    - all
    - ipv4
    - ipv6
  tags:
    description:
    - Tag to filter for, only IPs with one or more matching tags will be returned.
    type: list
    elements: str
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
# `ip_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get an IP address
  stephrobert.scaleway.lb_ip_info:
    zone: fr-par-1
    ip_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List IP addresses
  stephrobert.scaleway.lb_ip_info:
    zone: fr-par-1
  register: result
- name: Filter Scaleway Load Balancer IPs by tags
  stephrobert.scaleway.lb_ip_info:
    zone: fr-par-1
    tags:
    - production
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve the full details of a Load Balancer flexible IP address.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(ip_id) is provided
  type: dict
  version_added: 0.4.0
  contains:
    id:
      description:
      - IP address ID.
      returned: when the API returns it
      type: str
    ip_address:
      description:
      - IP address.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Organization ID of the Scaleway Organization the IP address is in.
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Project ID of the Scaleway Project the IP address is in.
      returned: when the API returns it
      type: str
    lb_id:
      description:
      - Load Balancer ID.
      returned: when the API returns it
      type: str
    reverse:
      description:
      - Reverse DNS (domain name) of the IP address.
      returned: when the API returns it
      type: str
    tags:
      description:
      - IP tags.
      returned: when the API returns it
      type: list
      elements: str
    region:
      description:
      - The region the IP address is in.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: str
    zone:
      description:
      - The zone the IP address is in.
      returned: when the API returns it
      type: str
ips:
  description:
  - List the Load Balancer flexible IP addresses held in the account (filtered by Organization
    ID or Project ID). It is also possible to search for a specific IP address.
  returned: when I(ip_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - IP address ID.
      returned: when the API returns it
      type: str
    ip_address:
      description:
      - IP address.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Organization ID of the Scaleway Organization the IP address is in.
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Project ID of the Scaleway Project the IP address is in.
      returned: when the API returns it
      type: str
    lb_id:
      description:
      - Load Balancer ID.
      returned: when the API returns it
      type: str
    reverse:
      description:
      - Reverse DNS (domain name) of the IP address.
      returned: when the API returns it
      type: str
    tags:
      description:
      - IP tags.
      returned: when the API returns it
      type: list
      elements: str
    region:
      description:
      - The region the IP address is in.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: str
    zone:
      description:
      - The zone the IP address is in.
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
    "ip_id": {"type": "str"},
    "ip_address": {"type": "str"},
    "ip_type": {
        "type": "str",
        "choices": ["all", "ipv4", "ipv6"],
    },
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetIp",
        method="GET",
        path="/lb/v1/zones/{zone}/ips/{ip_id}",
        path_params=("zone", "ip_id"),
        query_params=(),
        retry="safe",
    ),
    list_operation=Operation(
        id="ListIPs",
        method="GET",
        path="/lb/v1/zones/{zone}/ips",
        path_params=("zone",),
        query_params=("ip_address", "organization_id", "project_id", "ip_type", "tags"),
        payload_field="ips",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    ),
    selector="ip_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
