#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetVPCConnector, ListVPCConnectors
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_connector_info
short_description: Gather information about Scaleway VPC connectors
version_added: 0.9.0
description:
- Retrieve details of an existing VPC connector, specified by its VPC connector ID.
- List existing VPC connectors in the specified region.
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
  vpc_connector_id:
    description:
    - VPC connector ID. (UUID format)
    type: str
  name:
    description:
    - Name to filter for. Only connectors with names containing this string will be returned.
    type: str
  order_by:
    description:
    - Sort order of the returned VPC connectors.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - name_asc
    - name_desc
  status:
    description:
    - Status of the VPC connector.
    type: str
    choices:
    - unknown_vpc_connector_status
    - orphan
    - peered
    - conflict
  tags:
    description:
    - Tags to filter for. Only connectors with one or more matching tags will be returned.
    type: list
    elements: str
  target_vpc_id:
    description:
    - Target VPC ID to filter for. Only connectors belonging to this target VPC will be returned.
      (UUID format)
    type: str
  vpc_id:
    description:
    - VPC ID to filter for. Only connectors belonging to this VPC will be returned. (UUID
      format)
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
# `vpc_connector_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get a VPC connector
  stephrobert.scaleway.vpc_connector_info:
    region: fr-par
    vpc_connector_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List VPC connectors
  stephrobert.scaleway.vpc_connector_info:
    region: fr-par
  register: result
- name: Filter Scaleway VPC connectors by tags
  stephrobert.scaleway.vpc_connector_info:
    region: fr-par
    tags:
    - production
  register: result
"""

RETURN = r"""
result:
  description:
  - Retrieve details of an existing VPC connector, specified by its VPC connector ID.
  - 'The API contract names no payload field for this operation: the response body is returned
    as is.'
  returned: when I(vpc_connector_id) is provided
  type: dict
  contains:
    id:
      description:
      - VPC connector ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the VPC connector.
      returned: when the API returns it
      type: str
    name:
      description:
      - VPC connector name.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Scaleway Organization the VPC connector belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the VPC connector belongs to. (UUID format)
      returned: when the API returns it
      type: str
    vpc_id:
      description:
      - VPC the VPC connector belongs to (origin VPC). (UUID format)
      returned: when the API returns it
      type: str
    target_vpc_id:
      description:
      - VPC with which the VPC connector is peered (target VPC). (UUID format)
      returned: when the API returns it
      type: str
    status:
      description:
      - Status of the VPC connector.
      returned: when the API returns it
      type: str
    peer_info:
      description:
      - Peer info of target VPC. Available when status is Peered.
      returned: when the API returns it
      type: dict
    region:
      description:
      - Region of the VPC connector.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags for the VPC connector.
      returned: when the API returns it
      type: list
      elements: str
    created_at:
      description:
      - Date the VPC connector was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the VPC connector was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
vpc_connectors:
  description:
  - List existing VPC connectors in the specified region.
  returned: when I(vpc_connector_id) is omitted
  type: list
  elements: dict
  contains:
    id:
      description:
      - VPC connector ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the VPC connector.
      returned: when the API returns it
      type: str
    name:
      description:
      - VPC connector name.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Scaleway Organization the VPC connector belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the VPC connector belongs to. (UUID format)
      returned: when the API returns it
      type: str
    vpc_id:
      description:
      - VPC the VPC connector belongs to (origin VPC). (UUID format)
      returned: when the API returns it
      type: str
    target_vpc_id:
      description:
      - VPC with which the VPC connector is peered (target VPC). (UUID format)
      returned: when the API returns it
      type: str
    status:
      description:
      - Status of the VPC connector.
      returned: when the API returns it
      type: str
    peer_info:
      description:
      - Peer info of target VPC. Available when status is Peered.
      returned: when the API returns it
      type: dict
    region:
      description:
      - Region of the VPC connector.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags for the VPC connector.
      returned: when the API returns it
      type: list
      elements: str
    created_at:
      description:
      - Date the VPC connector was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the VPC connector was last modified. (RFC 3339 format)
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
    "vpc_connector_id": {"type": "str"},
    "name": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc", "name_asc", "name_desc"],
    },
    "status": {
        "type": "str",
        "choices": ["unknown_vpc_connector_status", "orphan", "peered", "conflict"],
    },
    "tags": {"type": "list", "elements": "str"},
    "target_vpc_id": {"type": "str"},
    "vpc_id": {"type": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetVPCConnector",
        method="GET",
        path="/vpc/v2/regions/{region}/vpc-connectors/{vpc_connector_id}",
        path_params=("region", "vpc_connector_id"),
        query_params=(),
        retry="safe",
    ),
    list_operation=Operation(
        id="ListVPCConnectors",
        method="GET",
        path="/vpc/v2/regions/{region}/vpc-connectors",
        path_params=("region",),
        query_params=(
            "order_by",
            "name",
            "tags",
            "organization_id",
            "project_id",
            "vpc_id",
            "target_vpc_id",
            "status",
        ),
        payload_field="vpc_connectors",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
        retry="safe",
    ),
    selector="vpc_connector_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
