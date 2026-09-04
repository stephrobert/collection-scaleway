#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/widget/input/widget.v1.yml
# Opérations : GetWidget, ListWidgets
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: widget_widget_info
short_description: Gather information about Scaleway Widget widgets
version_added: 9.9.9
description:
- Get a widget
- Lister les widgets d'une zone.
author:
- Contrat de laboratoire (@lab)
options:
  zone:
    description:
    - The zone you want to target
    type: str
    required: true
    choices:
    - fr-par-1
    - nl-ams-1
  widget_id:
    description:
    - Not documented by the Scaleway API contract.
    type: str
  state:
    description:
    - List widgets in this state.
    type: str
    choices:
    - running
    - stopped
extends_documentation_fragment:
- lab.widget.scaleway
"""

EXAMPLES = r"""
- name: Get a widget
  lab.widget.widget_widget_info:
    zone: fr-par-1
    widget_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List widgets
  lab.widget.widget_widget_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
widget:
  description:
  - Get a widget
  returned: when I(widget_id) is provided
  type: dict
widgets:
  description:
  - Lister les widgets d'une zone.
  returned: when I(widget_id) is omitted
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.lab.widget.plugins.module_utils.scaleway import (  # noqa: E402
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
        "choices": ["fr-par-1", "nl-ams-1"],
    },
    "widget_id": {"type": "str"},
    "state": {
        "type": "str",
        "choices": ["running", "stopped"],
    },
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetWidget",
        method="GET",
        path="/widget/v1/zones/{zone}/widgets/{widget_id}",
        path_params=("zone", "widget_id"),
        query_params=(),
        payload_field="widget",
    ),
    list_operation=Operation(
        id="ListWidgets",
        method="GET",
        path="/widget/v1/zones/{zone}/widgets",
        path_params=("zone",),
        query_params=("state",),
        payload_field="widgets",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="widget_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
