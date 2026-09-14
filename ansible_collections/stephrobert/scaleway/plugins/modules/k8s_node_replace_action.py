#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : ReplaceNode
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_node_replace_action
short_description: Perform an action on a Scaleway Kubernetes node replace
version_added: 0.8.0
description:
- Replace a specific Node. The node will first be drained and pods will be rescheduled onto
  another node. Note that when there is not enough space to reschedule all the pods (such
  as in a one-node cluster, or with specific constraints), disruption of your applications
  may occur.
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
    - nl-ams
    - pl-waw
    - it-mil
  node_id:
    description:
    - ID of the node to replace.
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

- name: Replace
  stephrobert.scaleway.k8s_node_replace_action:
    region: fr-par
    node_id: 11111111-2222-3333-4444-555555555555
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
        "choices": ["fr-par", "nl-ams", "pl-waw", "it-mil"],
    },
    "node_id": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    operation=Operation(
        id="ReplaceNode",
        method="POST",
        path="/k8s/v1/regions/{region}/nodes/{node_id}/replace",
        path_params=("region", "node_id"),
        query_params=(),
    ),
    action_parameter=None,
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_action_module(module, MODULE)


if __name__ == "__main__":
    main()
