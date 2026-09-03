# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Documentation de l'attente, pour les modules qui déclenchent un traitement.

Pendant du `scaleway_waitable_argument_spec()` du runtime. Un module
d'information n'hérite pas de ce fragment : il ne déclenche rien, donc il n'a
rien à attendre.

Les noms et les valeurs sont ceux de la collection officielle : un utilisateur
qui passe de l'une à l'autre ne doit pas réapprendre.
"""

from __future__ import annotations


class ModuleDocFragment:
    DOCUMENTATION = r"""
options:
  wait:
    description:
      - Wait for the action to reach its expected state before returning.
      - When false, the module returns as soon as the API accepts the action.
    type: bool
    default: true
  wait_timeout:
    description:
      - How long to wait for the expected state, in seconds.
    type: int
    default: 300
"""
