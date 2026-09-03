#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) Stéphane Robert (@stephrobert)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This file is generated.
# Do not edit manually.
#
# Contrat    : specs/scaleway/lb.v1.yml
# Opérations : GetBackend, UpdateBackend
# Régénérer  : mise run generate

from __future__ import annotations

DOCUMENTATION = r"""
module: lb_backend
short_description: Manage a Scaleway Lb backend
version_added: 0.1.0
description:
- Update a backend of a given Load Balancer, specified by its backend ID. Note that the request
  type is PUT and not PATCH. You must set all parameters.
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
    - nl-ams-1
    - nl-ams-2
    - nl-ams-3
    - pl-waw-1
    - pl-waw-2
    - pl-waw-3
  backend_id:
    description:
    - Backend ID.
    type: str
    required: true
  failover_host:
    description:
    - Scaleway Object Storage bucket website to be served as failover if all backend servers
      are down, e.g. failover-website.s3-website.fr-par.scw.cloud.
    type: str
  forward_port:
    description:
    - Port to be used by the backend when forwarding traffic to backend servers.
    type: int
    required: true
  forward_port_algorithm:
    description:
    - Load balancing algorithm to be used when determining which backend server to forward
      new traffic to.
    type: str
    required: true
    choices:
    - roundrobin
    - leastconn
    - first
  forward_protocol:
    description:
    - Protocol to be used by the backend when forwarding traffic to backend servers.
    type: str
    required: true
    choices:
    - tcp
    - http
  ignore_ssl_server_verify:
    description:
    - Defines whether the server certificate verification should be ignored.
    type: bool
  max_connections:
    description:
    - Maximum number of connections allowed per backend server.
    type: int
  max_retries:
    description:
    - Number of retries when a backend server connection failed.
    type: int
  name:
    description:
    - Backend name.
    type: str
    required: true
  on_marked_down_action:
    description:
    - Action to take when a backend server is marked as down.
    type: str
    choices:
    - on_marked_down_action_none
    - shutdown_sessions
  proxy_protocol:
    description:
    - Protocol to use between the Load Balancer and backend servers. Allows the backend servers
      to be informed of the client's real IP address. The PROXY protocol must be supported
      by the backend servers' software.
    type: str
    choices:
    - proxy_protocol_unknown
    - proxy_protocol_none
    - proxy_protocol_v1
    - proxy_protocol_v2
    - proxy_protocol_v2_ssl
    - proxy_protocol_v2_ssl_cn
  redispatch_attempt_count:
    description:
    - Whether to use another backend server on each attempt.
    type: int
  send_proxy_v2:
    description:
    - Deprecated in favor of proxy_protocol field.
    - Deprecated by the Scaleway API contract.
    type: bool
  ssl_bridging:
    description:
    - Defines whether to enable SSL bridging between the Load Balancer and backend servers.
    type: bool
  sticky_sessions:
    description:
    - Defines whether to activate sticky sessions (binding a particular session to a particular
      backend server) and the method to use if so. None disables sticky sessions. Cookie-based
      uses an HTTP cookie to stick a session to a backend server. Table-based uses the source
      (client) IP address to stick a session to a backend server.
    type: str
    required: true
    choices:
    - none
    - cookie
    - table
  sticky_sessions_cookie_name:
    description:
    - Cookie name for cookie-based sticky sessions.
    type: str
  timeout_connect:
    description:
    - Maximum allowed time for establishing a connection to a backend server. (in milliseconds)
    type: float
  timeout_queue:
    description:
    - Maximum time for a request to be left pending in queue when `max_connections` is reached.
      (in seconds)
    type: str
  timeout_server:
    description:
    - Maximum allowed time for a backend server to process a request. (in milliseconds)
    type: float
  timeout_tunnel:
    description:
    - Maximum allowed tunnel inactivity time after Websocket is established (takes precedence
      over client and server timeout). (in milliseconds)
    type: float
extends_documentation_fragment:
- stephrobert.scaleway.scaleway
"""

