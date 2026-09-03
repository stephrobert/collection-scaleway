#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetServer, UpdateServer
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_server
short_description: Manage a Scaleway Instance server
version_added: 0.1.0
description:
- Update the Instance information, such as name, boot mode, or tags.
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
  admin_password_encryption_ssh_key_id:
    description:
    - 'UUID of the SSH RSA key that will be used to encrypt the initial admin password for
      OS requiring it. Mandatory for Windows OS.

      The public_key value of this key is used to encrypt the admin password. When set to
      an empty string, reset this value and admin_password_encrypted_value to an empty string
      so a new password may be generated.'
    type: str
  boot_type:
    description:
    - Not documented by the Scaleway API contract.
    type: str
    choices:
    - local
    - bootscript
    - rescue
  commercial_type:
    description:
    - 'Set the commercial_type for this Instance.

      Warning: This field has some restrictions:

      - Cannot be changed if the Instance is not in `stopped` state.

      - Cannot be changed if the Instance is in a placement group.

      - Cannot be changed from/to a Windows offer to/from a Linux offer.

      - Local storage requirements of the target commercial_types must be fulfilled (i.e.
      if an Instance has 80GB of local storage, it can be changed into a GP1-XS, which has
      a maximum of 150GB, but it cannot be changed into a DEV1-S, which has only 20GB).'
    type: str
  dynamic_ip_required:
    description:
    - Not documented by the Scaleway API contract.
    type: bool
  enable_ipv6:
    description:
    - Not documented by the Scaleway API contract.
    - Deprecated by the Scaleway API contract.
    type: bool
  name:
    description:
    - Name of the Instance.
    type: str
  placement_group:
    description:
    - Placement group ID if Instance must be part of a placement group.
    type: str
  private_nics:
    description:
    - Instance private NICs.
    type: list
    elements: str
  protected:
    description:
    - True to activate server protection option.
    type: bool
  public_ips:
    description:
    - A list of reserved IP IDs to attach to the Instance.
    type: list
    elements: str
  routed_ip_enabled:
    description:
    - True to configure the instance so it uses the new routed IP mode (once this is set to
      True you cannot set it back to False).
    - Deprecated by the Scaleway API contract.
    type: bool
  security_group:
    description:
    - Not documented by the Scaleway API contract.
    type: dict
  tags:
    description:
    - Tags of the Instance.
    type: list
    elements: str
  volumes:
    description:
    - Not documented by the Scaleway API contract.
    type: dict
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway instance server
  stephrobert.scaleway.instance_server:
    zone: <zone>
    server_id: <server_id>
    name: <name>
  register: result
"""

RETURN = r"""
server:
  description:
  - Get the details of a specified Instance.
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
    "admin_password_encryption_ssh_key_id": {"type": "str", "no_log": True},
    "boot_type": {
        "type": "str",
        "choices": ["local", "bootscript", "rescue"],
    },
    "commercial_type": {"type": "str"},
    "dynamic_ip_required": {"type": "bool"},
    "enable_ipv6": {"type": "bool"},
    "name": {"type": "str"},
    "placement_group": {"type": "str"},
    "private_nics": {"type": "list", "elements": "str"},
    "protected": {"type": "bool"},
    "public_ips": {"type": "list", "elements": "str"},
    "routed_ip_enabled": {"type": "bool"},
    "security_group": {"type": "dict"},
    "tags": {"type": "list", "elements": "str"},
    "volumes": {"type": "dict"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetServer",
        method="GET",
        path="/instance/v1/zones/{zone}/servers/{server_id}",
        path_params=("zone", "server_id"),
        query_params=(),
        payload_field="server",
    ),
    update_operation=Operation(
        id="UpdateServer",
        method="PATCH",
        path="/instance/v1/zones/{zone}/servers/{server_id}",
        path_params=("zone", "server_id"),
        query_params=(),
        body_params=(
            "name",
            "boot_type",
            "tags",
            "volumes",
            "dynamic_ip_required",
            "routed_ip_enabled",
            "public_ips",
            "enable_ipv6",
            "protected",
            "security_group",
            "placement_group",
            "private_nics",
            "commercial_type",
            "admin_password_encryption_ssh_key_id",
        ),
        payload_field="server",
    ),
    managed_params=(
        "name",
        "boot_type",
        "tags",
        "volumes",
        "dynamic_ip_required",
        "routed_ip_enabled",
        "public_ips",
        "enable_ipv6",
        "protected",
        "security_group",
        "placement_group",
        "private_nics",
        "commercial_type",
        "admin_password_encryption_ssh_key_id",
    ),
    secret_params=("admin_password_encryption_ssh_key_id",),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
