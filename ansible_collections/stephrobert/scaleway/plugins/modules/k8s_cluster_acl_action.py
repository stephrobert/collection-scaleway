#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : AddClusterACLRules
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_cluster_acl_action
short_description: Perform an action on a Scaleway Kubernetes cluster ACL
version_added: 0.8.0
description:
- Add new ACL rules for a specific cluster.
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
  cluster_id:
    description:
    - ID of the cluster whose ACLs will be added.
    type: str
    required: true
  acls:
    description:
    - ACLs to add.
    type: list
    required: true
    elements: dict
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

- name: Acls
  stephrobert.scaleway.k8s_cluster_acl_action:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
    acls:
    - ip: 10.0.0.0/8
      description: operator network
  register: result
"""

RETURN = r"""
action:
  description:
  - The operation that was triggered.
  returned: always
  type: str
rules:
  description:
  - Add new ACL rules for a specific cluster.
  returned: when the API returns it
  type: dict
  contains:
    id:
      description:
      - ID of the ACL rule. (UUID format)
      returned: when the API returns it
      type: str
    ip:
      description:
      - IP subnet to allow. (IP network)
      returned: when the API returns it
      type: str
    scaleway_ranges:
      description:
      - 'Allow access to cluster from all Scaleway ranges as defined
        in https://www.scaleway.com/en/docs/console/account/reference-content/scaleway-network-information/#ip-ranges-used-by-scaleway.

        Only one rule with this field set to true can be added.'
      returned: when the API returns it
      type: bool
    description:
      description:
      - Description of the ACL.
      returned: when the API returns it
      type: str
    region:
      description:
      - Region of the ACL rule.
      returned: when the API returns it
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
    "cluster_id": {"type": "str", "required": True},
    "acls": {"type": "list", "required": True, "elements": "dict"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    operation=Operation(
        id="AddClusterACLRules",
        method="POST",
        path="/k8s/v1/regions/{region}/clusters/{cluster_id}/acls",
        path_params=("region", "cluster_id"),
        query_params=(),
        body_params=("acls",),
        payload_field="rules",
        is_list=True,
    ),
    action_parameter=None,
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_action_module(module, MODULE)


if __name__ == "__main__":
    main()
