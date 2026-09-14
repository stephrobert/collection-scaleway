#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : ListPools
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_cluster_pool_info
short_description: Gather information about Scaleway Kubernetes cluster pools
version_added: 0.8.0
description:
- List all the existing pools for a specific Kubernetes cluster.
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
    - ID of the cluster whose pools will be listed.
    type: str
    required: true
  name:
    description:
    - Name to filter on, only pools containing this substring in their name will be returned.
    type: str
  order_by:
    description:
    - Sort order of returned pools.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - updated_at_asc
    - updated_at_desc
    - name_asc
    - name_desc
    - status_asc
    - status_desc
    - version_asc
    - version_desc
  status:
    description:
    - Status to filter on, only pools with this status will be returned.
    type: str
    choices:
    - unknown
    - ready
    - deleting
    - deleted
    - scaling
    - warning
    - locked
    - upgrading
attributes:
  check_mode:
    description: This module only reads, so check mode changes nothing about how it runs.
    support: full
  diff_mode:
    description: This module changes nothing, so it has no difference to report.
    support: none
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.

- name: List Pools in a Cluster
  stephrobert.scaleway.k8s_cluster_pool_info:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: Filter Scaleway Kubernetes cluster pools by name
  stephrobert.scaleway.k8s_cluster_pool_info:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
    name: my-cluster-pool-info
  register: result
"""

RETURN = r"""
pools:
  description:
  - List all the existing pools for a specific Kubernetes cluster.
  returned: success
  type: list
  elements: dict
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
    InfoModule,
    Operation,
    run_info_module,
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
    "name": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": [
            "created_at_asc",
            "created_at_desc",
            "updated_at_asc",
            "updated_at_desc",
            "name_asc",
            "name_desc",
            "status_asc",
            "status_desc",
            "version_asc",
            "version_desc",
        ],
    },
    "status": {
        "type": "str",
        "choices": [
            "unknown",
            "ready",
            "deleting",
            "deleted",
            "scaling",
            "warning",
            "locked",
            "upgrading",
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
        id="ListPools",
        method="GET",
        path="/k8s/v1/regions/{region}/clusters/{cluster_id}/pools",
        path_params=("region", "cluster_id"),
        query_params=("order_by", "name", "status"),
        payload_field="pools",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
