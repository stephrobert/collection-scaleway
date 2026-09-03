#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : ListAcls
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_frontend_acl_info
short_description: Gather information about Scaleway Load Balancer frontend acls
version_added: 0.1.0
description:
- List the ACLs for a given frontend, specified by its frontend ID. The response is an array
  of ACL objects, each one representing an ACL that denies or allows traffic based on certain
  conditions.
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
  frontend_id:
    description:
    - Frontend ID (ACLs attached to this frontend will be returned in the response).
    type: str
    required: true
  name:
    description:
    - ACL name to filter for.
    type: str
  order_by:
    description:
    - Sort order of ACLs in the response.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - name_asc
    - name_desc
  page:
    description:
    - The page number to return, from the paginated results.
    type: int
  page_size:
    description:
    - The number of ACLs to return.
    type: int
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: List ACLs for a given frontend
  stephrobert.scaleway.lb_frontend_acl_info:
    zone: fr-par-1
    frontend_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
acls:
  description:
  - List the ACLs for a given frontend, specified by its frontend ID. The response is an array
    of ACL objects, each one representing an ACL that denies or allows traffic based on certain
    conditions.
  returned: success
  type: list
  elements: dict
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
            "nl-ams-1",
            "nl-ams-2",
            "nl-ams-3",
            "pl-waw-1",
            "pl-waw-2",
            "pl-waw-3",
        ],
    },
    "frontend_id": {"type": "str", "required": True},
    "name": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc", "name_asc", "name_desc"],
    },
    "page": {"type": "int"},
    "page_size": {"type": "int"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    list_operation=Operation(
        id="ListAcls",
        method="GET",
        path="/lb/v1/zones/{zone}/frontends/{frontend_id}/acls",
        path_params=("zone", "frontend_id"),
        query_params=("order_by", "page", "page_size", "name"),
        payload_field="acls",
        is_list=True,
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
