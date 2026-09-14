#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : ListNodes
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_cluster_node_info
short_description: Gather information about Scaleway Kubernetes cluster nodes
version_added: 0.8.0
description:
- List all the existing nodes for a specific Kubernetes cluster.
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
    - Cluster ID from which the nodes will be listed from.
    type: str
    required: true
  name:
    description:
    - Name to filter on, only nodes containing this substring in their name will be returned.
    type: str
  order_by:
    description:
    - Sort order of the returned nodes.
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
  pool_id:
    description:
    - Pool ID on which to filter the returned nodes.
    type: str
  status:
    description:
    - Status to filter on, only nodes with this status will be returned.
    type: str
    choices:
    - unknown
    - creating
    - not_ready
    - ready
    - deleting
    - deleted
    - locked
    - rebooting
    - creation_error
    - upgrading
    - starting
    - registering
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

- name: List Nodes in a Cluster
  stephrobert.scaleway.k8s_cluster_node_info:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: Filter Scaleway Kubernetes cluster nodes by name
  stephrobert.scaleway.k8s_cluster_node_info:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
    name: my-cluster-node-info
  register: result
"""

RETURN = r"""
nodes:
  description:
  - List all the existing nodes for a specific Kubernetes cluster.
  returned: success
  type: list
  elements: dict
  contains:
    id:
      description:
      - Node ID.
      returned: when the API returns it
      type: str
    pool_id:
      description:
      - Pool ID of the node.
      returned: when the API returns it
      type: str
    cluster_id:
      description:
      - Cluster ID of the node.
      returned: when the API returns it
      type: str
    provider_id:
      description:
      - Underlying instance ID. It is prefixed by instance type and location information (see
        https://pkg.go.dev/k8s.io/api/core/v1#NodeSpec.ProviderID).
      returned: when the API returns it
      type: str
    region:
      description:
      - Cluster region of the node.
      returned: when the API returns it
      type: str
    name:
      description:
      - Name of the node.
      returned: when the API returns it
      type: str
    status:
      description:
      - Status of the node.
      returned: when the API returns it
      type: str
    error_message:
      description:
      - Details of the error, if any occurred when managing the node.
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date on which the node was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the node was last updated. (RFC 3339 format)
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
    "pool_id": {"type": "str"},
    "status": {
        "type": "str",
        "choices": [
            "unknown",
            "creating",
            "not_ready",
            "ready",
            "deleting",
            "deleted",
            "locked",
            "rebooting",
            "creation_error",
            "upgrading",
            "starting",
            "registering",
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
        id="ListNodes",
        method="GET",
        path="/k8s/v1/regions/{region}/clusters/{cluster_id}/nodes",
        path_params=("region", "cluster_id"),
        query_params=("pool_id", "order_by", "name", "status"),
        payload_field="nodes",
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
