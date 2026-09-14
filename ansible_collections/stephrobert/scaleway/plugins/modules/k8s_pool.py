#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : GetPool, UpdatePool
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_pool
short_description: Manage a Scaleway Kubernetes pool
version_added: 0.8.0
description:
- Update the attributes of a specific pool, such as its desired size, autoscaling settings,
  and tags. To upgrade a pool, you will need to use the dedicated endpoint.
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
    - nl-ams
    - pl-waw
    - it-mil
  pool_id:
    description:
    - ID of the pool to update.
    type: str
    required: true
  autohealing:
    description:
    - New value for the pool autohealing enablement.
    - 'The contract marks this field clearable, but bool has no empty value, so the API cannot
      clear it. Setting it to null is refused: this API reads null as "field not provided"
      and would change nothing.'
    type: bool
  autoscaling:
    description:
    - New value for the pool autoscaling enablement.
    - 'The contract marks this field clearable, but bool has no empty value, so the API cannot
      clear it. Setting it to null is refused: this API reads null as "field not provided"
      and would change nothing.'
    type: bool
  kubelet_args:
    description:
    - New Kubelet arguments to be used by this pool. Note that this feature is experimental.
    - 'To clear this field, write `kubelet_args: {}`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: dict
  max_size:
    description:
    - New maximum size for the pool.
    - 'The contract marks this field clearable, but int has no empty value, so the API cannot
      clear it. Setting it to null is refused: this API reads null as "field not provided"
      and would change nothing.'
    type: int
  max_termination_grace_period:
    description:
    - New maximum amount of time before the API forces the drain and deletion of a `deleting`
      node. (in seconds)
    - 'To clear this field, write `max_termination_grace_period: ""`; omit the option to leave
      the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  min_size:
    description:
    - New minimum size for the pool.
    - 'The contract marks this field clearable, but int has no empty value, so the API cannot
      clear it. Setting it to null is refused: this API reads null as "field not provided"
      and would change nothing.'
    type: int
  security_group_id:
    description:
    - Security group ID in which all the nodes of the pool will be moved.
    - 'To clear this field, write `security_group_id: ""`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  size:
    description:
    - New desired pool size.
    - 'The contract marks this field clearable, but int has no empty value, so the API cannot
      clear it. Setting it to null is refused: this API reads null as "field not provided"
      and would change nothing.'
    type: int
  tags:
    description:
    - New tags associated with the pool.
    - 'To clear this field, write `tags: []`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: list
    elements: str
  upgrade_policy:
    description:
    - New upgrade policy for the pool.
    type: dict
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

- name: Update a Scaleway Kubernetes pool
  stephrobert.scaleway.k8s_pool:
    region: fr-par
    pool_id: 11111111-2222-3333-4444-555555555555
    autoscaling: true
  register: result
