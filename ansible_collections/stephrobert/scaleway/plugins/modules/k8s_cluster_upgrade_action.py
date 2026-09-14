#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : UpgradeCluster
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_cluster_upgrade_action
short_description: Perform an action on a Scaleway Kubernetes cluster upgrade
version_added: 0.8.0
description:
- Upgrade a specific Kubernetes cluster and possibly its associated pools to a specific and
  supported Kubernetes version.
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
    - ID of the cluster to upgrade.
    type: str
    required: true
  upgrade_pools:
    description:
    - Defines whether pools will also be upgraded once the control plane is upgraded.
    type: bool
  version:
    description:
    - New Kubernetes version of the cluster. Note that the version should either be a higher
      patch version of the same minor version or the direct minor version after the current
      one.
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

- name: Upgrade
  stephrobert.scaleway.k8s_cluster_upgrade_action:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
    version: '{{ k8s_target_version }}'
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
    "cluster_id": {"type": "str", "required": True},
    "upgrade_pools": {"type": "bool"},
    "version": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    operation=Operation(
        id="UpgradeCluster",
        method="POST",
        path="/k8s/v1/regions/{region}/clusters/{cluster_id}/upgrade",
        path_params=("region", "cluster_id"),
        query_params=(),
        body_params=("version", "upgrade_pools"),
    ),
    action_parameter=None,
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_action_module(module, MODULE)


if __name__ == "__main__":
    main()
