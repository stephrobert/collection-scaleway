#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetCertificate, ListCertificates
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_certificate_info
short_description: Gather information about Scaleway Load Balancer certificates
version_added: 0.3.0
description:
- Get information for a particular SSL/TLS certificate, specified by its certificate ID. The
  response returns full details of the certificate, including its type, main domain name,
  and alternative domain names.
- List all the SSL/TLS certificates on a given Load Balancer. The response is an array of
  certificate objects, which are by default listed in ascending order of creation date.
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
  lb_id:
    description:
    - Load Balancer ID.
    type: str
  name:
    description:
    - Certificate name to filter for, only certificates of this name will be returned.
    type: str
  order_by:
    description:
    - Sort order of certificates in the response.
    type: str
    choices:
    - created_at_asc
    - created_at_desc
    - name_asc
    - name_desc
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
# This module only reads: it never changes anything, and check mode
# is native.
#
# `certificate_id` decides which of the two reads runs: given, the
# module returns that one resource; omitted, it lists them all,
# walking every page rather than returning the first one in silence.

- name: Get an SSL/TLS certificate
  stephrobert.scaleway.lb_certificate_info:
    zone: fr-par-1
    certificate_id: 11111111-2222-3333-4444-555555555555
  register: result
- name: List all SSL/TLS certificates on a given Load Balancer
  stephrobert.scaleway.lb_certificate_info:
    zone: fr-par-1
  register: result
- name: Filter Scaleway Load Balancer certificates by name
  stephrobert.scaleway.lb_certificate_info:
    zone: fr-par-1
    name: my-certificate-info
  register: result
"""

RETURN = r"""
certificates:
  description:
  - List all the SSL/TLS certificates on a given Load Balancer. The response is an array of
    certificate objects, which are by default listed in ascending order of creation date.
  returned: when I(certificate_id) is omitted
  type: list
  elements: dict
  contains:
    type:
      description:
      - Certificate type (Let's Encrypt or custom).
      returned: when the API returns it
      type: str
    id:
      description:
      - Certificate ID.
      returned: when the API returns it
      type: str
    common_name:
      description:
      - Main domain name of certificate.
      returned: when the API returns it
      type: str
    subject_alternative_name:
      description:
      - Alternative domain names.
      returned: when the API returns it
      type: list
      elements: str
    fingerprint:
      description:
      - Identifier (SHA-1) of the certificate.
      returned: when the API returns it
      type: str
    not_valid_before:
      description:
      - Lower validity bound. (RFC 3339 format)
      returned: when the API returns it
      type: str
    not_valid_after:
      description:
      - Upper validity bound. (RFC 3339 format)
      returned: when the API returns it
      type: str
    status:
      description:
      - Certificate status.
      returned: when the API returns it
      type: str
    lb:
      description:
      - Load Balancer object the certificate is attached to.
      returned: when the API returns it
      type: dict
    name:
      description:
      - Certificate name.
      returned: when the API returns it
      type: str
    created_at:
      description:
      - Date on which the certificate was created. (RFC 3339 format)
      returned: when the API returns it
      type: str
    updated_at:
      description:
      - Date on which the certificate was last updated. (RFC 3339 format)
      returned: when the API returns it
      type: str
    status_details:
      description:
      - Additional information about the certificate status (useful in case of certificate
        generation failure, for example).
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
            "nl-ams-1",
            "nl-ams-2",
            "nl-ams-3",
            "pl-waw-1",
            "pl-waw-2",
            "pl-waw-3",
        ],
    },
    "certificate_id": {"type": "str"},
    "lb_id": {"type": "str"},
    "name": {"type": "str"},
    "order_by": {
        "type": "str",
        "choices": ["created_at_asc", "created_at_desc", "name_asc", "name_desc"],
    },
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = InfoModule(
    get_operation=Operation(
        id="GetCertificate",
        method="GET",
        path="/lb/v1/zones/{zone}/certificates/{certificate_id}",
        path_params=("zone", "certificate_id"),
        query_params=(),
    ),
    list_operation=Operation(
        id="ListCertificates",
        method="GET",
        path="/lb/v1/zones/{zone}/lbs/{lb_id}/certificates",
        path_params=("zone", "lb_id"),
        query_params=("order_by", "name"),
        payload_field="certificates",
        is_list=True,
        page_param="page",
        per_page_param="page_size",
    ),
    selector="certificate_id",
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_info_module(module, MODULE)


if __name__ == "__main__":
    main()
