"""Ce qu'un nom permet de retrouver, et ce que le contrat ne permet pas.

La moitié de la collection réclame un identifiant qu'aucun humain ne connaît par
coeur. Le parcours actuel est d'appeler un module d'information, d'enregistrer
le résultat, d'y prendre un UUID et de le réinjecter. Ce module calcule ce qu'il
faut pour l'éviter : pour chaque paramètre d'identifiant, **l'unique opération
de liste qui rend l'objet portant cet identifiant**, la portée qu'elle exige, et
le champ qui porte les éléments.

## Pourquoi la jointure passe par le schéma de réponse

La tentation est de joindre sur la ressource dérivée. Mesuré sur `lb`, ça rate :
l'API expose un même objet par deux familles de chemins,

    POST /lb/v1/zones/{zone}/frontends/{frontend_id}/acls   créer
    GET  /lb/v1/zones/{zone}/frontends/{frontend_id}/acls   lister
    GET  /lb/v1/zones/{zone}/acls/{acl_id}                  lire

et la dérivation en fait deux ressources, `frontend_acl` et `acl`. Joindre sur
la ressource déclarerait `acl_id` non résoluble alors que le contrat sait le
résoudre. Le schéma de réponse, lui, est le même objet des deux côtés.

## Pourquoi la casse ne se devine pas

Le contrat porte `PrivateNIC` et `Ip` dans le même document. Une jointure
sensible à la casse ne rate pas seulement le rattachement : elle publie une
raison **fausse**, « aucun schéma nommé PrivateNic », là où le contrat en porte
un, sans champ `name`. Un refus mal motivé coûte plus cher qu'un refus.

## Ce qui n'est pas résoluble le reste, et le dit

Quatre objets des contrats versionnés ne portent pas de champ `name` : `Ip`,
`Route`, `PrivateNIC` et `SecurityGroupRule`. Il n'y a rien à chercher par nom,
et aucune heuristique ne comblera ça. Ces refus partent dans les limites du
rapport ; ils ne deviennent pas un contournement.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from generator.ir.models import ApiOperation, ApiService

#: Les paramètres qui ressemblent à un identifiant de ressource sans en être un :
#: ils désignent le compte, pas une chose qu'on cherche par son nom.
HORS_RESOLUTION = frozenset({"project_id", "organization_id"})

#: Les paramètres de chemin qui sont de la portée d'appel, pas de la portée
#: d'une ressource. Le lookup les reçoit comme n'importe quel module.
PORTEE_D_APPEL = frozenset({"zone", "region"})


@dataclass(frozen=True)
class Resolution:
    """Comment retrouver un identifiant depuis un nom, tel que le contrat le permet."""

    #: Le paramètre que l'utilisateur remplit, `backend_id`. C'est la clé, parce
    #: que c'est littéralement ce qu'il cherche à écrire.
    parameter: str
    #: Le service qui la porte, pour qu'un refus puisse nommer les deux camps.
    service: str
    #: L'objet du contrat qui porte l'identifiant et le nom.
    schema: str
    #: L'opération de liste, et de quoi l'exécuter sans rien redemander au contrat.
    list_operation: str
    path: str
    payload_field: str
    #: Ce que la liste exige en plus de la zone ou de la région, dans l'ordre du
    #: contrat : `('lb_id',)` pour un backend.
    scope: tuple[str, ...]
    #: L'API sait-elle filtrer elle-même sur le nom. Quand non, on liste et on
    #: filtre localement : le verdict est le même, le coût ne l'est pas.
    filters_by_name: bool
    page_param: str | None = None
    per_page_param: str | None = None


@dataclass(frozen=True)
class Refus:
    """Un identifiant que le contrat ne permet pas de résoudre, et pourquoi."""

    parameter: str
    reason: str


def _nom_court(schema: str | None) -> str:
    return (schema or "").rsplit(".", 1)[-1]


def _schema_rendu(operation: ApiOperation) -> str | None:
    """Le schéma des éléments rendus par une liste, ou None hors d'une liste."""
    return operation.response.payload_schema if operation.response is not None else None


def _camel(nom: str) -> str:
    return "".join(morceau.capitalize() for morceau in nom.split("_"))


def _listes_par_schema(service: ApiService) -> dict[str, list[ApiOperation]]:
    """Les opérations de liste, rangées par l'objet qu'elles rendent."""
    index: dict[str, list[ApiOperation]] = defaultdict(list)
    for operation in service.operations:
        reponse = operation.response
        if operation.http_method.value != "GET" or reponse is None or not reponse.is_list:
            continue
        index[_nom_court(reponse.payload_schema).lower()].append(operation)
    return index


