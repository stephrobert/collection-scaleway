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
    ambigues: Sequence[Resolution] = (),
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
            *_corps_de_lookup(resolution, classifications, indent=8),
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
        lignes += _refus_rendu(refuse.parameter, refuse.reason)
    lignes += ["}", ""]

    lignes += [
        "",
        "#: Ce qu'un nom désigne dans **plusieurs** produits, rangé par produit.",
        "#:",
        "#: Le nom seul ne tranche pas, donc le lookup refuse : rendre",
        "#: l'identifiant du mauvais produit est pire que ne rien rendre. Mais",
        "#: retirer la résolution punirait l'utilisateur pour notre nommage, alors",
        "#: elle est servie dès que l'appelant dit de quel produit il parle.",
        "AMBIGUOUS: dict[str, dict[str, ResourceLookup]] = {",
    ]
    par_parametre: dict[str, list[Resolution]] = {}
    for resolution in ambigues:
        par_parametre.setdefault(resolution.parameter, []).append(resolution)
    for parametre in sorted(par_parametre):
        lignes.append(f'    "{parametre}": {{')
        for resolution in sorted(par_parametre[parametre], key=lambda r: r.service):
            lignes += [
                f'        "{resolution.service}": ResourceLookup(',
                *_corps_de_lookup(resolution, classifications, indent=12),
                "        ),",
            ]
        lignes.append("    },")
    lignes += ["}", ""]

    return "\n".join(lignes)


#: La ligne qu'`ansible-test sanity` accepte dans un fichier publié. C'est elle
#: qui décide, pas une préférence de ce dépôt.
LIGNE_MAXIMALE = 160


def _refus_rendu(parametre: str, raison: str) -> list[str]:
    """Une entrée de refus, repliée quand sa raison ne tient pas sur la ligne.

    **Une raison fusionnée peut être longue.** `merge_refus` réunit celles de
    plusieurs produits, et deux raisons mises bout à bout dépassaient la ligne
    que le sanity accepte. Replier est la réponse ; tronquer ferait perdre
    exactement ce que ce champ existe pour dire, et exempter le fichier
    introduirait la première exemption de sanity du dépôt pour un défaut de mise
    en forme.

    La concaténation implicite de Python rend une seule chaîne : ce que le
    runtime lit ne change pas.
    """
    une_ligne = f'    "{parametre}": "{raison}",'
    if len(une_ligne) <= LIGNE_MAXIMALE:
        return [une_ligne]

    # Coupé aux espaces, donc jamais à l'intérieur d'un mot : une raison nomme
    # des identifiants, et les couper les rendrait introuvables.
    largeur = LIGNE_MAXIMALE - 16
    morceaux: list[str] = []
    courant = ""
    for mot in raison.split(" "):
        if courant and len(courant) + 1 + len(mot) > largeur:
            morceaux.append(courant + " ")
            courant = mot
        else:
            courant = f"{courant} {mot}" if courant else mot
    morceaux.append(courant)

    return [
        f'    "{parametre}": (',
        *[f'        "{morceau}"' for morceau in morceaux],
        "    ),",
    ]


def _corps_de_lookup(
    resolution: Resolution, classifications: Mapping[str, OperationKind], *, indent: int
) -> list[str]:
    """Les champs d'un `ResourceLookup`, à l'indentation demandée.

    Écrit une fois plutôt que deux : `RESOLUTIONS` et `AMBIGUOUS` portent la même
    structure, et deux copies d'un rendu finissent par diverger sur un champ que
    l'une gagne et l'autre pas.
    """
    marge = " " * indent
    return [
        f'{marge}parameter="{resolution.parameter}",',
        f'{marge}service="{resolution.service}",',
        f'{marge}schema="{resolution.schema}",',
        f"{marge}operation=Operation(",
        f'{marge}    id="{resolution.list_operation}",',
        f'{marge}    method="{resolution.http_method}",',
        f'{marge}    path="{resolution.path}",',
        f"{marge}    path_params={python_literal(_chemin(resolution), indent=indent + 4)},",
        f"{marge}    query_params={python_literal(resolution.query_params, indent=indent + 4)},",
        f'{marge}    payload_field="{resolution.payload_field}",',
        f"{marge}    is_list=True,",
        f"{marge}    page_param={python_literal(resolution.page_param)},",
        f"{marge}    per_page_param={python_literal(resolution.per_page_param)},",
        f'{marge}    retry="{_retry(resolution, classifications)}",',
        f"{marge}),",
        f"{marge}scope={python_literal(resolution.scope, indent=indent)},",
        f"{marge}filters_by_name={resolution.filters_by_name},",
    ]


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
