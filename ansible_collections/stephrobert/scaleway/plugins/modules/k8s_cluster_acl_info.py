#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : ListClusterACLRules
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_cluster_acl_info
short_description: Gather information about Scaleway Kubernetes cluster ACLs
version_added: 0.8.0
description:
- List ACLs for a specific cluster.
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
    - ID of the cluster whose ACLs will be listed.
    type: str
    required: true
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

- name: List ACLs
  stephrobert.scaleway.k8s_cluster_acl_info:
    region: fr-par
    cluster_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
rules:
  description:
  - List ACLs for a specific cluster.
  returned: success
  type: list
  elements: dict
  contains:
    id:
      description:
      - ID of the ACL rule. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the ACL rule.
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
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    list_operation=Operation(
        id="ListClusterACLRules",
        method="GET",
        path="/k8s/v1/regions/{region}/clusters/{cluster_id}/acls",
        path_params=("region", "cluster_id"),
        query_params=(),
        payload_field="rules",
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
