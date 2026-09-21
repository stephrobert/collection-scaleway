#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/ipam.v1.yml
# Opérations : GetIP, ListIPs
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: ipam_ip_info
short_description: Gather information about Scaleway IPAM IPs
version_added: 0.9.0
description:
- Retrieve details of an existing IP, specified by its IP ID.
- List existing IPs in the specified region using various filters. For example, you can filter
  for IPs within a specified Private Network, or for public IPs within a specified Project.
  By default, the IPs returned in the list are ordered by creation date in ascending order,
  though this can be modified via the order_by field.
author:
- Stéphane Robert (@stephrobert)
options:
  region:
    description:
    - The region you want to target
    type: str
    required: true
    choices:
    - fr-par
    - it-mil
    - nl-ams
    - pl-waw
  ip_id:
    description:
    - IP ID. (UUID format)
    type: str
  attached:
    description:
    - Defines whether to filter only for IPs which are attached to a resource.
    type: bool
  ip_ids:
    description:
    - IP IDs to filter for. Only IPs with these UUIDs will be returned.
    type: list
    elements: str
  is_ipv6:
    description:
    - Defines whether to filter only for IPv4s or IPv6s.
    type: bool
  mac_address:
    description:
    - MAC address to filter for. Only IPs attached to a resource with this MAC address will
      be returned.
    type: str
  order_by:
    description:
    - Sort order of the returned IPs.
    type: str
    choices:
    - created_at_desc
    - created_at_asc
    - updated_at_desc
    - updated_at_asc
    - attached_at_desc
    - attached_at_asc
    - ip_address_desc
    - ip_address_asc
    - mac_address_desc
    - mac_address_asc
  resource_id:
    description:
    - Resource ID to filter for. Only IPs attached to this resource will be returned. (UUID
      format)
    type: str
  resource_ids:
    description:
    - Resource IDs to filter for. Only IPs attached to at least one of these resources will
      be returned.
    type: list
    elements: str
  resource_name:
    description:
    - Attached resource name to filter for, only IPs attached to a resource with this string
      within their name will be returned.
    type: str
  resource_type:
    description:
    - Resource type to filter for. Only IPs attached to this type of resource will be returned.
    type: str
    choices:
    - unknown_type
    - custom
    - instance_server
    - instance_ip
    - instance_private_nic
    - lb_server
    - fip_ip
    - vpc_gateway
    - vpc_gateway_network
    - k8s_node
    - k8s_cluster
    - rdb_instance
    - redis_cluster
    - baremetal_server
    - baremetal_private_nic
    - llm_deployment
    - mgdb_instance
    - apple_silicon_server
    - apple_silicon_private_nic
    - serverless_container
    - serverless_function
    - vpn_gateway
    - ddl_datalab
    - kafka_cluster
    - bgp_endpoint
    - scbl_sedb_cluster
    - dtwh_deployment
    - sedb_cluster
    - msgq_cluster
    - edge_vpc_endpoint
    - dviz_cluster
    - nats_cluster
  resource_types:
    description:
    - Resource types to filter for. Only IPs attached to these types of resources will be
      returned.
    type: list
    elements: str
  tags:
    description:
    - Tags to filter for, only IPs with one or more matching tags will be returned.
    type: list
    elements: str
  vpc_id:
    description:
    - 'VPC ID to filter for.

      Only IPs owned by resources in this VPC will be returned.'
    type: str
attributes:
  check_mode:
    description: This module only reads, so check mode changes nothing about how it runs.
    support: full
  diff_mode:
    description: This module changes nothing, so it has no difference to report.
    support: none
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.
#
# `ip_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get an IP
  stephrobert.scaleway.ipam_ip_info:
    region: fr-par
    ip_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List existing IPs
  stephrobert.scaleway.ipam_ip_info:
    region: fr-par
  register: result
- name: Filter Scaleway IPAM IPs by tags
  stephrobert.scaleway.ipam_ip_info:
    region: fr-par
    tags:
    - production
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve details of an existing IP, specified by its IP ID.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(ip_id) is provided
  type: dict
  contains:
    id:
      description:
      - IP ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the IP.
      returned: when the API returns it
      type: str
    address:
      description:
      - IPv4 or IPv6 address in CIDR notation. (IP network)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the IP belongs to. (UUID format)
      returned: when the API returns it
      type: str
    is_ipv6:
      description:
      - Defines whether the IP is an IPv6 (false = IPv4).
      returned: when the API returns it
      type: bool
    created_at:
      description:
      - Date the IP was reserved. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the IP was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    source:
      description:
      - Source pool where the IP was reserved in.
      returned: when the API returns it
      type: dict
    resource:
      description:
      - Resource which the IP is attached to.
      returned: when the API returns it
      type: dict
    tags:
      description:
      - Tags for the IP.
      returned: when the API returns it
      type: list
      elements: str
    reverses:
      description:
      - Array of reverses associated with the IP.
      returned: when the API returns it
      type: list
      elements: dict
    region:
      description:
      - Region of the IP.
      returned: when the API returns it
      type: str
    zone:
      description:
      - Zone of the IP, if zonal.
      returned: when the API returns it
      type: str
