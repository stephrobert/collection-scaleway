#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/vpc.v2.yml
# Opérations : GetIngressRule, UpdateIngressRule
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: vpc_ingress_rule
short_description: Manage a Scaleway VPC ingress rule
version_added: 0.9.0
description:
- Update an ingress rule specified by its ingress rule ID.
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
  rule_id:
    description:
    - ID of the ingress rule to update. (UUID format)
    type: str
    required: true
  description:
    description:
    - Description to set for this ingress rule.
    - 'To clear this field, write `description: ""`; omit the option to leave the current
      value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  nexthop_private_network_id:
    description:
    - ID of the Private Network the destination resource is in. (UUID format)
    - 'To clear this field, write `nexthop_private_network_id: ""`; omit the option to leave
      the current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  nexthop_resource_ip:
    description:
    - IP of the local resource to redirect ingress traffic to. IP version must be consistent
      with the source network. (IP address)
    - 'To clear this field, write `nexthop_resource_ip: ""`; omit the option to leave the
      current value untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  source:
    description:
    - Source network to match ingress traffic on. Can be IPv4 or IPv6. (IP network)
    - 'To clear this field, write `source: ""`; omit the option to leave the current value
      untouched.'
    - 'Setting it to null is refused: this API reads null as "field not provided" and would
      change nothing.'
    type: str
  tags:
    description:
    - Tags to set for this ingress rule.
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

- name: Update a Scaleway VPC ingress rule
  stephrobert.scaleway.vpc_ingress_rule:
    region: fr-par
    rule_id: 11111111-2222-3333-4444-555555555555
    source: 1.2.3.4/32
  register: result
- name: Preview the change on a Scaleway VPC ingress rule without writing
  stephrobert.scaleway.vpc_ingress_rule:
    region: fr-par
    rule_id: 11111111-2222-3333-4444-555555555555
    source: 1.2.3.4/32
  register: result
  check_mode: true
  diff: true
"""

RETURN = r"""
resource:
  description:
  - Retrieve details of an existing ingress rule, specified by its ingress rule ID.
  returned: success
  type: dict
  contains:
    id:
      description:
      - ID of the ingress rule. (UUID format)
      returned: when the API returns it
      type: str
    srn:
      description:
      - The SRN of the ingress rule.
      returned: when the API returns it
      type: str
    vpc_id:
      description:
      - ID of the VPC this rule belongs to. (UUID format)
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date the ingress rule was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date the ingress rule was last modified. (RFC 3339 format)
      returned: when the API returns it
      type: str
    is_ipv6:
      description:
      - Whether this rule applies to IPv4 or IPv6 traffic.
      returned: when the API returns it
      type: bool
    source:
      description:
      - Source network to apply this rule on. (IP network)
      returned: when the API returns it
      type: str
    nexthop_resource_ip:
      description:
      - IP of the local resource to redirect ingress traffic to. (IP address)
      returned: when the API returns it
      type: str
    nexthop_private_network_id:
      description:
      - ID of the Private Network the destination resource is in. (UUID format)
      returned: when the API returns it
      type: str
    description:
      description:
      - Description of this ingress rule.
      returned: when the API returns it
      type: str
    tags:
      description:
      - Tags of this ingress rule.
      returned: when the API returns it
      type: list
      elements: str
    organization_id:
      description:
      - Scaleway Organization the ingress rule belongs to. (UUID format)
      returned: when the API returns it
      type: str
    project_id:
      description:
      - Scaleway Project the ingress rule belongs to. (UUID format)
      returned: when the API returns it
      type: str
    region:
      description:
      - Region of the ingress rule.
      returned: when the API returns it
      type: str
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
    "rule_id": {"type": "str", "required": True},
    "description": {"type": "str"},
    "nexthop_private_network_id": {"type": "str"},
    "nexthop_resource_ip": {"type": "str"},
    "source": {"type": "str"},
    "tags": {"type": "list", "elements": "str"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetIngressRule",
        method="GET",
        path="/vpc/v2/regions/{region}/ingress-rules/{rule_id}",
        path_params=("region", "rule_id"),
        query_params=(),
        retry="safe",
    ),
    update_operation=Operation(
        id="UpdateIngressRule",
        method="PATCH",
        path="/vpc/v2/regions/{region}/ingress-rules/{rule_id}",
        path_params=("region", "rule_id"),
        query_params=(),
        body_params=(
            "source",
            "nexthop_resource_ip",
            "nexthop_private_network_id",
            "description",
            "tags",
        ),
        retry="limited",
    ),
    managed_params=(
        "source",
        "nexthop_resource_ip",
        "nexthop_private_network_id",
        "description",
        "tags",
    ),
    comparisons=(
        ("description", "scalar"),
        ("nexthop_private_network_id", "scalar"),
        ("nexthop_resource_ip", "scalar"),
        ("source", "scalar"),
        ("tags", "ordered_list"),
    ),
    nullable_params=(
        "description",
        "nexthop_private_network_id",
        "nexthop_resource_ip",
        "source",
        "tags",
    ),
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
