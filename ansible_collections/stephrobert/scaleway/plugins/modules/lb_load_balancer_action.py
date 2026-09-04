#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : MigrateLb
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_load_balancer_action
short_description: Perform an action on a Scaleway Load Balancer load balancer
version_added: 0.1.0
description:
- Migrate an existing Load Balancer from one commercial type to another. Allows you to scale
  your Load Balancer up or down in terms of bandwidth or multi-cloud provision.
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
  type:
    description:
    - Load Balancer type to migrate to (use the List all Load Balancer offer types endpoint
      to get a list of available offer types).
    type: str
    required: true
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Migrate
  stephrobert.scaleway.lb_load_balancer_action:
    zone: fr-par-1
    lb_id: 11111111-2222-3333-4444-555555555555
    type: <type>
  register: result
"""

RETURN = r"""
action:
  description:
  - The operation that was triggered.
  returned: always
  type: str
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
    ActionModule,
    Operation,
    run_action_module,
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
    "type": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    operation=Operation(
        id="MigrateLb",
        method="POST",
        path="/lb/v1/zones/{zone}/lbs/{lb_id}/migrate",
        path_params=("zone", "lb_id"),
        query_params=(),
        body_params=("type",),
    ),
    action_parameter=None,
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_action_module(module, MODULE)


if __name__ == "__main__":
    main()
