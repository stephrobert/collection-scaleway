#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetVPC, UpdateVPC
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc
short_description: Manage a Scaleway VPC
version_added: 0.9.0
description:
- Update parameters including name and tags of the specified VPC.
- The module reads the resource first and writes only the fields that differ, so a second
  run reports no change.
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
  vpc_id:
    description:
    - VPC ID. (UUID format)
    type: str
    required: true
  name:
    description:
    - Name for the VPC.
    - 'To clear this field, write `name: ""`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  tags:
    description:
    - Tags for the VPC.
    - 'To clear this field, write `tags: []`; omit the option to leave the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: list
    elements: str
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
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# The module reads the resource, compares, and writes only what
# differs: run it twice and the second run reports no change.
#
# Check mode compares without writing, and `--diff` shows what would
# change. A parameter you do not pass is a parameter the module does
# not touch.

- name: Update a Scaleway VPC
  stephrobert.scaleway.vpc:
    region: fr-par
    vpc_id: 11111111-2222-3333-4444-555555555555
    name: my-resource
  register: result
- name: Preview the change on a Scaleway VPC without writing
  stephrobert.scaleway.vpc:
    region: fr-par
    vpc_id: 11111111-2222-3333-4444-555555555555
    name: my-resource
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
resource:
  description:
  - Retrieve details of an existing VPC, specified by its VPC ID.
  returned: success
  type: dict
  contains:
    id:
      description:
      - VPC ID. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the VPC.
      returned: when the API returns it
      type: str
    name:
      description:
      - VPC name.
      returned: when the API returns it
      type: str
    organization_id:
      description:
      - Scaleway Organization the VPC belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the VPC belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region of the VPC.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags for the VPC.
      returned: when the API returns it
      type: list
      elements: str
    is_default:
      description:
      - Defines whether the VPC is the default one for its Project.
      returned: when the API returns it
      type: bool
    created_at:
      description:
      - Date the VPC was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the VPC was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    private_network_count:
      description:
      - Number of Private Networks within this VPC.
      returned: when the API returns it
      type: int
    routing_enabled:
      description:
      - Defines whether the VPC routes traffic between its Private Networks.
      returned: when the API returns it
      type: bool
    custom_routes_propagation_enabled:
      description:
      - Defines whether the VPC advertises custom routes between its Private Networks.
      returned: when the API returns it
      type: bool
    transitivity_enabled:
      description:
      - Defines whether the VPC allows packets from peered VPCs to transit through.
      returned: when the API returns it
      type: bool
    object_storage_private_access_enabled:
      description:
      - Defines whether the Object Storage private access is enabled for the VPC.
      returned: when the API returns it
      type: bool
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402

from ansible_collections.stephrobert.scaleway.plugins.module_utils.scaleway import (  # noqa: E402
    ManageModule,
    Operation,
    poser_les_temoins,
    run_manage_module,
    scaleway_argument_spec,
)

#: Options propres au module, traduites depuis le contrat.
MODULE_ARGUMENT_SPEC = {
    "region": {
        "type": "str",
        "required": True,
        "choices": ["fr-par", "it-mil", "nl-ams", "pl-waw"],
    },
    "vpc_id": {"type": "str", "required": True},
    "name": {"type": "str"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetVPC",
        method="GET",
        path="/vpc/v2/regions/{region}/vpcs/{vpc_id}",
        path_params=("region", "vpc_id"),
        query_params=(),
        retry="safe",
    ),
    update_operation=Operation(
        id="UpdateVPC",
        method="PATCH",
        path="/vpc/v2/regions/{region}/vpcs/{vpc_id}",
        path_params=("region", "vpc_id"),
        query_params=(),
        body_params=("name", "tags"),
        retry="limited",
    ),
    managed_params=("name", "tags"),
    comparisons=(
        ("name", "scalar"),
        ("tags", "ordered_list"),
    ),
    nullable_params=("name", "tags"),
)

#: Ce que le contrat déclare effaçable. Ansible n'appelle un `fallback`
#: que sur une clé absente de l'invocation : le témoin note le nom sans
#: rien injecter, ce qui sépare `champ: null` de `champ` omis.
OMISSIONS = poser_les_temoins(ARGUMENT_SPEC, MODULE.nullable_params)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE, OMISSIONS)


if __name__ == "__main__":
    main()
