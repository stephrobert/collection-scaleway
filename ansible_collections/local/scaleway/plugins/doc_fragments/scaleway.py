# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Documentation des paramètres communs.

Ce fragment est le pendant documentaire de `scaleway_argument_spec()` : les
deux décrivent le même ensemble, et `ansible-test sanity` échoue si l'un
diverge de l'autre. Un module généré ne redéclare jamais ces options.
"""

from __future__ import annotations


class ModuleDocFragment:
    DOCUMENTATION = r"""
options:
  profile:
    description:
      - Name of the profile to read in the Scaleway configuration file.
    type: str
  config_file:
    description:
      - Path to the Scaleway configuration file.
    type: path
  access_key:
    description:
      - Scaleway API access key.
    type: str
  secret_key:
    description:
      - Scaleway API secret key.
    type: str
  api_url:
    description:
      - URL of the Scaleway API endpoint.
      - Point it at a local emulator to exercise a playbook without credentials.
      - >-
        Falls back to the Scaleway configuration file, then to
        C(https://api.scaleway.com). It carries no module default on purpose:
        a default is never unset, so it would always override the profile.
    type: str
  api_allow_insecure:
    description:
      - Allow the API endpoint to be reached without verifying its TLS certificate.
      - Falls back to the Scaleway configuration file, then to C(false).
    type: bool
  api_timeout:
    description:
      - Seconds allowed for a single API call, connection and read.
      - >-
        Without a limit a silent connection would hang the module forever: the
        Scaleway SDK issues its requests with no timeout at all.
      - >-
        This bounds a single call, not a whole wait. Modules that can wait for
        a state bound the overall wait separately.
    type: int
    default: 60
  user_agent:
    description:
      - Value of the User-Agent header sent to the API.
    type: str
  organization_id:
    description:
      - Default Organization ID used when an operation does not name one.
    type: str
  project_id:
    description:
      - Default Project ID used when an operation does not name one.
    type: str
requirements:
  - scaleway >= 2.9.0
notes:
  - >-
    Every option can be set from its environment variable, respectively
    C(SCW_PROFILE), C(SCW_CONFIG_PATH), C(SCW_ACCESS_KEY), C(SCW_SECRET_KEY),
    C(SCW_API_URL), C(SCW_DEFAULT_ORGANIZATION_ID) and C(SCW_DEFAULT_PROJECT_ID).
  - Module options take precedence over environment variables, which take
    precedence over the configuration file.
"""
