#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : ListServersTypes
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_server_type_info
short_description: Gather information about Scaleway Instance server types
version_added: 0.1.0
description:
- List available Instance types and their technical details.
author:
- Stéphane Robert (@stephrobert)
options:
  zone:
    description:
    - The zone you want to target
    type: str
    required: true
    choices:
    - fr-par-1
    - fr-par-2
    - fr-par-3
    - nl-ams-1
    - nl-ams-2
    - nl-ams-3
    - pl-waw-1
    - pl-waw-2
    - pl-waw-3
    - it-mil-1
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

- name: List Instance types
  stephrobert.scaleway.instance_server_type_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
servers:
  description:
  - List available Instance types and their technical details.
  returned: success
  type: dict
  version_added: 0.5.0
  contains:
    monthly_price:
      description:
      - Estimated monthly price, for a 30 days month, in Euro.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: float
    hourly_price:
      description:
      - Hourly price in Euro.
      returned: when the API returns it
      type: float
    alt_names:
      description:
      - Alternative Instance name, if any.
      returned: when the API returns it
      type: list
      elements: str
    per_volume_constraint:
      description:
      - Additional volume constraints.
      returned: when the API returns it
      type: dict
    volumes_constraint:
      description:
      - Initial volume constraints.
      returned: when the API returns it
      type: dict
    ncpus:
      description:
      - Number of CPU.
      returned: when the API returns it
      type: int
    gpu:
      description:
      - Number of GPU.
      returned: when the API returns it
      type: int
    ram:
      description:
      - Available RAM in bytes.
      returned: when the API returns it
      type: int
    gpu_info:
      description:
      - GPU information.
      returned: when the API returns it
      type: dict
    arch:
      description:
      - CPU architecture.
      returned: when the API returns it
      type: str
    network:
      description:
      - Network available for the Instance.
      returned: when the API returns it
      type: dict
    capabilities:
      description:
      - Capabilities.
      returned: when the API returns it
      type: dict
    scratch_storage_max_size:
      description:
      - Maximum available scratch storage. (in bytes)
      returned: when the API returns it
      type: int
    scratch_storage_max_volumes_count:
      description:
      - Maximum supported number of scratch volumes.
      returned: when the API returns it
      type: int
    block_bandwidth:
      description:
      - The maximum bandwidth allocated to block storage access (in bytes per second).
      returned: when the API returns it
      type: int
    end_of_service:
      description:
      - True if this Instance type has reached end of service.
      returned: when the API returns it
      type: bool
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
    "zone": {
        "type": "str",
        "required": True,
        "choices": [
            "fr-par-1",
            "fr-par-2",
            "fr-par-3",
            "nl-ams-1",
            "nl-ams-2",
            "nl-ams-3",
            "pl-waw-1",
            "pl-waw-2",
            "pl-waw-3",
            "it-mil-1",
        ],
    },
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="ListServersTypes",
        method="GET",
        path="/instance/v1/zones/{zone}/products/servers",
        path_params=("zone",),
        query_params=(),
        payload_field="servers",
        page_param="page",
        per_page_param="per_page",
        retry="safe",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
