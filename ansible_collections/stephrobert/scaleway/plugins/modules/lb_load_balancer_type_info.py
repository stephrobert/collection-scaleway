#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : ListLbTypes
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_load_balancer_type_info
short_description: Gather information about Scaleway Load Balancer types
version_added: 0.4.0
description:
- List all the different commercial Load Balancer types. The response includes an array of
  offer types, each with a name, description, and information about its stock availability.
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
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.

- name: List all Load Balancer offer types
  stephrobert.scaleway.lb_load_balancer_type_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
lb_types:
  description:
  - List all the different commercial Load Balancer types. The response includes an array
    of offer types, each with a name, description, and information about its stock availability.
  returned: success
  type: list
  elements: dict
  contains:
    name:
      description:
      - Load Balancer commercial offer type name.
      returned: when the API returns it
      type: str
    stock_status:
      description:
      - Current stock status for a given Load Balancer type.
      returned: when the API returns it
      type: str
    bandwidth:
      description:
      - Maximum bandwidth for a given Load Balancer type.
      returned: when the API returns it
      type: int
    multicloud:
      description:
      - Ability to handle backend servers outside Scaleway for a given Load Balancer type.
      returned: when the API returns it
      type: bool
    description:
      description:
      - Load Balancer commercial offer type description.
      returned: when the API returns it
      type: str
    region:
      description:
      - The region the Load Balancer stock is in.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: str
    zone:
      description:
      - The zone the Load Balancer stock is in.
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
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    list_operation=Operation(
        id="ListLbTypes",
        method="GET",
        path="/lb/v1/zones/{zone}/lb-types",
        path_params=("zone",),
        query_params=(),
        payload_field="lb_types",
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
