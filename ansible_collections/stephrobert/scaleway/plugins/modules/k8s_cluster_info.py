#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : GetCluster, ListClusters
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_cluster_info
short_description: Gather information about Scaleway Kubernetes clusters
version_added: 0.8.0
description:
- Retrieve information about a specific Kubernetes cluster.
- List all existing Kubernetes clusters in a specific region.
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
    - ID of the requested cluster.
    type: str
  name:
    description:
    - Name to filter on, only clusters containing this substring in their name will be returned.
    type: str
  order_by:
    description:
    - Sort order of returned clusters.
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
  private_network_id:
    description:
    - Private Network ID to filter on, only clusters within this Private Network will be returned.
    type: str
  status:
    description:
    - Status to filter on, only clusters with this status will be returned.
    type: str
    choices:
    - unknown
    - creating
    - ready
    - deleting
    - deleted
    - updating
    - locked
    - pool_required
  type:
    description:
    - Type to filter on, only clusters with this type will be returned.
    type: str
  version:
    description:
    - Version to filter on, only cluster matching this prefix version will be returned.
    type: str
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
#
# `cluster_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a Cluster
  stephrobert.scaleway.k8s_cluster_info:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List Clusters
  stephrobert.scaleway.k8s_cluster_info:
    region: fr-par
  register: result
- name: Filter Scaleway Kubernetes clusters by name
  stephrobert.scaleway.k8s_cluster_info:
    region: fr-par
    name: my-cluster-info
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve information about a specific Kubernetes cluster.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(cluster_id) is provided
  type: dict
  contains:
    id:
      description:
      - Cluster ID.
      returned: when the API returns it
      type: str
    type:
      description:
      - Cluster type.
      returned: when the API returns it
      type: str
    name:
      description:
      - Cluster name.
      returned: when the API returns it
      type: str
    status:
      description:
      - Status of the cluster.
      returned: when the API returns it
      type: str
    version:
      description:
      - Kubernetes version of the cluster.
      returned: when the API returns it
      type: str
    region:
      description:
      - Region in which the cluster is deployed.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - ID of the Organization owning the cluster.
      returned: when the API returns it
      type: str
    project_id:
      description:
      - ID of the Project owning the cluster.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags associated with the cluster.
      returned: when the API returns it
      type: list
      elements: str
    cni:
      description:
      - Container Network Interface (CNI) plugin running in the cluster.
      returned: when the API returns it
      type: str
    description:
      description:
      - Cluster description.
      returned: when the API returns it
      type: str
    cluster_url:
      description:
      - Kubernetes API server URL of the cluster.
      returned: when the API returns it
      type: str
    dns_wildcard:
      description:
      - Wildcard DNS resolving all the ready cluster nodes.
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date on which the cluster was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the cluster was last updated. (RFC 3339 format)
      returned: when the API returns it
      type: str
    autoscaler_config:
      description:
      - Autoscaler configuration for the cluster, see https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/FAQ.md
        for details.
      returned: when the API returns it
      type: dict
    auto_upgrade:
      description:
      - Auto upgrade Kubernetes version of the cluster.
      returned: when the API returns it
      type: dict
    upgrade_available:
      description:
      - Defines whether a new Kubernetes version is available.
      returned: when the API returns it
      type: bool
    feature_gates:
      description:
      - List of enabled feature gates.
      returned: when the API returns it
      type: list
      elements: str
    admission_plugins:
      description:
      - List of enabled admission plugins.
      returned: when the API returns it
      type: list
      elements: str
    open_id_connect_config:
      description:
      - This configuration enables to update the OpenID Connect configuration of the Kubernetes
        API server.
      returned: when the API returns it
      type: dict
    apiserver_cert_sans:
      description:
      - Additional Subject Alternative Names for the Kubernetes API server certificate.
      returned: when the API returns it
      type: list
      elements: str
    private_network_id:
      description:
      - Private network ID for internal cluster communication.
      returned: when the API returns it
      type: str
    commitment_ends_at:
      description:
      - Date on which it will be possible to switch to a smaller offer. (RFC 3339 format)
      returned: when the API returns it
      type: str
    acl_available:
      description:
      - Defines whether ACL is available on the cluster.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: bool
    iam_nodes_group_id:
      description:
      - IAM group that nodes are members of (this field might be empty during early stage
        of cluster creation).
      returned: when the API returns it
      type: str
    pod_cidr:
      description:
      - Subnet used for the Pod CIDR. (IP network)
      returned: when the API returns it
      type: str
    service_cidr:
      description:
      - Subnet used for the Service CIDR. (IP network)
      returned: when the API returns it
      type: str
    service_dns_ip:
      description:
      - IP used for the DNS Service. (IPv4 address)
      returned: when the API returns it
      type: str