EXAMPLES = r"""
- name: Update a Scaleway lb backend
  stephrobert.scaleway.lb_backend:
    zone: <zone>
    backend_id: <backend_id>
    forward_port: <forward_port>
    forward_port_algorithm: <forward_port_algorithm>
    forward_protocol: <forward_protocol>
    name: <name>
    sticky_sessions: <sticky_sessions>
  register: result
"""

RETURN = r"""
resource:
  description:
  - Get the full details of a given backend, specified by its backend ID. The response contains
    the backend's full configuration parameters including protocol, port and forwarding algorithm.
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
    "backend_id": {"type": "str", "required": True},
    "failover_host": {"type": "str"},
    "forward_port": {"type": "int", "required": True},
    "forward_port_algorithm": {
        "type": "str",
        "required": True,
        "choices": ["roundrobin", "leastconn", "first"],
    },
    "forward_protocol": {
        "type": "str",
        "required": True,
        "choices": ["tcp", "http"],
    },
    "ignore_ssl_server_verify": {"type": "bool"},
    "max_connections": {"type": "int"},
    "max_retries": {"type": "int"},
    "name": {"type": "str", "required": True},
    "on_marked_down_action": {
        "type": "str",
        "choices": ["on_marked_down_action_none", "shutdown_sessions"],
    },
    "proxy_protocol": {
        "type": "str",
        "choices": [
            "proxy_protocol_unknown",
            "proxy_protocol_none",
            "proxy_protocol_v1",
            "proxy_protocol_v2",
            "proxy_protocol_v2_ssl",
            "proxy_protocol_v2_ssl_cn",
        ],
    },
    "redispatch_attempt_count": {"type": "int"},
    "send_proxy_v2": {"type": "bool"},
    "ssl_bridging": {"type": "bool"},
    "sticky_sessions": {
        "type": "str",
        "required": True,
        "choices": ["none", "cookie", "table"],
    },
    "sticky_sessions_cookie_name": {"type": "str"},
    "timeout_connect": {"type": "float"},
    "timeout_queue": {"type": "str"},
    "timeout_server": {"type": "float"},
    "timeout_tunnel": {"type": "float"},
}

#: Les paramètres communs viennent du runtime : un module ne les redéclare pas.
ARGUMENT_SPEC: dict = {}
ARGUMENT_SPEC.update(scaleway_argument_spec())
ARGUMENT_SPEC.update(MODULE_ARGUMENT_SPEC)

#: Ce que le module exécute, et les décisions que le générateur a prises.
MODULE = ManageModule(
    read_operation=Operation(
        id="GetBackend",
        method="GET",
        path="/lb/v1/zones/{zone}/backends/{backend_id}",
        path_params=("zone", "backend_id"),
        query_params=(),
    ),
    update_operation=Operation(
        id="UpdateBackend",
        method="PUT",
        path="/lb/v1/zones/{zone}/backends/{backend_id}",
        path_params=("zone", "backend_id"),
        query_params=(),
        body_params=(
            "name",
            "forward_protocol",
            "forward_port",
            "forward_port_algorithm",
            "sticky_sessions",
            "sticky_sessions_cookie_name",
            "send_proxy_v2",
            "timeout_server",
            "timeout_connect",
            "timeout_tunnel",
            "on_marked_down_action",
            "proxy_protocol",
            "failover_host",
            "ssl_bridging",
            "ignore_ssl_server_verify",
            "redispatch_attempt_count",
            "max_retries",
            "max_connections",
            "timeout_queue",
        ),
    ),
    managed_params=(
        "name",
        "forward_protocol",
        "forward_port",
        "forward_port_algorithm",
        "sticky_sessions",
        "sticky_sessions_cookie_name",
        "send_proxy_v2",
        "timeout_server",
        "timeout_connect",
        "timeout_tunnel",
        "on_marked_down_action",
        "proxy_protocol",
        "failover_host",
        "ssl_bridging",
        "ignore_ssl_server_verify",
        "redispatch_attempt_count",
        "max_retries",
        "max_connections",
        "timeout_queue",
    ),
)


def main() -> None:
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    run_manage_module(module, MODULE)


if __name__ == "__main__":
    main()
