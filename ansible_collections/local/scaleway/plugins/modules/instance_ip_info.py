#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetIp, ListIps
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_ip_info
short_description: Gather information about Scaleway Instance ips
version_added: 0.1.0
description:
- Get details of an IP with the specified ID or address.
- List all flexible IPs in a specified zone.
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
  ip:
    description:
    - IP ID or address to get.
    type: str
  name:
    description:
    - Filter on the IP address (Works as a LIKE operation on the IP address).
    type: str
  organization:
    description:
    - Organization ID in which the IPs are reserved.
    type: str
  project:
    description:
    - Project ID in which the IPs are reserved.
    type: str
  tags:
    description:
    - Filter IPs with these exact tags (to filter with several tags, use commas to separate
      them).
    type: str
  type:
    description:
    - Filter on the IP Mobility IP type (whose value should be either 'routed_ipv4' or 'routed_ipv6').
    type: str
extends_documentation_fragment:
- local.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get a flexible IP
  local.scaleway.instance_ip_info:
    zone: fr-par-1
    ip: 11111111-2222-3333-4444-555555555555
  register: result
- name: List all flexible IPs
  local.scaleway.instance_ip_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
ip:
  description:
  - Get details of an IP with the specified ID or address.
  returned: when I(ip) is provided
  type: dict
ips:
  description:
  - List all flexible IPs in a specified zone.
  returned: when I(ip) is omitted
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
    "ip": {"type": "str"},
    "name": {"type": "str"},
    "organization": {"type": "str"},
    "project": {"type": "str"},
    "tags": {"type": "str"},
    "type": {"type": "str"},
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
        path="/instance/v1/zones/{zone}/ips/{ip}",
        path_params=("zone", "ip"),
        query_params=(),
        payload_field="ip",
    ),
    list_operation=Operation(
        id="ListIps",
        method="GET",
        path="/instance/v1/zones/{zone}/ips",
        path_params=("zone",),
        query_params=("project", "organization", "tags", "name", "type"),
        payload_field="ips",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="ip",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
