#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetIp, UpdateIp
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_ip
short_description: Manage a Scaleway Instance ip
version_added: 0.1.0
description:
- Update a flexible IP in the specified zone with the specified ID.
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
  ip:
    description:
    - IP ID or IP address.
    type: str
    required: true
  reverse:
    description:
    - Reverse domain name.
    type: str
  server:
    description:
    - Not documented by the Scaleway API contract.
    type: str
  tags:
    description:
    - An array of keywords you want to tag this IP with.
    type: list
    elements: str
  type:
    description:
    - Should have no effect.
    type: str
    choices:
    - unknown_iptype
    - routed_ipv4
    - routed_ipv6
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway instance ip
  stephrobert.scaleway.instance_ip:
    zone: <zone>
    ip: <ip>
    reverse: <reverse>
  register: result
"""

RETURN = r"""
ip:
  description:
  - Get details of an IP with the specified ID or address.
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
    "ip": {"type": "str", "required": True},
    "reverse": {"type": "str"},
    "server": {"type": "str"},
    "tags": {"type": "list", "elements": "str"},
    "type": {
        "type": "str",
        "choices": ["unknown_iptype", "routed_ipv4", "routed_ipv6"],
    },
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetIp",
        method="GET",
        path="/instance/v1/zones/{zone}/ips/{ip}",
        path_params=("zone", "ip"),
        query_params=(),
        payload_field="ip",
    ),
    update_operation=Operation(
        id="UpdateIp",
        method="PATCH",
        path="/instance/v1/zones/{zone}/ips/{ip}",
        path_params=("zone", "ip"),
        query_params=(),
        body_params=("reverse", "type", "tags", "server"),
        payload_field="ip",
    ),
    managed_params=("reverse", "type", "tags", "server"),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
