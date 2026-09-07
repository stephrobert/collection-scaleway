#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/instance.v1.yml
# Opérations : GetServer, ListServers
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: instance_server_info
short_description: Gather information about Scaleway Instance servers
version_added: 0.1.0
description:
- Get the details of a specified Instance.
- List all Instances in a specified Availability Zone, e.g. `fr-par-1`.
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
    - UUID of the Instance you want to get.
    type: str
  commercial_type:
    description:
    - List Instances of this commercial type.
    type: str
  name:
    description:
    - Filter Instances by name (eg. "server1" will return "server100" and "server1" but not
      "foo").
    type: str
  order:
    description:
    - Define the order of the returned servers.
    type: str
    choices:
    - creation_date_desc
    - creation_date_asc
    - modification_date_desc
    - modification_date_asc
  organization:
    description:
    - List only Instances of this Organization ID.
    type: str
  private_ip:
    description:
    - List Instances by private_ip. (IP address)
    - Deprecated by the Scaleway API contract.
    type: str
  private_network:
    description:
    - List Instances in this Private Network.
    type: str
  private_networks:
    description:
    - List Instances from the given Private Networks (use commas to separate them).
    type: str
  private_nic_mac_address:
    description:
    - List Instances associated with the given private NIC MAC address.
    type: str
  project:
    description:
    - List only Instances of this Project ID.
    type: str
  servers:
    description:
    - List Instances from these server ids (use commas to separate them).
    type: str
  state:
    description:
    - List Instances in this state.
    type: str
    choices:
    - running
    - stopped
    - stopped in place
    - starting
    - stopping
    - locked
  tags:
    description:
    - List Instances with these exact tags (to filter with several tags, use commas to separate
      them).
    type: list
    elements: str
  with_ip:
    description:
    - List Instances by IP (both private_ip and public_ip are supported). (IP address)
    type: str
  without_ip:
    description:
    - List Instances that are not attached to a public IP.
    type: bool
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.
#
# `server_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get an Instance
  stephrobert.scaleway.instance_server_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List all Instances
  stephrobert.scaleway.instance_server_info:
    zone: fr-par-1
  register: result
- name: Filter Scaleway Instance servers by tags
  stephrobert.scaleway.instance_server_info:
    zone: fr-par-1
    tags:
    - production
  register: result
"""

RETURN = r"""
server:
  description:
  - Get the details of a specified Instance.
  returned: when I(server_id) is provided
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
servers:
  description:
  - List all Instances in a specified Availability Zone, e.g. `fr-par-1`.
  returned: when I(server_id) is omitted
  type: list
  elements: dict
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
    "server_id": {"type": "str"},
    "commercial_type": {"type": "str"},
    "name": {"type": "str"},
    "order": {
        "type": "str",
        "choices": [
            "creation_date_desc",
            "creation_date_asc",
            "modification_date_desc",
            "modification_date_asc",
        ],
    },
    "organization": {"type": "str"},
    "private_ip": {"type": "str"},
    "private_network": {"type": "str"},
    "private_networks": {"type": "str"},
    "private_nic_mac_address": {"type": "str"},
    "project": {"type": "str"},
    "servers": {"type": "str"},
    "state": {
        "type": "str",
        "choices": ["running", "stopped", "stopped in place", "starting", "stopping", "locked"],
    },
    "tags": {"type": "list", "elements": "str"},
    "with_ip": {"type": "str"},
    "without_ip": {"type": "bool"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetServer",
        method="GET",
        path="/instance/v1/zones/{zone}/servers/{server_id}",
        path_params=("zone", "server_id"),
        query_params=(),
        payload_field="server",
    ),
    list_operation=Operation(
        id="ListServers",
        method="GET",
        path="/instance/v1/zones/{zone}/servers",
        path_params=("zone",),
        query_params=(
            "organization",
            "project",
            "name",
            "private_ip",
            "without_ip",
            "with_ip",
            "commercial_type",
            "state",
            "tags",
            "private_network",
            "order",
            "private_networks",
            "private_nic_mac_address",
            "servers",
        ),
        csv_params=("tags",),
        payload_field="servers",
        is_list=True,
        page_param="page",
        per_page_param="per_page",
    ),
    selector="server_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
