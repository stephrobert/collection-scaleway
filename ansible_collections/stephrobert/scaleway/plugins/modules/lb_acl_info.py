#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetAcl
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_acl_info
short_description: Gather information about Scaleway Load Balancer acls
version_added: 0.1.0
description:
- Get information for a particular ACL, specified by its ACL ID. The response returns full
  details of the ACL, including its name, action, match rule and frontend.
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
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get an ACL
  stephrobert.scaleway.lb_acl_info:
    zone: fr-par-1
    acl_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
result:
  description:
  - Get information for a particular ACL, specified by its ACL ID. The response returns full
    details of the ACL, including its name, action, match rule and frontend.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: success
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
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetAcl",
        method="GET",
        path="/lb/v1/zones/{zone}/acls/{acl_id}",
        path_params=("zone", "acl_id"),
        query_params=(),
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
