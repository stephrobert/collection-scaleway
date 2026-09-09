#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Contrat de laboratoire (@lab)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : tests/fixtures/widget/input/widget.v1.yml
# Opérations : ListWidgetTypes
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: widget_widget_type_info
short_description: Gather information about Scaleway Widget types
version_added: 9.9.9
description:
- Lister les types de widgets, sous forme de map.
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
attributes:
  check_mode:
    description: This module only reads, so check mode changes nothing about how it runs.
    support: full
  diff_mode:
    description: This module changes nothing, so it has no difference to report.
    support: none
extends_documentation_fragment:
- lab.widget.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.

- name: List widget types
  lab.widget.widget_widget_type_info:
    zone: fr-par-1
  register: result
"""

RETURN = r"""
types:
  description:
  - Lister les types de widgets, sous forme de map.
  returned: success
  type: dict
  contains:
    type_name:
      description:
      - Name of the widget type.
      returned: when the API returns it
      type: str
    gizmo_capacity:
      description:
      - How many gizmos this type carries.
      returned: when the API returns it
      type: int
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
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="ListWidgetTypes",
        method="GET",
        path="/widget/v1/zones/{zone}/widget-types",
        path_params=("zone",),
        query_params=(),
        payload_field="types",
        retry="safe",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