clusters:
  description:
  - List all existing Kubernetes clusters in a specific region.
  returned: when I(cluster_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - Cluster ID.
      returned: when the API returns it
      type: str
    type:
      description:
      - Cluster type.
      returned: when the API returns it
      type: str
    name:
      description:
      - Cluster name.
      returned: when the API returns it
      type: str
    status:
      description:
      - Status of the cluster.
      returned: when the API returns it
      type: str
    version:
      description:
      - Kubernetes version of the cluster.
      returned: when the API returns it
      type: str
    region:
      description:
      - Region in which the cluster is deployed.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - ID of the Organization owning the cluster.
      returned: when the API returns it
      type: str
    project_id:
      description:
      - ID of the Project owning the cluster.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags associated with the cluster.
      returned: when the API returns it
      type: list
      elements: str
    cni:
      description:
      - Container Network Interface (CNI) plugin running in the cluster.
      returned: when the API returns it
      type: str
    description:
      description:
      - Cluster description.
      returned: when the API returns it
      type: str
    cluster_url:
      description:
      - Kubernetes API server URL of the cluster.
      returned: when the API returns it
      type: str
    dns_wildcard:
      description:
      - Wildcard DNS resolving all the ready cluster nodes.
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date on which the cluster was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the cluster was last updated. (RFC 3339 format)
      returned: when the API returns it
      type: str
    autoscaler_config:
      description:
      - Autoscaler configuration for the cluster, see https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/FAQ.md
        for details.
      returned: when the API returns it
      type: dict
    auto_upgrade:
      description:
      - Auto upgrade Kubernetes version of the cluster.
      returned: when the API returns it
      type: dict
    upgrade_available:
      description:
      - Defines whether a new Kubernetes version is available.
      returned: when the API returns it
      type: bool
    feature_gates:
      description:
      - List of enabled feature gates.
      returned: when the API returns it
      type: list
      elements: str
    admission_plugins:
      description:
      - List of enabled admission plugins.
      returned: when the API returns it
      type: list
      elements: str
    open_id_connect_config:
      description:
      - This configuration enables to update the OpenID Connect configuration of the Kubernetes
        API server.
      returned: when the API returns it
      type: dict
    apiserver_cert_sans:
      description:
      - Additional Subject Alternative Names for the Kubernetes API server certificate.
      returned: when the API returns it
      type: list
      elements: str
    private_network_id:
      description:
      - Private network ID for internal cluster communication.
      returned: when the API returns it
      type: str
    commitment_ends_at:
      description:
      - Date on which it will be possible to switch to a smaller offer. (RFC 3339 format)
      returned: when the API returns it
      type: str
    acl_available:
      description:
      - Defines whether ACL is available on the cluster.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: bool
    iam_nodes_group_id:
      description:
      - IAM group that nodes are members of (this field might be empty during early stage
        of cluster creation).
      returned: when the API returns it
      type: str
    pod_cidr:
      description:
      - Subnet used for the Pod CIDR. (IP network)
      returned: when the API returns it
      type: str
    service_cidr:
      description:
      - Subnet used for the Service CIDR. (IP network)
      returned: when the API returns it
      type: str
    service_dns_ip:
      description:
      - IP used for the DNS Service. (IPv4 address)
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
    "cluster_id": {"type": "str"},
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
    "private_network_id": {"type": "str"},
    "status": {
        "type": "str",
        "choices": [
            "unknown",
            "creating",
            "ready",
            "deleting",
            "deleted",
            "updating",
            "locked",
            "pool_required",
        ],
    },
    "type": {"type": "str"},
    "version": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetCluster",
        method="GET",
        path="/k8s/v1/regions/{region}/clusters/{cluster_id}",
        path_params=("region", "cluster_id"),
        query_params=(),
        retry="safe",
    ),
    list_operation=Operation(
        id="ListClusters",
        method="GET",
        path="/k8s/v1/regions/{region}/clusters",
        path_params=("region",),
        query_params=(
            "organization_id",
            "project_id",
            "order_by",
            "name",
            "status",
            "type",
            "private_network_id",
            "version",
        ),
        payload_field="clusters",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    ),
    selector="cluster_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
