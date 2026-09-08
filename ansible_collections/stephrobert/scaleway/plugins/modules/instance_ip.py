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
short_description: Manage a Scaleway Instance IP
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
    - 'To clear this field, write `reverse: ""`; omit the option to leave the current value
      untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  server:
    description:
    - Instance attached to the IP.
    - 'To clear this field, write `server: ""`; omit the option to leave the current value
      untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  tags:
    description:
    - An array of keywords you want to tag this IP with.
    - 'To clear this field, write `tags: []`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
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
attributes:
  check_mode:
    description: In check mode the module reads the resource and compares it, then reports
      what it would write without writing it.
    support: full
  diff_mode:
    description: The module reports the fields that differ, read through the same projection
      the comparison uses.
    support: full
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

- name: Update a Scaleway Instance IP
  stephrobert.scaleway.instance_ip:
    zone: fr-par-1
    ip: 11111111-2222-3333-4444-555555555555
    reverse: server-1.example.com
  register: result
- name: Preview the change on a Scaleway Instance IP without writing
  stephrobert.scaleway.instance_ip:
    zone: fr-par-1
    ip: 11111111-2222-3333-4444-555555555555
    reverse: server-1.example.com
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
ip:
  description:
  - Get details of an IP with the specified ID or address.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Unique ID of the IP.
      returned: when the API returns it
      type: str
    address:
      description:
      - (IP address)
      returned: when the API returns it
      type: str
    reverse:
      description:
      - Reverse domain name.
      returned: when the API returns it
      type: str
    server:
      description:
      - Instance attached to the volume.
      returned: when the API returns it
      type: dict
    organization:
      description:
      - Organization ID of the IP.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags of the IP.
      returned: when the API returns it
      type: list
      elements: str
    project:
      description:
      - Project ID of the IP.
      returned: when the API returns it
      type: str
    type:
      description:
      - Type of the IP address.
      returned: when the API returns it
      type: str
    state:
      description:
      - State of the IP.
      returned: when the API returns it
      type: str
    prefix:
      description:
      - (IP network)
      returned: when the API returns it
      type: str
    ipam_id:
      description:
      - (UUID format)
      returned: when the API returns it
      type: str
    zone:
      description:
      - The zone you want to target
      returned: when the API returns it
      type: str
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
    ManageModule,
    Operation,
    poser_les_temoins,
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
    comparisons=(
        ("reverse", "scalar"),
        ("server", "scalar"),
        ("tags", "ordered_list"),
        ("type", "scalar"),
    ),
    nullable_params=("reverse", "server", "tags"),
)

#: Ce que le contrat déclare effaçable. Ansible n'appelle un `fallback`
#: que sur une clé absente de l'invocation : le témoin note le nom sans
#: rien injecter, ce qui sépare `champ: null` de `champ` omis.
OMISSIONS = poser_les_temoins(ARGUMENT_SPEC, MODULE.nullable_params)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE, OMISSIONS)


if __name__ == "__main__":
    main()
