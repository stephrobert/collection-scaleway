#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetIp, UpdateIp
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_ip
short_description: Manage a Scaleway Load Balancer IP
version_added: 0.3.0
description:
- Update the reverse DNS of a Load Balancer flexible IP address.
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
    required: true
  lb_id:
    description:
    - ID of the server on which to attach the flexible IP.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  reverse:
    description:
    - Reverse DNS (domain name) for the IP address.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  tags:
    description:
    - List of tags for the IP.
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

- name: Update a Scaleway Load Balancer IP
  stephrobert.scaleway.lb_ip:
    zone: fr-par-1
    ip_id: 11111111-2222-3333-4444-555555555555
    reverse: server-1.example.com
  register: result
- name: Preview the change on a Scaleway Load Balancer IP without writing
  stephrobert.scaleway.lb_ip:
    zone: fr-par-1
    ip_id: 11111111-2222-3333-4444-555555555555
    reverse: server-1.example.com
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
resource:
  description:
  - Retrieve the full details of a Load Balancer flexible IP address.
  returned: success
  type: dict
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
            "nl-ams-1",
            "nl-ams-2",
            "nl-ams-3",
            "pl-waw-1",
            "pl-waw-2",
            "pl-waw-3",
        ],
    },
    "ip_id": {"type": "str", "required": True},
    "lb_id": {"type": "raw", "default": "__unchanged__"},
    "reverse": {"type": "raw", "default": "__unchanged__"},
    "tags": {"type": "raw", "default": "__unchanged__"},
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
        path="/lb/v1/zones/{zone}/ips/{ip_id}",
        path_params=("zone", "ip_id"),
        query_params=(),
    ),
    update_operation=Operation(
        id="UpdateIp",
        method="PATCH",
        path="/lb/v1/zones/{zone}/ips/{ip_id}",
        path_params=("zone", "ip_id"),
        query_params=(),
        body_params=("reverse", "lb_id", "tags"),
    ),
    managed_params=("reverse", "lb_id", "tags"),
    comparisons=(
        ("lb_id", "scalar"),
        ("reverse", "scalar"),
        ("tags", "ordered_list"),
    ),
    nullable_params=(
        ("lb_id", {"type": "str"}),
        ("reverse", {"type": "str"}),
        ("tags", {"type": "list", "elements": "str"}),
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
