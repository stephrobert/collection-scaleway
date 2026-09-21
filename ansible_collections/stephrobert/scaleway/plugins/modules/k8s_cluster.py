#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : GetCluster, UpdateCluster
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_cluster
short_description: Manage a Scaleway Kubernetes cluster
version_added: 0.8.0
description:
- Update information on a specific Kubernetes cluster. You can update details such as its
  name, description, tags and configuration. To upgrade a cluster, you will need to use the
  dedicated endpoint.
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
  cluster_id:
    description:
    - ID of the cluster to update.
    type: str
    required: true
  admission_plugins:
    description:
    - List of admission plugins to enable.
    - 'To clear this field, write `admission_plugins: []`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: list
    elements: str
  apiserver_cert_sans:
    description:
    - Additional Subject Alternative Names for the Kubernetes API server certificate.
    - 'To clear this field, write `apiserver_cert_sans: []`; omit the option to leave the
      current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: list
    elements: str
  auto_upgrade:
    description:
    - New auto upgrade configuration for the cluster. Note that all fields needs to be set.
    type: dict
  autoscaler_config:
    description:
    - New autoscaler config for the cluster.
    type: dict
  description:
    description:
    - New description for the cluster.
    - 'To clear this field, write `description: ""`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  feature_gates:
    description:
    - List of feature gates to enable.
    - 'To clear this field, write `feature_gates: []`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: list
    elements: str
  name:
    description:
    - New external name for the cluster.
    - 'To clear this field, write `name: ""`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  open_id_connect_config:
    description:
    - OpenID Connect configuration of the cluster. This configuration enables to update the
      OpenID Connect configuration of the Kubernetes API server.
    type: dict
  tags:
    description:
    - New tags associated with the cluster.
    - 'To clear this field, write `tags: []`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: list
    elements: str
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

- name: Update a Scaleway Kubernetes cluster
  stephrobert.scaleway.k8s_cluster:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
    name: my-cluster
  register: result
- name: Preview the change on a Scaleway Kubernetes cluster without writing
  stephrobert.scaleway.k8s_cluster:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
    name: my-cluster
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
resource:
  description:
  - Retrieve information about a specific Kubernetes cluster.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Cluster ID.
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the cluster.
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
    "cluster_id": {"type": "str", "required": True},
    "admission_plugins": {"type": "list", "elements": "str"},
    "apiserver_cert_sans": {"type": "list", "elements": "str"},
    "auto_upgrade": {"type": "dict"},
    "autoscaler_config": {"type": "dict"},
    "description": {"type": "str"},
    "feature_gates": {"type": "list", "elements": "str"},
    "name": {"type": "str"},
    "open_id_connect_config": {"type": "dict"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetCluster",
        method="GET",
        path="/k8s/v1/regions/{region}/clusters/{cluster_id}",
        path_params=("region", "cluster_id"),
        query_params=(),
        retry="safe",
    ),
    update_operation=Operation(
        id="UpdateCluster",
        method="PATCH",
        path="/k8s/v1/regions/{region}/clusters/{cluster_id}",
        path_params=("region", "cluster_id"),
        query_params=(),
        body_params=(
            "name",
            "description",
            "tags",
            "autoscaler_config",
            "auto_upgrade",
            "feature_gates",
            "admission_plugins",
            "open_id_connect_config",
            "apiserver_cert_sans",
        ),
        retry="limited",
    ),
    managed_params=(
        "name",
        "description",
        "tags",
        "autoscaler_config",
        "auto_upgrade",
        "feature_gates",
        "admission_plugins",
        "open_id_connect_config",
        "apiserver_cert_sans",
    ),
    comparisons=(
        ("admission_plugins", "ordered_list"),
        ("apiserver_cert_sans", "ordered_list"),
        ("auto_upgrade", "mapping"),
        ("autoscaler_config", "mapping"),
        ("description", "scalar"),
        ("feature_gates", "ordered_list"),
        ("name", "scalar"),
        ("open_id_connect_config", "mapping"),
        ("tags", "ordered_list"),
    ),
    nullable_params=(
        "admission_plugins",
        "apiserver_cert_sans",
        "description",
        "feature_gates",
        "name",
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
