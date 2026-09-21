#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : EnableDHCP
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_private_network_enable_dhcp_action
short_description: Perform an action on a Scaleway VPC private network
version_added: 0.9.0
description:
- Enable DHCP managed on an existing Private Network. Note that you will not be able to deactivate
  it afterwards.
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
  private_network_id:
    description:
    - Private Network ID. (UUID format)
    type: str
    required: true
attributes:
  check_mode:
    description: In check mode the module reports the action it would trigger and sends nothing,
      without even building an API client.
    support: full
  diff_mode:
    description: An action is a trigger rather than a state, so there is no before and after
      to compare.
    support: none
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# An action is a trigger, not a state: running this a second time
# reports `changed` again, and that is correct. Idempotence is the
# business of the management modules.

- name: Enable dhcp
  stephrobert.scaleway.vpc_private_network_enable_dhcp_action:
    region: fr-par
    private_network_id: 11111111-2222-3333-4444-555555555555
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
    "region": {
        "type": "str",
        "required": True,
        "choices": ["fr-par", "it-mil", "nl-ams", "pl-waw"],
    },
    "private_network_id": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    operation=Operation(
        id="EnableDHCP",
        method="POST",
        path="/vpc/v2/regions/{region}/private-networks/{private_network_id}/enable-dhcp",
        path_params=("region", "private_network_id"),
        query_params=(),
    ),
    action_parameter=None,
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_action_module(module, MODULE)


if __name__ == "__main__":
    main()
