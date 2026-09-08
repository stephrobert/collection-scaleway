"""Les `parameters` qu'un chemin déclare pour toutes ses opérations.

OpenAPI 3.0 §4.7.9.1 autorise un `parameters` au niveau du chemin, et dit qu'il
s'applique à chaque opération qui s'y trouve. Le parser ne lisait que celui de
l'opération : un contrat qui déclare `{zone}` et `{id}` une fois pour tout le
chemin produisait une opération **sans aucun paramètre**, donc un module dont
le chemin gardait ses accolades, et rien ne le signalait.

Rapporté par l'agent d'audit, reproduit ici avant d'être corrigé (#128).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from generator.parser.openapi import parse_document
from generator.source.base import SpecDocument

REPONSE = {
    "200": {
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/scaleway.sonde.v1.Chose"}}
        }
    }
}


def _parse(paths: dict) -> object:  # type: ignore[no-untyped-def]
    document = {
        "openapi": "3.0.3",
        "info": {"title": "Sonde", "version": "v1"},
        "components": {
            "schemas": {
                "scaleway.sonde.v1.Chose": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                }
            }
        },
        "paths": paths,
    }
    return parse_document(
        SpecDocument(product="sonde", version="v1", path=Path("sonde.v1.yml"), document=document)
    )


def _parametre(nom: str, emplacement: str = "path", description: str | None = None) -> dict:
    declaration: dict = {
        "name": nom,
        "in": emplacement,
        "required": emplacement == "path",
        "schema": {"type": "string"},
    }
    if description:
        declaration["description"] = description
    return declaration


def test_un_parametre_declare_par_le_chemin_arrive_sur_loperation() -> None:
    """Le cas que l'audit rapporte, et que le parser perdait en silence."""
    service = _parse(
        {
            "/sonde/v1/zones/{zone}/choses/{chose_id}": {
                "parameters": [_parametre("zone"), _parametre("chose_id")],
                "get": {"operationId": "GetChose", "responses": REPONSE},
            }
        }
    )

    lus = [p.name for p in service.operations[0].parameters]

    assert lus == ["zone", "chose_id"]


def test_loperation_gagne_sur_le_chemin() -> None:
    """§4.7.9.1 : un paramètre de l'opération remplace celui du chemin.

    L'inverse écraserait une précision locale par une valeur générale, ce qui
    est le sens même d'une redéclaration.
    """
    service = _parse(
        {
            "/sonde/v1/choses/{chose_id}": {
                "parameters": [_parametre("chose_id", description="celle du chemin")],
                "get": {
                    "operationId": "GetChose",
                    "parameters": [_parametre("chose_id", description="celle de l'opération")],
                    "responses": REPONSE,
                },
            }
        }
    )

    parametres = service.operations[0].parameters

    assert len(parametres) == 1, "le paramètre ne doit pas apparaître deux fois"
    assert parametres[0].description == "celle de l'opération"


def test_le_meme_nom_a_un_autre_emplacement_ne_se_recouvre_pas() -> None:
    """L'identité d'un paramètre est son nom **et** son emplacement.

    Le contre-exemple du test précédent : recouvrir sur le seul nom ferait
    disparaître un filtre de requête parce qu'un segment de chemin porte le
    même mot.
    """
    service = _parse(
        {
            "/sonde/v1/choses/{chose_id}": {
                "parameters": [_parametre("chose_id")],
                "get": {
                    "operationId": "GetChose",
                    "parameters": [_parametre("chose_id", emplacement="query")],
                    "responses": REPONSE,
                },
            }
        }
    )

    emplacements = sorted(p.location.value for p in service.operations[0].parameters)

    assert emplacements == ["path", "query"]


def test_un_parameters_de_chemin_qui_nest_pas_une_liste_est_signale() -> None:
    """Le générateur ne devine pas, et ne se tait pas non plus."""
    service = _parse(
        {
            "/sonde/v1/choses/{chose_id}": {
                "parameters": {"name": "chose_id"},
                "get": {"operationId": "GetChose", "responses": REPONSE},
            }
        }
    )

    assert any("`parameters` du chemin" in avertissement for avertissement in service.warnings)


def test_aucun_contrat_versionne_ne_declare_de_parametre_partage() -> None:
    """Ce que le correctif corrige est **latent**, et ce test porte ce fait.

    Le jour où un contrat s'en servira, ce test rougira et dira que le cas est
    devenu réel : la correction sera déjà là, et le compte cessera d'être zéro.
    """
    racines = (Path("specs/scaleway"), Path("specs/scaleway/suivis"))
    contrats = [chemin for racine in racines if racine.is_dir() for chemin in racine.glob("*.yml")]
    assert contrats, "aucun contrat examiné : le test ne mesure plus rien"

    porteurs = [
        f"{chemin.name}:{route}"
        for chemin in contrats
        for route, item in (
            yaml.safe_load(chemin.read_text(encoding="utf-8")).get("paths") or {}
        ).items()
        if isinstance(item, dict) and "parameters" in item
    ]

    assert porteurs == []
