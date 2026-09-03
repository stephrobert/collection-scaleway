#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/widget/input/widget.v1.yml
# Opérations : GetWidget, UpdateWidget
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: widget_widget
short_description: Manage a Scaleway Widget widget
version_added: 9.9.9
description:
- Update a widget
- The module reads the resource first and writes only the fields that differ, so a second
  run reports no change.
author:
- Contrat de laboratoire (@lab)
options:
  zone:
    description:
    - Not documented by the Scaleway API contract.
    type: str
    required: true
    choices:
    - fr-par-1
    - nl-ams-1
  widget_id:
    description:
    - Not documented by the Scaleway API contract.
    type: str
    required: true
  protected:
    description:
    - Not documented by the Scaleway API contract.
    type: bool
  secret_token:
    description:
    - Jeton de rotation.
    type: str
  tags:
    description:
    - Tags of the widget.
    type: list
    elements: str
extends_documentation_fragment:
- lab.widget.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway widget widget
  lab.widget.widget_widget:
    zone: <zone>
    widget_id: <widget_id>
    tags: <tags>
  register: result
"""

RETURN = r"""
widget:
  description:
  - Get a widget
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.lab.widget.plugins.module_utils.scaleway import (  # noqa: E402
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
        "choices": ["fr-par-1", "nl-ams-1"],
    },
    "widget_id": {"type": "str", "required": True},
    "protected": {"type": "bool"},
    "secret_token": {"type": "str", "no_log": True},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetWidget",
        method="GET",
        path="/widget/v1/zones/{zone}/widgets/{widget_id}",
        path_params=("zone", "widget_id"),
        query_params=(),
        payload_field="widget",
    ),
    update_operation=Operation(
        id="UpdateWidget",
        method="PATCH",
        path="/widget/v1/zones/{zone}/widgets/{widget_id}",
        path_params=("zone", "widget_id"),
        query_params=(),
        body_params=("tags", "protected", "secret_token"),
    ),
    managed_params=("tags", "protected", "secret_token"),
    secret_params=("secret_token",),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
