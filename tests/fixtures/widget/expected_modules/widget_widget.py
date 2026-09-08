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
short_description: Manage a Scaleway Widget
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
  email_config:
    description:
    - Email address configuration.
    - 'To clear this field, write `email_config: {}`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: dict
  label:
    description:
    - Free-form label of the widget.
    type: str
  protected:
    description:
    - Not documented by the Scaleway API contract.
    - 'The contract marks this field clearable, but bool has no empty value, so the API cannot
      clear it. Setting it to null is refused: this API reads null as "field not provided"
      and would change nothing.'
    type: bool
  secret_token:
    description:
    - Jeton de rotation.
    - 'To clear this field, write `secret_token: ""`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  tags:
    description:
    - Tags of the widget.
    - 'To clear this field, write `tags: []`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: list
    elements: str
  webhook_config:
    description:
    - Webhook URI configuration.
    - 'To clear this field, write `webhook_config: {}`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: dict
attributes:
  check_mode:
    description: In check mode the module reads the resource and compares it, then reports
      what it would write without writing it.
    support: full
  diff_mode:
    description: The module reports the fields that differ, read through the same projection
      the comparison uses.
    support: full
extends_documentation_fragment:
- lab.widget.scaleway
"""

EXAMPLES = r"""
# The module reads the resource, compares, and writes only what
# differs: run it twice and the second run reports no change.
#
# Check mode compares without writing, and `--diff` shows what would
# change. A parameter you do not pass is a parameter the module does
# not touch.

- name: Update a Scaleway Widget
  lab.widget.widget_widget:
    zone: fr-par-1
    widget_id: 11111111-2222-3333-4444-555555555555
    tags:
    - production
  register: result
- name: Preview the change on a Scaleway Widget without writing
  lab.widget.widget_widget:
    zone: fr-par-1
    widget_id: 11111111-2222-3333-4444-555555555555
    tags:
    - production
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
widget:
  description:
  - Get a widget
  returned: success
  type: dict
  contains:
    id:
      description:
      - Unique ID of the widget.
      returned: when the API returns it
      type: str
    name:
      description:
      - Name of the widget.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags of the widget.
      returned: when the API returns it
      type: list
      elements: str
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.lab.widget.plugins.module_utils.scaleway import (  # noqa: E402
    ManageModule,
    Operation,
    poser_les_temoins,
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
    "email_config": {"type": "dict"},
    "label": {"type": "str"},
    "protected": {"type": "bool"},
    "secret_token": {"type": "str", "no_log": True},
    "tags": {"type": "list", "elements": "str"},
    "webhook_config": {"type": "dict"},
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
        body_params=("tags", "label", "protected", "secret_token", "email_config", "webhook_config"),
    ),
    managed_params=("tags", "label", "protected", "secret_token", "email_config", "webhook_config"),
    comparisons=(
        ("email_config", "mapping"),
        ("label", "scalar"),
        ("protected", "scalar"),
        ("secret_token", "scalar"),
        ("tags", "ordered_list"),
        ("webhook_config", "mapping"),
    ),
    secret_params=("secret_token",),
    nullable_params=("email_config", "protected", "secret_token", "tags", "webhook_config"),
)

#: Ce que le contrat déclare effaçable. Ansible n'appelle un `fallback`
#: que sur une clé absente de l'invocation : le témoin note le nom sans
#: rien injecter, ce qui sépare `champ: null` de `champ` omis.
OMISSIONS = poser_les_temoins(ARGUMENT_SPEC, MODULE.nullable_params)


#: Ce que l'API interdit d'utiliser ensemble, déclaré par le contrat.
MUTUALLY_EXCLUSIVE = [
    ["email_config", "webhook_config"],
]


def main() -> None:
    module = AnsibleModule(
        argument_spec=ARGUMENT_SPEC,
        supports_check_mode=True,
        mutually_exclusive=MUTUALLY_EXCLUSIVE,
    )
    run_manage_module(module, MODULE, OMISSIONS)


if __name__ == "__main__":
    main()
