#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetLb, UpdateLb
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_load_balancer
short_description: Manage a Scaleway Lb load balancer
version_added: 0.1.0
description:
- Update the parameters of an existing Load Balancer, specified by its Load Balancer ID. Note
  that the request type is PUT and not PATCH. You must set all parameters.
- The module reads the resource first and writes only the fields that differ, so a second
  run reports no change.
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
    - nl-ams-1
    - nl-ams-2
    - nl-ams-3
    - pl-waw-1
    - pl-waw-2
    - pl-waw-3
  lb_id:
    description:
    - Load Balancer ID.
    type: str
    required: true
  description:
    description:
    - Load Balancer description.
    type: str
    required: true
  name:
    description:
    - Load Balancer name.
    type: str
    required: true
  ssl_compatibility_level:
    description:
    - Determines the minimal SSL version which needs to be supported on the client side, in
      an SSL/TLS offloading context. Intermediate is suitable for general-purpose servers
      with a variety of clients, recommended for almost all systems (>= TLS1.2). Modern is
      suitable for services with clients that support TLS 1.3 and do not need backward compatibility
      (= TLS1.3). Old is compatible with a small number of very old clients and should be
      used only as a last resort (>= TLS1.0).
    type: str
    choices:
    - ssl_compatibility_level_unknown
    - ssl_compatibility_level_intermediate
    - ssl_compatibility_level_modern
    - ssl_compatibility_level_old
  tags:
    description:
    - List of tags for the Load Balancer.
    type: list
    elements: str
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway lb load balancer
  stephrobert.scaleway.lb_load_balancer:
    zone: <zone>
    lb_id: <lb_id>
    description: <description>
    name: <name>
  register: result
"""

RETURN = r"""
resource:
  description:
  - Retrieve information about an existing Load Balancer, specified by its Load Balancer ID.
    Its full details, including name, status and IP address, are returned in the response
    object.
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
    ManageModule,
    Operation,
    run_manage_module,
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
            "nl-ams-1",
            "nl-ams-2",
            "nl-ams-3",
            "pl-waw-1",
            "pl-waw-2",
            "pl-waw-3",
        ],
    },
    "lb_id": {"type": "str", "required": True},
    "description": {"type": "str", "required": True},
    "name": {"type": "str", "required": True},
    "ssl_compatibility_level": {
        "type": "str",
        "choices": [
            "ssl_compatibility_level_unknown",
            "ssl_compatibility_level_intermediate",
            "ssl_compatibility_level_modern",
            "ssl_compatibility_level_old",
        ],
    },
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetLb",
        method="GET",
        path="/lb/v1/zones/{zone}/lbs/{lb_id}",
        path_params=("zone", "lb_id"),
        query_params=(),
    ),
    update_operation=Operation(
        id="UpdateLb",
        method="PUT",
        path="/lb/v1/zones/{zone}/lbs/{lb_id}",
        path_params=("zone", "lb_id"),
        query_params=(),
        body_params=("name", "description", "tags", "ssl_compatibility_level"),
    ),
    managed_params=("name", "description", "tags", "ssl_compatibility_level"),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
