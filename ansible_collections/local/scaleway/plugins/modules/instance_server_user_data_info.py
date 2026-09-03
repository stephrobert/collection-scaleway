#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetServerUserData, ListServerUserData
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_server_user_data_info
short_description: Gather information about Scaleway Instance server user data
version_added: 0.1.0
description:
- Get the content of a user data with the specified key on an Instance.
- List all user data keys registered on a specified Instance.
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
  key:
    description:
    - Key of the user data to get.
    type: str
  server_id:
    description:
    - UUID of the Instance.
    type: str
    required: true
extends_documentation_fragment:
- local.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Get user data
  local.scaleway.instance_server_user_data_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    key: 11111111-2222-3333-4444-555555555555
  register: result
- name: List user data
  local.scaleway.instance_server_user_data_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
user_data:
  description:
  - List all user data keys registered on a specified Instance.
  returned: when I(key) is omitted
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.local.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
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
    "key": {"type": "str", "no_log": False},
    "server_id": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetServerUserData",
        method="GET",
        path="/instance/v1/zones/{zone}/servers/{server_id}/user_data/{key}",
        path_params=("zone", "server_id", "key"),
        query_params=(),
    ),
    list_operation=Operation(
        id="ListServerUserData",
        method="GET",
        path="/instance/v1/zones/{zone}/servers/{server_id}/user_data",
        path_params=("zone", "server_id"),
        query_params=(),
        payload_field="user_data",
        is_list=True,
    ),
    selector="key",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
