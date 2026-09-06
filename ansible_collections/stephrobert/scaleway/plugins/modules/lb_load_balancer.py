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
short_description: Manage a Scaleway Load Balancer
version_added: 0.2.0
description:
- Update the parameters of an existing Load Balancer, specified by its Load Balancer ID.
- 'The module reads the resource first and writes the whole body, because this operation replaces
  the resource: fields you do not set keep the value the API returns. A second run reports
  no change.'
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
# The module reads the resource, compares, and writes only what
# differs: run it twice and the second run reports no change.
#
# Check mode compares without writing, and `--diff` shows what would
# change. A parameter you do not pass is a parameter the module does
# not touch.

- name: Update a Scaleway Load Balancer
  stephrobert.scaleway.lb_load_balancer:
    zone: fr-par-1
    lb_id: 11111111-2222-3333-4444-555555555555
    description: Managed by Ansible
    name: my-load-balancer
  register: result
- name: Preview the change on a Scaleway Load Balancer without writing
  stephrobert.scaleway.lb_load_balancer:
    zone: fr-par-1
    lb_id: 11111111-2222-3333-4444-555555555555
    description: Managed by Ansible
    name: my-load-balancer
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
resource:
  description:
  - Retrieve information about an existing Load Balancer, specified by its Load Balancer ID.
    Its full details, including name, status and IP address, are returned in the response
    object.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Underlying Instance ID.
      returned: when the API returns it
      type: str
    name:
      description:
      - Load Balancer name.
      returned: when the API returns it
      type: str
    description:
      description:
      - Load Balancer description.
      returned: when the API returns it
      type: str
    status:
      description:
      - Load Balancer status.
      returned: when the API returns it
      type: str
    instances:
      description:
      - List of underlying Instances.
      returned: when the API returns it
      type: list
      elements: dict
    organization_id:
      description:
      - Scaleway Organization ID.
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project ID.
      returned: when the API returns it
      type: str
    ip:
      description:
      - List of IP addresses attached to the Load Balancer.
      returned: when the API returns it
      type: list
      elements: dict
    tags:
      description:
      - Load Balancer tags.
      returned: when the API returns it
      type: list
      elements: str
    frontend_count:
      description:
      - Number of frontends the Load Balancer has.
      returned: when the API returns it
      type: int
    backend_count:
      description:
      - Number of backends the Load Balancer has.
      returned: when the API returns it
      type: int
    type:
      description:
      - Load Balancer offer type.
      returned: when the API returns it
      type: str
    subscriber:
      description:
      - Subscriber information.
      returned: when the API returns it
      type: dict
    ssl_compatibility_level:
      description:
      - Determines the minimal SSL version which needs to be supported on client side.
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date on which the Load Balancer was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the Load Balancer was last updated. (RFC 3339 format)
      returned: when the API returns it
      type: str
    private_network_count:
      description:
      - Number of Private Networks attached to the Load Balancer.
      returned: when the API returns it
      type: int
    route_count:
      description:
      - Number of routes configured on the Load Balancer.
      returned: when the API returns it
      type: int
    region:
      description:
      - The region the Load Balancer is in.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: str
    zone:
      description:
      - The zone the Load Balancer is in.
      returned: when the API returns it
      type: str
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
