# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Les groupes natifs, et l'assainissement de leurs noms.

Une seule implémentation de l'assainissement, ici, testée. Le plugin officiel
remplace trois caractères (`-`, espace, `:`) et laisse passer tout le reste :
`production/web` en ressort inchangé, et n'est pas un nom de groupe valide.

Ansible accepte pour un nom de groupe les lettres, les chiffres et le tiret
bas, et refuse un nom qui commence par un chiffre.
"""

from __future__ import annotations

import re
import unicodedata

from .models import InventoryHost

#: Ce que `group_by` accepte. Un axe absent de cette table est une faute de
#: configuration, pas un groupe vide créé en silence.
AXES: tuple[str, ...] = (
    "product",
    "project",
    "region",
    "zone",
    "state",
    "tags",
    "vpc",
    "private_network",
)

#: Préfixe des groupes produits par le plugin, pour qu'ils ne se confondent
#: pas avec ceux qu'un `keyed_groups` de l'utilisateur crée.
PREFIX = "scw"

_INVALIDES = re.compile(r"[^A-Za-z0-9_]+")


def sanitize_group_name(raw: str, fallback: str = "inconnu") -> str:
    """Rend un nom de groupe valide pour Ansible, de façon déterministe.

    Les accents sont dépliés plutôt que supprimés : `pré-prod` devient
    `pre_prod` et non `pr_prod`, ce qui reste lisible pour qui écrit le
    playbook.
    """
    texte = unicodedata.normalize("NFKD", str(raw))
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = _INVALIDES.sub("_", texte).strip("_")
    texte = re.sub(r"_{2,}", "_", texte)

    if not texte:
        return fallback
    if texte[0].isdigit():
        return f"_{texte}"
    return texte


def group_names(host: InventoryHost, axes: tuple[str, ...]) -> tuple[str, ...]:
    """Les groupes auxquels cette machine appartient, selon les axes demandés.

    Le produit est un axe à part entière, et non un tag injecté comme le fait
    le plugin officiel : `scaleway_tags` doit refléter ce que porte Scaleway,
    pas ce que le plugin y a glissé.
    """
    noms: list[str] = []

    for axe in axes:
        if axe == "product" and host.product:
            noms.append(f"{PREFIX}_product_{sanitize_group_name(host.product)}")
        elif axe == "project" and host.project_id:
            noms.append(f"{PREFIX}_project_{sanitize_group_name(host.project_id)}")
        elif axe == "region" and host.region:
            noms.append(f"{PREFIX}_region_{sanitize_group_name(host.region)}")
        elif axe == "zone" and host.zone:
            noms.append(f"{PREFIX}_zone_{sanitize_group_name(host.zone)}")
        elif axe == "state" and host.state:
            noms.append(f"{PREFIX}_state_{sanitize_group_name(host.state)}")
        elif axe == "tags":
            noms.extend(f"{PREFIX}_tag_{sanitize_group_name(tag)}" for tag in host.tags if tag)
        elif axe == "vpc":
            noms.extend(
                f"{PREFIX}_vpc_{sanitize_group_name(a.vpc_name or a.vpc_id)}"
                for a in host.private_networks
                if a.vpc_name or a.vpc_id
            )
        elif axe == "private_network":
            noms.extend(
                f"{PREFIX}_private_network_"
                f"{sanitize_group_name(a.private_network_name or a.private_network_id)}"
                for a in host.private_networks
            )

    # Trié et dédoublonné : deux exécutions doivent produire le même inventaire.
    return tuple(sorted(set(noms)))
