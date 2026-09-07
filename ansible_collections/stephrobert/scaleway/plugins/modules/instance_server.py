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
version_added: 0.4.0
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
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  boot_type:
    description:
    - Instance boot type.
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
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  dynamic_ip_required:
    description:
    - True if a dynamic IPv4 is required.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is bool.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  enable_ipv6:
    description:
    - True if IPv6 is enabled (deprecated and always `False` when `routed_ip_enabled` is `True`).
    - Deprecated by the Scaleway API contract.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is bool.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  name:
    description:
    - Name of the Instance.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  placement_group:
    description:
    - Placement group ID if Instance must be part of a placement group.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  private_nics:
    description:
    - Instance private NICs.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is list of str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  protected:
    description:
    - True to activate server protection option.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is bool.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  public_ips:
    description:
    - A list of reserved IP IDs to attach to the Instance.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is list of str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  routed_ip_enabled:
    description:
    - True to configure the instance so it uses the new routed IP mode (once this is set to
      True you cannot set it back to False).
    - Deprecated by the Scaleway API contract.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is bool.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  security_group:
    description:
    - Instance security group.
    type: dict
  tags:
    description:
    - Tags of the Instance.
    - 'Omit this option to keep the current value: the published default is only the marker
      of an omitted option, and the API type is list of str.'
    - An explicit null is refused, because clearing this field is not supported by the module
      yet.
    type: raw
    default: __unchanged__
  volumes:
    description:
    - Instance volumes.
    type: dict
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# The module reads the resource, compares, and writes only what
# differs: run it twice and the second run reports no change.
#
# Check mode compares without writing, and `--diff` shows what would
# change. A parameter you do not pass is a parameter the module does
# not touch.

- name: Update a Scaleway Instance server
  stephrobert.scaleway.instance_server:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    name: my-server
  register: result
