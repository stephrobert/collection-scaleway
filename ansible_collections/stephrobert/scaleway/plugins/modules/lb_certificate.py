#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetCertificate, UpdateCertificate
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_certificate
short_description: Manage a Scaleway Lb certificate
version_added: 0.1.0
description:
- Update the name of a particular SSL/TLS certificate, specified by its certificate ID.
- 'The module reads the resource first and writes the whole body, because this operation replaces
  the resource: fields you do not set keep the value the API returns. A second run reports
  no change.'
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
  certificate_id:
    description:
    - Certificate ID.
    type: str
    required: true
  name:
    description:
    - Certificate name.
    type: str
    required: true
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway lb certificate
  stephrobert.scaleway.lb_certificate:
    zone: <zone>
    certificate_id: <certificate_id>
    name: <name>
  register: result
"""

RETURN = r"""
resource:
  description:
  - Get information for a particular SSL/TLS certificate, specified by its certificate ID.
    The response returns full details of the certificate, including its type, main domain
    name, and alternative domain names.
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
    "certificate_id": {"type": "str", "required": True},
    "name": {"type": "str", "required": True},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetCertificate",
        method="GET",
        path="/lb/v1/zones/{zone}/certificates/{certificate_id}",
        path_params=("zone", "certificate_id"),
        query_params=(),
    ),
    update_operation=Operation(
        id="UpdateCertificate",
        method="PUT",
        path="/lb/v1/zones/{zone}/certificates/{certificate_id}",
        path_params=("zone", "certificate_id"),
        query_params=(),
        body_params=("name",),
    ),
    managed_params=("name",),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