def build_resolutions(
    service: ApiService,
    parameters: frozenset[str] | set[str],
) -> tuple[tuple[Resolution, ...], tuple[Refus, ...]]:
    """Rend ce qui est résoluble, et ce qui ne l'est pas **avec sa raison**.

    Jamais l'un sans l'autre : un identifiant qui disparaîtrait en silence de
    cette table serait un identifiant que l'utilisateur continue de recopier
    sans savoir pourquoi.
    """
    champs = {objet.name: {champ.name for champ in objet.fields} for objet in service.objects}
    index = _listes_par_schema(service)

    resolutions: list[Resolution] = []
    refus: list[Refus] = []

    for parameter in sorted(parameters):
        if parameter in HORS_RESOLUTION or not parameter.endswith("_id"):
            continue

        attendu = _camel(parameter[: -len("_id")])
        candidates = index.get(attendu.lower(), [])

        if not candidates:
            refus.append(
                Refus(
                    parameter,
                    f"aucun schéma nommé {attendu} n'est rendu par une opération de liste",
                )
            )
            continue

        # L'ordre des refus n'est pas cosmétique : on nomme d'abord ce qui
        # resterait bloquant une fois l'autre raison levée. Une portée ambiguë se
        # tranche par un override ; un objet sans `name` ne se tranche pas.
        nommables = [
            operation
            for operation in candidates
            if "name" in champs.get(_schema_rendu(operation) or "", set())
        ]
        if not nommables:
            reel = _nom_court(_schema_rendu(candidates[0]))
            refus.append(Refus(parameter, f"{reel} ne porte pas de champ name dans le contrat"))
            continue

        if len(nommables) > 1:
            noms = ", ".join(sorted(operation.id for operation in nommables))
            refus.append(
                Refus(
                    parameter,
                    f"{len(nommables)} listes rendent {attendu} ({noms}) : la portée est ambiguë",
                )
            )
            continue

        operation = nommables[0]
        reponse = operation.response
        assert reponse is not None  # garanti par _listes_par_schema
        if reponse.payload_field is None:
            refus.append(
                Refus(parameter, f"{operation.id} ne déclare pas quel champ porte les éléments")
            )
            continue

        resolutions.append(
            Resolution(
                parameter=parameter,
                service=service.name,
                schema=reponse.payload_schema or "",
                list_operation=operation.id,
                path=operation.path,
                payload_field=reponse.payload_field,
                scope=tuple(
                    p.name
                    for p in operation.parameters
                    if p.location.value == "path" and p.name not in PORTEE_D_APPEL
                ),
                filters_by_name=any(
                    p.name == "name" and p.location.value == "query" for p in operation.parameters
                ),
                page_param=operation.pagination.page_param if operation.pagination else None,
                per_page_param=(
                    operation.pagination.per_page_param if operation.pagination else None
                ),
            )
        )

    return tuple(resolutions), tuple(refus)


def merge_resolutions(
    par_service: list[tuple[Resolution, ...]],
) -> tuple[tuple[Resolution, ...], tuple[Refus, ...]]:
    """Fond les tables des produits, et **refuse** un identifiant revendiqué deux fois.

    `ip_id` existe dans `instance` et dans `lb`, et ces deux `ip` ne sont pas la
    même chose. Aucun des deux n'est résoluble aujourd'hui, faute de champ
    `name` ; le jour où l'un le devient, choisir en silence donnerait à
    l'utilisateur l'identifiant du mauvais produit, ce qui est pire que de ne
    rien lui donner.
    """
    par_parametre: dict[str, list[Resolution]] = defaultdict(list)
    for table in par_service:
        for resolution in table:
            par_parametre[resolution.parameter].append(resolution)

    gardees: list[Resolution] = []
    refus: list[Refus] = []
    for parameter in sorted(par_parametre):
        candidates = par_parametre[parameter]
        if len(candidates) == 1:
            gardees.append(candidates[0])
            continue
        services = ", ".join(sorted(c.service for c in candidates))
        refus.append(
            Refus(
                parameter,
                f"revendiqué par {len(candidates)} produits ({services}) : "
                "lequel n'est pas décidable",
            )
        )
    return tuple(gardees), tuple(refus)