- name: Preview the change on a Scaleway Kubernetes pool without writing
  stephrobert.scaleway.k8s_pool:
    region: fr-par
    pool_id: 11111111-2222-3333-4444-555555555555
    autoscaling: true
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
resource:
  description:
  - Retrieve details about a specific pool in a Kubernetes cluster.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Pool ID. (UUID format)
      returned: when the API returns it
      type: str
    cluster_id:
      description:
      - Cluster ID of the pool. (UUID format)
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date on which the pool was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the pool was last updated. (RFC 3339 format)
      returned: when the API returns it
      type: str
    name:
      description:
      - Pool name.
      returned: when the API returns it
      type: str
    status:
      description:
      - Pool status.
      returned: when the API returns it
      type: str
    version:
      description:
      - Pool version.
      returned: when the API returns it
      type: str
    node_type:
      description:
      - Node type is the type of Scaleway Instance wanted for the pool. Nodes with insufficient
        memory are not eligible (DEV1-S, PLAY2-PICO, STARDUST). 'external' is a special node
        type used to provision instances from other cloud providers in a Kosmos Cluster.
      returned: when the API returns it
      type: str
    autoscaling:
      description:
      - Defines whether the autoscaling feature is enabled for the pool.
      returned: when the API returns it
      type: bool
    size:
      description:
      - Size (number of nodes) of the pool.
      returned: when the API returns it
      type: int
    min_size:
      description:
      - Defines the minimum size of the pool. Note that this field is only used when autoscaling
        is enabled on the pool.
      returned: when the API returns it
      type: int
    max_size:
      description:
      - Defines the maximum size of the pool. Note that this field is only used when autoscaling
        is enabled on the pool.
      returned: when the API returns it
      type: int
    container_runtime:
      description:
      - Customization of the container runtime is available for each pool.
      returned: when the API returns it
      type: str
    autohealing:
      description:
      - Defines whether the autohealing feature is enabled for the pool.
      returned: when the API returns it
      type: bool
    tags:
      description:
      - Tags associated with the pool, see L(managing tags,https://www.scaleway.com/en/docs/kubernetes/api-cli/managing-tags).
      returned: when the API returns it
      type: list
      elements: str
    placement_group_id:
      description:
      - Placement group ID in which all the nodes of the pool will be created, placement groups
        are limited to 20 instances. (UUID format)
      returned: when the API returns it
      type: str
    kubelet_args:
      description:
      - Kubelet arguments to be used by this pool. Note that this feature is experimental.
      returned: when the API returns it
      type: dict
    upgrade_policy:
      description:
      - Defines how node provisioning should behave during pool version upgrade.
      returned: when the API returns it
      type: dict
    zone:
      description:
      - Zone in which the pool's nodes will be spawned.
      returned: when the API returns it
      type: str
    root_volume_type:
      description:
      - 'Defines the system volume disk type. Several types of volume (`volume_type`) are
        provided:.

        * `l_ssd` is a local block storage which means your system is stored locally on your
        node''s hypervisor. This type is not available for all node types

        * `sbs_5k` is a remote block storage which means your system is stored on a centralized
        and resilient cluster with 5k IOPS limits

        * `sbs_15k` is a faster remote block storage which means your system is stored on
        a centralized and resilient cluster with 15k IOPS limits

        * `b_ssd` is the legacy remote block storage which means your system is stored on
        a centralized and resilient cluster. Not available for new pools, use `sbs_5k` or
        `sbs_15k` instead.'
      returned: when the API returns it
      type: str
    root_volume_size:
      description:
      - System volume disk size. (in bytes)
      returned: when the API returns it
      type: int
    public_ip_disabled:
      description:
      - Defines if the public IP should be removed from Nodes. To use this feature, your Cluster
        must have an attached Private Network set up with a Public Gateway.
      returned: when the API returns it
      type: bool
    security_group_id:
      description:
      - Security group ID in which all the nodes of the pool will be created. If unset, the
        pool will use default Kapsule security group in current zone. (UUID format)
      returned: when the API returns it
      type: str
    labels:
      description:
      - Kubernetes labels applied and reconciled on the nodes.
      returned: when the API returns it
      type: dict
    taints:
      description:
      - Kubernetes taints applied and reconciled on the nodes.
      returned: when the API returns it
      type: list
      elements: dict
    startup_taints:
      description:
      - Kubernetes taints applied at node creation but not reconciled afterwards.
      returned: when the API returns it
      type: list
      elements: dict
    error_message:
      description:
      - Details of the error, if any occurred when managing the pool.
      returned: when the API returns it
      type: str
    max_termination_grace_period:
      description:
      - Maximum amount of time before the API forces the drain and deletion of a `deleting`
        node. It overrides pods `PodDisruptionBudget` and `terminationGracePeriodSeconds`.
        Defaults to 15 minutes, up to 1 hour. (in seconds)
      returned: when the API returns it
      type: str
    region:
      description:
      - Cluster region of the pool.
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
        "choices": ["fr-par", "nl-ams", "pl-waw", "it-mil"],
    },
    "pool_id": {"type": "str", "required": True},
    "autohealing": {"type": "bool"},
    "autoscaling": {"type": "bool"},
    "kubelet_args": {"type": "dict"},
    "max_size": {"type": "int"},
    "max_termination_grace_period": {"type": "str"},
    "min_size": {"type": "int"},
    "security_group_id": {"type": "str"},
    "size": {"type": "int"},
    "tags": {"type": "list", "elements": "str"},
    "upgrade_policy": {"type": "dict"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetPool",
        method="GET",
        path="/k8s/v1/regions/{region}/pools/{pool_id}",
        path_params=("region", "pool_id"),
        query_params=(),
        retry="safe",
    ),
    update_operation=Operation(
        id="UpdatePool",
        method="PATCH",
        path="/k8s/v1/regions/{region}/pools/{pool_id}",
        path_params=("region", "pool_id"),
        query_params=(),
        body_params=(
            "autoscaling",
            "size",
            "min_size",
            "max_size",
            "autohealing",
            "tags",
            "kubelet_args",
            "upgrade_policy",
            "security_group_id",
            "max_termination_grace_period",
        ),
        retry="limited",
    ),
    managed_params=(
        "autoscaling",
        "size",
        "min_size",
        "max_size",
        "autohealing",
        "tags",
        "kubelet_args",
        "upgrade_policy",
        "security_group_id",
        "max_termination_grace_period",
    ),
    comparisons=(
        ("autohealing", "scalar"),
        ("autoscaling", "scalar"),
        ("kubelet_args", "mapping"),
        ("max_size", "scalar"),
        ("max_termination_grace_period", "scalar"),
        ("min_size", "scalar"),
        ("security_group_id", "scalar"),
        ("size", "scalar"),
        ("tags", "ordered_list"),
        ("upgrade_policy", "mapping"),
    ),
    nullable_params=(
        "autohealing",
        "autoscaling",
        "kubelet_args",
        "max_size",
        "max_termination_grace_period",
        "min_size",
        "security_group_id",
        "size",
        "tags",
    ),
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
