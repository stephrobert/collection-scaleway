#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetDashboard
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_dashboard_info
short_description: Gather information about Scaleway Instance dashboards
version_added: 0.3.0
description:
- 'Return the Instance dashboard of one zone: the resource counts the API keeps for an Organization
  or a Project, such as `servers_count`, `running_servers_count`, `volumes_count`, `images_count`,
  `snapshots_count`, `ips_count`, `ips_unused` and `security_groups_count`.'
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
  organization:
    description:
    - Organization ID whose dashboard is returned.
    type: str
  project:
    description:
    - Project ID whose dashboard is returned.
    type: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.

- name: Read a Scaleway Instance dashboard
  stephrobert.scaleway.instance_dashboard_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
dashboard:
  description:
  - 'Return the Instance dashboard of one zone: the resource counts the API keeps for an Organization
    or a Project, such as `servers_count`, `running_servers_count`, `volumes_count`, `images_count`,
    `snapshots_count`, `ips_count`, `ips_unused` and `security_groups_count`.'
  returned: success
  type: dict
  contains:
    volumes_count:
      description:
      - Count of volumes.
      returned: when the API returns it
      type: int
    running_servers_count:
      description:
      - Count of running servers.
      returned: when the API returns it
      type: int
    servers_by_types:
      description:
      - Count of servers per type.
      returned: when the API returns it
      type: dict
    images_count:
      description:
      - Count of images.
      returned: when the API returns it
      type: int
    snapshots_count:
      description:
      - Count of snapshots.
      returned: when the API returns it
      type: int
    servers_count:
      description:
      - Count of servers.
      returned: when the API returns it
      type: int
    ips_count:
      description:
      - Count of IPs.
      returned: when the API returns it
      type: int
    security_groups_count:
      description:
      - Count of security groups.
      returned: when the API returns it
      type: int
    ips_unused:
      description:
      - Count of unused IP addresses.
      returned: when the API returns it
      type: int
    volumes_l_ssd_count:
      description:
      - Count of volumes l ssd.
      returned: when the API returns it
      type: int
    volumes_l_ssd_total_size:
      description:
      - (in bytes)
      returned: when the API returns it
      type: int
    private_nics_count:
      description:
      - Count of private NICs.
      returned: when the API returns it
      type: int
    placement_groups_count:
      description:
      - Count of placement groups.
      returned: when the API returns it
      type: int
    volumes_scratch_count:
      description:
      - Count of volumes scratch.
      returned: when the API returns it
      type: int
    volumes_b_ssd_count:
      description:
      - Count of volumes b ssd.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: int
    volumes_b_ssd_total_size:
      description:
      - (in bytes)
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: int
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
    "organization": {"type": "str"},
    "project": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetDashboard",
        method="GET",
        path="/instance/v1/zones/{zone}/dashboard",
        path_params=("zone",),
        query_params=("organization", "project"),
        payload_field="dashboard",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
