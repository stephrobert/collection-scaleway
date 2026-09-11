"""Écrit la table de résolution que le runtime consomme.

Pas de Jinja ici, et ce n'est pas une économie : il n'y a aucune décision à
prendre au rendu. Ce que la table contient a été décidé par
`generator.ansible.resolution`, et ce module se contente de l'écrire d'une
façon qui se relit en diff.

**Les refus sont écrits, pas seulement les résolutions.** Un identifiant absent
de la table pour cause de contrat muet et un identifiant absent parce que
personne n'y a pensé se ressemblent trop. `UNRESOLVABLE` porte la raison, et le
lookup la rend à l'utilisateur au lieu d'un « inconnu » qui l'enverrait chercher
une faute de frappe.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from generator.ansible.resolution import Refus, Resolution
from generator.ansible.retry import politique_par_defaut
from generator.ir.enums import HTTPMethod, OperationKind
from generator.renderer.modules import python_literal

EN_TETE = "# This file is generated. Do not edit manually."


def _retry(resolution: Resolution, classifications: Mapping[str, OperationKind]) -> str:
    """La politique de réessai de la liste, calculée par la règle du dépôt.

    On ne suppose pas `safe` parce que c'est un GET : `politique_par_defaut`
    regarde la classe avant la méthode, et c'est elle qui sait qu'une action est
    un POST plutôt qu'un GET (ADR-018). Une seconde règle écrite ici finirait
    par diverger de celle que les modules appliquent.
    """
    classe = classifications.get(resolution.list_operation, OperationKind.INFO)
    return politique_par_defaut(HTTPMethod(resolution.http_method), classe).value


def render_resolution(
    resolutions: Sequence[Resolution],
    refus: Sequence[Refus],
    *,
    classifications: Mapping[str, OperationKind],
    sources: Sequence[str],
) -> str:
    """Rend le module de table, trié, donc comparable d'une génération à l'autre."""
    lignes: list[str] = [
        EN_TETE,
        '"""Ce qu\'un nom permet de retrouver, tel que les contrats le déclarent.',
        "",
        "Cette table est dérivée des contrats versionnés, jamais écrite à la main :",
        "une ressource qui cesse d'être listable, ou qui perd son champ `name`, sort",
        "d'ici à la génération suivante plutôt que de rester une promesse.",
        "",
        "Contrats lus :",
        "",
    ]
    lignes += [f"    {source}" for source in sorted(sources)]
    lignes += [
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from .scaleway import Operation, ResourceLookup",
        "",
        "#: Les identifiants qu'un nom suffit à retrouver, et comment.",
        "RESOLUTIONS: dict[str, ResourceLookup] = {",
    ]

    for resolution in sorted(resolutions, key=lambda item: item.parameter):
        lignes += [
            f'    "{resolution.parameter}": ResourceLookup(',
            f'        parameter="{resolution.parameter}",',
            f'        service="{resolution.service}",',
            f'        schema="{resolution.schema}",',
            "        operation=Operation(",
            f'            id="{resolution.list_operation}",',
            f'            method="{resolution.http_method}",',
            f'            path="{resolution.path}",',
            f"            path_params={python_literal(_chemin(resolution), indent=12)},",
            f"            query_params={python_literal(resolution.query_params, indent=12)},",
            f'            payload_field="{resolution.payload_field}",',
            "            is_list=True,",
            f"            page_param={python_literal(resolution.page_param)},",
            f"            per_page_param={python_literal(resolution.per_page_param)},",
            f'            retry="{_retry(resolution, classifications)}",',
            "        ),",
            f"        scope={python_literal(resolution.scope, indent=8)},",
            f"        filters_by_name={resolution.filters_by_name},",
            "    ),",
        ]

    lignes += [
        "}",
        "",
        "#: Ce que les contrats ne permettent pas de résoudre, **avec sa raison**.",
        "#: Le lookup la rend telle quelle : « inconnu » enverrait l'utilisateur",
        "#: chercher une faute de frappe dans un nom qui est correct.",
        "UNRESOLVABLE: dict[str, str] = {",
    ]
    for refuse in sorted(refus, key=lambda item: item.parameter):
        lignes.append(f'    "{refuse.parameter}": "{refuse.reason}",')
    lignes += ["}", ""]

    return "\n".join(lignes)


def _chemin(resolution: Resolution) -> tuple[str, ...]:
    """Les paramètres de chemin de la liste, portée d'appel comprise.

    `scope` dit ce que l'utilisateur doit fournir en plus de la zone ; le
    runtime, lui, a besoin de la liste complète pour rendre le chemin.
    """
    depuis_le_chemin = [
        segment[1:-1]
        for segment in resolution.path.split("/")
        if segment.startswith("{") and segment.endswith("}")
    ]
    return tuple(depuis_le_chemin)
