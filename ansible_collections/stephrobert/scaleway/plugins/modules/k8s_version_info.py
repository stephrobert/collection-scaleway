#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/k8s.v1.yml
# Opérations : GetVersion, ListVersions
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: k8s_version_info
short_description: Gather information about Scaleway Kubernetes versions
version_added: 0.8.0
description:
- Retrieve a specific Kubernetes version and its details.
- List all available versions for the creation of a new Kubernetes cluster.
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
  version_name:
    description:
    - Requested version name.
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
# `version_name` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a Version
  stephrobert.scaleway.k8s_version_info:
    region: fr-par
    version_name: 11111111-2222-3333-4444-555555555555
  register: result
- name: List all available Versions
  stephrobert.scaleway.k8s_version_info:
    region: fr-par
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve a specific Kubernetes version and its details.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(version_name) is provided
  type: dict
  contains:
    name:
      description:
      - Name of the Kubernetes version.
      returned: when the API returns it
      type: str
    label:
      description:
      - Label of the Kubernetes version.
      returned: when the API returns it
      type: str
    region:
      description:
      - Region in which this version is available.
      returned: when the API returns it
      type: str
    available_cnis:
      description:
      - Supported Container Network Interface (CNI) plugins for this version.
      returned: when the API returns it
      type: list
      elements: str
    available_container_runtimes:
      description:
      - Supported container runtimes for this version.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: list
      elements: str
    available_feature_gates:
      description:
      - Supported feature gates for this version.
      returned: when the API returns it
      type: list
      elements: str
    available_admission_plugins:
      description:
      - Supported admission plugins for this version.
      returned: when the API returns it
      type: list
      elements: str
    available_kubelet_args:
      description:
      - Supported kubelet arguments for this version.
      returned: when the API returns it
      type: dict
    deprecated_at:
      description:
      - Date from which this version will no longer be available for provisioning. (RFC 3339
        format)
      returned: when the API returns it
      type: str
    end_of_life_at:
      description:
      - Date from which any remaining clusters on this version will begin to be forcibly upgraded
        to the next minor version. (RFC 3339 format)
      returned: when the API returns it
      type: str
    released_at:
      description:
      - Date at which this version was made available by Kapsule product. (RFC 3339 format)
      returned: when the API returns it
      type: str
    additional_components:
      description:
      - Map containing every sub-component version shipped with this Kapsule version.
      returned: when the API returns it
      type: dict
versions:
  description:
  - List all available versions for the creation of a new Kubernetes cluster.
  returned: when I(version_name) is omitted
  type: list
  elements: dict
  contains:
    name:
      description:
      - Name of the Kubernetes version.
      returned: when the API returns it
      type: str
    label:
      description:
      - Label of the Kubernetes version.
      returned: when the API returns it
      type: str
    region:
      description:
      - Region in which this version is available.
      returned: when the API returns it
      type: str
    available_cnis:
      description:
      - Supported Container Network Interface (CNI) plugins for this version.
      returned: when the API returns it
      type: list
      elements: str
    available_container_runtimes:
      description:
      - Supported container runtimes for this version.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: list
      elements: str
    available_feature_gates:
      description:
      - Supported feature gates for this version.
      returned: when the API returns it
      type: list
      elements: str
    available_admission_plugins:
      description:
      - Supported admission plugins for this version.
      returned: when the API returns it
      type: list
      elements: str
    available_kubelet_args:
      description:
      - Supported kubelet arguments for this version.
      returned: when the API returns it
      type: dict
    deprecated_at:
      description:
      - Date from which this version will no longer be available for provisioning. (RFC 3339
        format)
      returned: when the API returns it
      type: str
    end_of_life_at:
      description:
      - Date from which any remaining clusters on this version will begin to be forcibly upgraded
        to the next minor version. (RFC 3339 format)
      returned: when the API returns it
      type: str
    released_at:
      description:
      - Date at which this version was made available by Kapsule product. (RFC 3339 format)
      returned: when the API returns it
      type: str
    additional_components:
      description:
      - Map containing every sub-component version shipped with this Kapsule version.
      returned: when the API returns it
      type: dict
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
    "version_name": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetVersion",
        method="GET",
        path="/k8s/v1/regions/{region}/versions/{version_name}",
        path_params=("region", "version_name"),
        query_params=(),
        retry="safe",
    ),
    list_operation=Operation(
        id="ListVersions",
        method="GET",
        path="/k8s/v1/regions/{region}/versions",
        path_params=("region",),
        query_params=(),
        payload_field="versions",
        is_list=True,
        retry="safe",
    ),
    selector="version_name",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
