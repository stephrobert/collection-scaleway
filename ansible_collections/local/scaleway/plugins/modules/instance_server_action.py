#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : ServerAction
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_server_action
short_description: Perform an action on a Scaleway Instance server
version_added: 0.1.0
description:
- 'Perform an action on an Instance.

  Available actions are:

  * `poweron`: Start a stopped Instance.

  * `poweroff`: Fully stop the Instance and release the hypervisor slot.

  * `stop_in_place`: Stop the Instance, but keep the slot on the hypervisor.

  * `reboot`: Stop the instance and restart it.'
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
  server_id:
    description:
    - UUID of the Instance.
    type: str
    required: true
  action:
    description:
    - Action to perform on the Instance.
    type: str
    required: true
    choices:
    - poweron
    - poweroff
    - reboot
    - stop_in_place
extends_documentation_fragment:
- local.scaleway.scaleway
- local.scaleway.waitable
"""

EXAMPLES = r"""
- name: Poweron an Instance
  local.scaleway.instance_server_action:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    action: poweron
  register: result
- name: Poweroff an Instance
  local.scaleway.instance_server_action:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    action: poweroff
  register: result
- name: Reboot an Instance
  local.scaleway.instance_server_action:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    action: reboot
  register: result
- name: Stop in place an Instance
  local.scaleway.instance_server_action:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    action: stop_in_place
  register: result
"""

RETURN = r"""
action:
  description:
  - The action that was requested.
  returned: always
  type: str
state:
  description:
  - State of the resource once the action completed.
  returned: when the module waited for the action to complete
  type: str
task:
  description:
  - 'Perform an action on an Instance.

    Available actions are:

    * `poweron`: Start a stopped Instance.

    * `poweroff`: Fully stop the Instance and release the hypervisor slot.

    * `stop_in_place`: Stop the Instance, but keep the slot on the hypervisor.

    * `reboot`: Stop the instance and restart it.

    * `backup`: Create an image with all the volumes of an Instance.

    * `terminate`: Delete the Instance along with its attached local volumes.

    * `enable_routed_ip`: Migrate the Instance to the new network stack.'
  returned: when the API returns it
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.local.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
    ActionModule,
    Operation,
    run_action_module,
    scaleway_argument_spec,
    scaleway_waitable_argument_spec,
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
    "server_id": {"type": "str", "required": True},
    "action": {
        "type": "str",
        "required": True,
        "choices": ["poweron", "poweroff", "reboot", "stop_in_place"],
    },
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(scaleway_waitable_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ActionModule(
    operation=Operation(
        id="ServerAction",
        method="POST",
        path="/instance/v1/zones/{zone}/servers/{server_id}/action",
        path_params=("zone", "server_id"),
        query_params=(),
        body_params=("action",),
        payload_field="task",
    ),
    action_parameter="action",
    read_operation=Operation(
        id="GetServer",
        method="GET",
        path="/instance/v1/zones/{zone}/servers/{server_id}",
        path_params=("zone", "server_id"),
        query_params=(),
        payload_field="server",
    ),
    state_field="state",
    wait_states={
        "poweroff": "stopped",
        "poweron": "running",
        "reboot": "running",
        "stop_in_place": "stopped in place",
    },
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_action_module(module, MODULE)


if __name__ == "__main__":
    main()
