#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : ListClusterTypes
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_cluster_type_info
short_description: Gather information about Scaleway Kubernetes cluster types
version_added: 0.8.0
description:
- List available cluster types and their technical details.
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

- name: List cluster types
  stephrobert.scaleway.k8s_cluster_type_info:
    region: fr-par
  register: result
"""

RETURN = r"""
cluster_types:
  description:
  - List available cluster types and their technical details.
  returned: success
  type: list
  elements: dict
  contains:
    name:
      description:
      - Cluster type name.
      returned: when the API returns it
      type: str
    availability:
      description:
      - Cluster type availability.
      returned: when the API returns it
      type: str
    max_nodes:
      description:
      - Maximum number of nodes supported by the offer.
      returned: when the API returns it
      type: int
    commitment_delay:
      description:
      - Time period during which you can no longer switch to a lower offer. (in seconds)
      returned: when the API returns it
      type: str
    sla:
      description:
      - Value of the Service Level Agreement of the offer.
      returned: when the API returns it
      type: float
    resiliency:
      description:
      - Resiliency offered by the offer.
      returned: when the API returns it
      type: str
    memory:
      description:
      - Max RAM allowed for the control plane. (in bytes)
      returned: when the API returns it
      type: int
    dedicated:
      description:
      - Returns information if this offer uses dedicated resources.
      returned: when the API returns it
      type: bool
    audit_logs_supported:
      description:
      - True if the offer allows activation of the audit log functionality. Please note that
        audit logs are sent to Cockpit.
      returned: when the API returns it
      type: bool
    region:
      description:
      - The region of the cluster type.
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
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    list_operation=Operation(
        id="ListClusterTypes",
        method="GET",
        path="/k8s/v1/regions/{region}/cluster-types",
        path_params=("region",),
        query_params=(),
        payload_field="cluster_types",
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
