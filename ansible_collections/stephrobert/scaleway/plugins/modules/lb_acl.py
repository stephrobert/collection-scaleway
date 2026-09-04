#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetAcl, UpdateAcl
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_acl
short_description: Manage a Scaleway Lb acl
version_added: 0.1.0
description:
- Update a particular ACL, specified by its ACL ID. You can update details including its name,
  action and match rule.
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
  acl_id:
    description:
    - ACL ID.
    type: str
    required: true
  action:
    description:
    - Action to take when incoming traffic matches an ACL filter.
    type: dict
    required: true
  description:
    description:
    - ACL description.
    type: str
  index:
    description:
    - Priority of this ACL (ACLs are applied in ascending order, 0 is the first ACL executed).
    type: int
    required: true
  match:
    description:
    - ACL match filter object. One of `ip_subnet`, `ips_edge_services` or `http_filter` &
      `http_filter_value` are required.
    type: dict
  name:
    description:
    - ACL name.
    type: str
    required: true
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway lb acl
  stephrobert.scaleway.lb_acl:
    zone: <zone>
    acl_id: <acl_id>
    action: <action>
    index: <index>
    name: <name>
  register: result
"""

RETURN = r"""
resource:
  description:
  - Get information for a particular ACL, specified by its ACL ID. The response returns full
    details of the ACL, including its name, action, match rule and frontend.
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
    "acl_id": {"type": "str", "required": True},
    "action": {"type": "dict", "required": True},
    "description": {"type": "str"},
    "index": {"type": "int", "required": True},
    "match": {"type": "dict"},
    "name": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetAcl",
        method="GET",
        path="/lb/v1/zones/{zone}/acls/{acl_id}",
        path_params=("zone", "acl_id"),
        query_params=(),
    ),
    update_operation=Operation(
        id="UpdateAcl",
        method="PUT",
        path="/lb/v1/zones/{zone}/acls/{acl_id}",
        path_params=("zone", "acl_id"),
        query_params=(),
        body_params=("name", "action", "match", "index", "description"),
    ),
    managed_params=("name", "action", "match", "index", "description"),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