- name: Preview the change on a Scaleway Instance server without writing
  stephrobert.scaleway.instance_server:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
    name: my-server
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
server:
  description:
  - Get the details of a specified Instance.
  returned: success
  type: dict
  contains:
    id:
      description:
      - Instance unique ID.
      returned: when the API returns it
      type: str
    name:
      description:
      - Instance name.
      returned: when the API returns it
      type: str
    organization:
      description:
      - Instance Organization ID.
      returned: when the API returns it
      type: str
    project:
      description:
      - Instance Project ID.
      returned: when the API returns it
      type: str
    allowed_actions:
      description:
      - List of allowed actions on the Instance.
      returned: when the API returns it
      type: list
      elements: str
    tags:
      description:
      - Tags associated with the Instance.
      returned: when the API returns it
      type: list
      elements: str
    commercial_type:
      description:
      - Instance commercial type (eg. GP1-M).
      returned: when the API returns it
      type: str
    creation_date:
      description:
      - Instance creation date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    dynamic_ip_required:
      description:
      - True if a dynamic IPv4 is required.
      returned: when the API returns it
      type: bool
    routed_ip_enabled:
      description:
      - True to configure the instance so it uses the routed IP mode. Use of `routed_ip_enabled`
        as `False` is deprecated.
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: bool
    enable_ipv6:
      description:
      - True if IPv6 is enabled (deprecated and always `False` when `routed_ip_enabled` is
        `True`).
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: bool
    hostname:
      description:
      - Instance host name.
      returned: when the API returns it
      type: str
    image:
      description:
      - Information about the Instance image.
      returned: when the API returns it
      type: dict
    protected:
      description:
      - Defines whether the Instance protection option is activated.
      returned: when the API returns it
      type: bool
    private_ip:
      description:
      - Private IP address of the Instance (deprecated and always `null` when `routed_ip_enabled`
        is `True`).
      returned: when the API returns it
      type: str
    public_ip:
      description:
      - Information about the public IP (deprecated in favor of `public_ips`).
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    public_ips:
      description:
      - Information about all the public IPs attached to the server.
      returned: when the API returns it
      type: list
      elements: dict
    mac_address:
      description:
      - The server's MAC address.
      returned: when the API returns it
      type: str
    modification_date:
      description:
      - Instance modification date. (RFC 3339 format)
      returned: when the API returns it
      type: str
    state:
      description:
      - Instance state.
      returned: when the API returns it
      type: str
    location:
      description:
      - Instance location.
      returned: when the API returns it
      type: dict
    ipv6:
      description:
      - Instance IPv6 address (deprecated when `routed_ip_enabled` is `True`).
      - Deprecated by the Scaleway API contract.
      returned: when the API returns it
      type: dict
    boot_type:
      description:
      - Instance boot type.
      returned: when the API returns it
      type: str
    volumes:
      description:
      - Instance volumes.
      returned: when the API returns it
      type: dict
    security_group:
      description:
      - Instance security group.
      returned: when the API returns it
      type: dict
    maintenances:
      description:
      - Instance planned maintenance.
      returned: when the API returns it
      type: list
      elements: dict
    state_detail:
      description:
      - Detailed information about the Instance state.
      returned: when the API returns it
      type: str
    arch:
      description:
      - Instance architecture.
      returned: when the API returns it
      type: str
    placement_group:
      description:
      - Instance placement group.
      returned: when the API returns it
      type: dict
    private_nics:
      description:
      - Instance private NICs.
      returned: when the API returns it
      type: list
      elements: dict
    zone:
      description:
      - Zone in which the Instance is located.
      returned: when the API returns it
      type: str
    admin_password_encryption_ssh_key_id:
      description:
      - 'UUID of the SSH RSA key that will be used to encrypt the initial admin password for
        OS requiring it. Mandatory for Windows OS.

        The public_key value of this key is used to encrypt the admin password. When set to
        an empty string, reset this value and admin_password_encrypted_value to an empty string
        so a new password may be generated.'
      returned: when the API returns it
      type: str
    admin_password_encrypted_value:
      description:
      - 'A base64 encoded string containing the admin password encrypted with the public key
        pointed to by admin_password_encryption_ssh_key_id.

        This value is reset when admin_password_encryption_ssh_key_id is set to an empty string.'
      returned: when the API returns it
      type: str
    filesystems:
      description:
      - List of attached filesystems.
      returned: when the API returns it
      type: list
      elements: dict
    end_of_service:
      description:
      - True if the Instance type has reached end of service.
      returned: when the API returns it
      type: bool
    dns:
      description:
      - Public DNS of the server.
      returned: when the API returns it
      type: str
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
    "admin_password_encryption_ssh_key_id": {"type": "raw", "default": "__unchanged__", "no_log": False},
    "boot_type": {
        "type": "str",
        "choices": ["local", "bootscript", "rescue"],
    },
    "commercial_type": {"type": "raw", "default": "__unchanged__"},
    "dynamic_ip_required": {"type": "raw", "default": "__unchanged__"},
    "enable_ipv6": {"type": "raw", "default": "__unchanged__"},
    "name": {"type": "raw", "default": "__unchanged__"},
    "placement_group": {"type": "raw", "default": "__unchanged__"},
    "private_nics": {"type": "raw", "default": "__unchanged__"},
    "protected": {"type": "raw", "default": "__unchanged__"},
    "public_ips": {"type": "raw", "default": "__unchanged__"},
    "routed_ip_enabled": {"type": "raw", "default": "__unchanged__"},
    "security_group": {"type": "dict"},
    "tags": {"type": "raw", "default": "__unchanged__"},
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
    comparisons=(
        ("admin_password_encryption_ssh_key_id", "scalar"),
        ("boot_type", "scalar"),
        ("commercial_type", "scalar"),
        ("dynamic_ip_required", "scalar"),
        ("enable_ipv6", "scalar"),
        ("name", "scalar"),
        ("placement_group", "scalar"),
        ("private_nics", "ordered_list"),
        ("protected", "scalar"),
        ("public_ips", "ordered_list"),
        ("routed_ip_enabled", "scalar"),
        ("security_group", "mapping"),
        ("tags", "ordered_list"),
        ("volumes", "mapping"),
    ),
    nullable_params=(
        ("admin_password_encryption_ssh_key_id", {"type": "str"}),
        ("commercial_type", {"type": "str"}),
        ("dynamic_ip_required", {"type": "bool"}),
        ("enable_ipv6", {"type": "bool"}),
        ("name", {"type": "str"}),
        ("placement_group", {"type": "str"}),
        ("private_nics", {"type": "list", "elements": "str"}),
        ("protected", {"type": "bool"}),
        ("public_ips", {"type": "list", "elements": "str"}),
        ("routed_ip_enabled", {"type": "bool"}),
        ("tags", {"type": "list", "elements": "str"}),
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
