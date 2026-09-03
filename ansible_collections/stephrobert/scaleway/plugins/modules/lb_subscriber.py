#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetSubscriber, UpdateSubscriber
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_subscriber
short_description: Manage a Scaleway Lb subscriber
version_added: 0.1.0
description:
- Update the parameters of a given subscriber (e.g. name, webhook configuration, email configuration),
  specified by its subscriber ID.
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
  subscriber_id:
    description:
    - Subscriber ID.
    type: str
    required: true
  email_config:
    description:
    - Email address configuration.
    type: dict
  name:
    description:
    - Subscriber name.
    type: str
    required: true
  webhook_config:
    description:
    - Webhook URI configuration.
    type: dict
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway lb subscriber
  stephrobert.scaleway.lb_subscriber:
    zone: <zone>
    subscriber_id: <subscriber_id>
    name: <name>
  register: result
"""

RETURN = r"""
resource:
  description:
  - Retrieve information about an existing subscriber, specified by its subscriber ID. Its
    full details, including name and email/webhook configuration, are returned in the response
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
    "subscriber_id": {"type": "str", "required": True},
    "email_config": {"type": "dict"},
    "name": {"type": "str", "required": True},
    "webhook_config": {"type": "dict"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetSubscriber",
        method="GET",
        path="/lb/v1/zones/{zone}/subscribers/{subscriber_id}",
        path_params=("zone", "subscriber_id"),
        query_params=(),
    ),
    update_operation=Operation(
        id="UpdateSubscriber",
        method="PUT",
        path="/lb/v1/zones/{zone}/subscribers/{subscriber_id}",
        path_params=("zone", "subscriber_id"),
        query_params=(),
        body_params=("name", "email_config", "webhook_config"),
    ),
    managed_params=("name", "email_config", "webhook_config"),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