ips:
  description:
  - List existing IPs in the specified region using various filters. For example, you can
    filter for IPs within a specified Private Network, or for public IPs within a specified
    Project. By default, the IPs returned in the list are ordered by creation date in ascending
    order, though this can be modified via the order_by field.
  returned: when I(ip_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - IP ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the IP.
      returned: when the API returns it
      type: str
    address:
      description:
      - IPv4 or IPv6 address in CIDR notation. (IP network)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the IP belongs to. (UUID format)
      returned: when the API returns it
      type: str
    is_ipv6:
      description:
      - Defines whether the IP is an IPv6 (false = IPv4).
      returned: when the API returns it
      type: bool
    created_at:
      description:
      - Date the IP was reserved. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the IP was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    source:
      description:
      - Source pool where the IP was reserved in.
      returned: when the API returns it
      type: dict
    resource:
      description:
      - Resource which the IP is attached to.
      returned: when the API returns it
      type: dict
    tags:
      description:
      - Tags for the IP.
      returned: when the API returns it
      type: list
      elements: str
    reverses:
      description:
      - Array of reverses associated with the IP.
      returned: when the API returns it
      type: list
      elements: dict
    region:
      description:
      - Region of the IP.
      returned: when the API returns it
      type: str
    zone:
      description:
      - Zone of the IP, if zonal.
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
    "region": {
        "type": "str",
        "required": True,
        "choices": ["fr-par", "it-mil", "nl-ams", "pl-waw"],
    },
    "ip_id": {"type": "str"},
    "attached": {"type": "bool"},
    "ip_ids": {"type": "list", "elements": "str"},
    "is_ipv6": {"type": "bool"},
    "mac_address": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": [
            "created_at_desc",
            "created_at_asc",
            "updated_at_desc",
            "updated_at_asc",
            "attached_at_desc",
            "attached_at_asc",
            "ip_address_desc",
            "ip_address_asc",
            "mac_address_desc",
            "mac_address_asc",
        ],
    },
    "resource_id": {"type": "str"},
    "resource_ids": {"type": "list", "elements": "str"},
    "resource_name": {"type": "str"},
    "resource_type": {
        "type": "str",
        "choices": [
            "unknown_type",
            "custom",
            "instance_server",
            "instance_ip",
            "instance_private_nic",
            "lb_server",
            "fip_ip",
            "vpc_gateway",
            "vpc_gateway_network",
            "k8s_node",
            "k8s_cluster",
            "rdb_instance",
            "redis_cluster",
            "baremetal_server",
            "baremetal_private_nic",
            "llm_deployment",
            "mgdb_instance",
            "apple_silicon_server",
            "apple_silicon_private_nic",
            "serverless_container",
            "serverless_function",
            "vpn_gateway",
            "ddl_datalab",
            "kafka_cluster",
            "bgp_endpoint",
            "scbl_sedb_cluster",
            "dtwh_deployment",
            "sedb_cluster",
            "msgq_cluster",
            "edge_vpc_endpoint",
            "dviz_cluster",
            "nats_cluster",
        ],
    },
    "resource_types": {"type": "list", "elements": "str"},
    "tags": {"type": "list", "elements": "str"},
    "vpc_id": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetIP",
        method="GET",
        path="/ipam/v1/regions/{region}/ips/{ip_id}",
        path_params=("region", "ip_id"),
        query_params=(),
        retry="safe",
    ),
    list_operation=Operation(
        id="ListIPs",
        method="GET",
        path="/ipam/v1/regions/{region}/ips",
        path_params=("region",),
        query_params=(
            "order_by",
            "project_id",
            "vpc_id",
            "attached",
            "resource_name",
            "resource_id",
            "resource_ids",
            "resource_type",
            "resource_types",
            "mac_address",
            "tags",
            "organization_id",
            "is_ipv6",
            "ip_ids",
        ),
        payload_field="ips",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    ),
    selector="ip_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
