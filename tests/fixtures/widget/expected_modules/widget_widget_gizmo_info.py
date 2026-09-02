#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/widget/input/widget.v1.yml
# Opérations : ListWidgetGizmos
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: widget_widget_gizmo_info
short_description: Gather information about Scaleway Widget widget gizmos
version_added: 9.9.9
description:
- List the gizmos of a widget
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
extends_documentation_fragment:
- lab.widget.scaleway
"""

EXAMPLES = r"""
- name: List the gizmos of a widget
  lab.widget.widget_widget_gizmo_info:
    zone: fr-par-1
    widget_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

RETURN = r"""
widgets:
  description:
  - List the gizmos of a widget
  returned: success
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
    "widget_id": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    list_operation=Operation(
        id="ListWidgetGizmos",
        method="GET",
        path="/widget/v1/zones/{zone}/widgets/{widget_id}/gizmos",
        path_params=("zone", "widget_id"),
        query_params=(),
        payload_field="widgets",
        is_list=True,
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
