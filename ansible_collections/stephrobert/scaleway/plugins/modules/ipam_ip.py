#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/ipam.v1.yml
# Opérations : GetIP, UpdateIP
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: ipam_ip
short_description: Manage a Scaleway IPAM IP
version_added: 0.9.0
description:
- Update parameters including tags of the specified IP.
- The module reads the resource first and writes only the fields that differ, so a second
  run reports no change.
author:
- Stéphane Robert (@stephrobert)
options:
  region:
    description:
    - The region you want to target
    type: str
    required: true
    choices:
    - fr-par
    - it-mil
    - nl-ams
    - pl-waw
  ip_id:
    description:
    - IP ID. (UUID format)
    type: str
    required: true
  reverses:
    description:
    - Array of reverse domain names associated with an IP in the subnet of the current IP.
    type: list
    elements: dict
  tags:
    description:
    - Tags for the IP.
    - 'To clear this field, write `tags: []`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: list
    elements: str
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

- name: Update a Scaleway IPAM IP
  stephrobert.scaleway.ipam_ip:
    region: fr-par
    ip_id: 11111111-2222-3333-4444-555555555555
    tags:
    - production
  register: result
- name: Preview the change on a Scaleway IPAM IP without writing
  stephrobert.scaleway.ipam_ip:
    region: fr-par
    ip_id: 11111111-2222-3333-4444-555555555555
    tags:
    - production
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
resource:
  description:
  - Retrieve details of an existing IP, specified by its IP ID.
  returned: success
  type: dict
  contains:
    id:
      description:
      - IP ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the IP.
      returned: when the API returns it
      type: str
    address:
      description:
      - IPv4 or IPv6 address in CIDR notation. (IP network)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the IP belongs to. (UUID format)
      returned: when the API returns it
      type: str
    is_ipv6:
      description:
      - Defines whether the IP is an IPv6 (false = IPv4).
      returned: when the API returns it
      type: bool
    created_at:
      description:
      - Date the IP was reserved. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the IP was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    source:
      description:
      - Source pool where the IP was reserved in.
      returned: when the API returns it
      type: dict
    resource:
      description:
      - Resource which the IP is attached to.
      returned: when the API returns it
      type: dict
    tags:
      description:
      - Tags for the IP.
      returned: when the API returns it
      type: list
      elements: str
    reverses:
      description:
      - Array of reverses associated with the IP.
      returned: when the API returns it
      type: list
      elements: dict
    region:
      description:
      - Region of the IP.
      returned: when the API returns it
      type: str
    zone:
      description:
      - Zone of the IP, if zonal.
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
    "region": {
        "type": "str",
        "required": True,
        "choices": ["fr-par", "it-mil", "nl-ams", "pl-waw"],
    },
    "ip_id": {"type": "str", "required": True},
    "reverses": {"type": "list", "elements": "dict"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetIP",
        method="GET",
        path="/ipam/v1/regions/{region}/ips/{ip_id}",
        path_params=("region", "ip_id"),
        query_params=(),
        retry="safe",
    ),
    update_operation=Operation(
        id="UpdateIP",
        method="PATCH",
        path="/ipam/v1/regions/{region}/ips/{ip_id}",
        path_params=("region", "ip_id"),
        query_params=(),
        body_params=("tags", "reverses"),
        retry="limited",
    ),
    managed_params=("tags", "reverses"),
    comparisons=(
        ("reverses", "id_list"),
        ("tags", "ordered_list"),
    ),
    nullable_params=("tags",),
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
