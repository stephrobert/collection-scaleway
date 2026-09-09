"""L'IR ne doit pas dépendre de l'ordre des chemins du document.

C'est la règle 6 du dépôt : même contrat, mêmes fichiers, octet pour octet. Un
document dont on permute les chemins **est** le même contrat, et le parser
devait le prouver.

Il ne le prouvait pas. `_deref` fusionne les clés sœurs d'un `$ref` dans ce
qu'il rend, ce qui est juste pour lire un **champ** : sa description lui
appartient. Elle ne décrit pas le **type** pour autant, et un enum est un type,
partagé par tous ses porteurs. `scaleway.instance.v1.IpType` est décrit « IP
type to reserve » sur un site et « Should have no effect. » sur un autre : le
premier chemin parcouru gagnait, et l'IR changeait avec l'ordre du document.

Piste rapportée par l'agent d'audit dans #128, restée indéterminée une première
fois parce que ma sonde n'atteignait pas le mécanisme.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
import yaml

from generator.parser.openapi import parse_document
from generator.source.base import SpecDocument, VendoredSpecSource

SPECS = Path("specs/scaleway")


def _ir(produit: str, version: str, document: dict) -> str:
    service = parse_document(
        SpecDocument(
            product=produit,
            version=version,
            path=SPECS / f"{produit}.{version}.yml",
            document=document,
        )
    )
    return json.dumps(service.to_dict(), ensure_ascii=False, sort_keys=True)


@pytest.mark.parametrize(("produit", "version"), [("instance", "v1"), ("lb", "v1")])
def test_permuter_les_chemins_ne_change_pas_lir(produit: str, version: str) -> None:
    """Sur les contrats réels, et pas sur un cas fabriqué.

    Le défaut ne se voyait que sur un document où deux sites décrivent le même
    enum autrement, ce qu'un laboratoire n'aurait pas reproduit sans qu'on
    sache déjà quoi y mettre.
    """
    chemin = SPECS / f"{produit}.{version}.yml"
    document = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    assert document["paths"], "aucun chemin : le test ne mesure plus rien"

    reference = _ir(produit, version, document)
    for graine in range(5):
        routes = list(document["paths"].items())
        random.Random(graine).shuffle(routes)
        assert _ir(produit, version, {**document, "paths": dict(routes)}) == reference, (
            f"l'IR de {produit}.{version} change avec l'ordre des chemins (graine {graine})"
        )


def test_un_enum_ne_prend_pas_la_description_du_site_qui_le_reference() -> None:
    """La cause, prise à sa source plutôt qu'à son symptôme.

    Le champ, lui, garde la sienne : c'est elle qui décrit ce que **ce**
    paramètre attend, et c'est elle que la page publie.
    """
    service = parse_document(VendoredSpecSource(root=SPECS).load("instance", "v1"))

    ip_type = next(e for e in service.enums if e.name.endswith("IpType"))
    assert ip_type.description is None, "le schéma `IpType` ne porte aucune description"

    descriptions = {
        (operation.id, parametre.description)
        for operation in service.operations
        for parametre in operation.parameters
        if parametre.name == "type" and operation.id in {"CreateIp", "UpdateIp"}
    }
    assert ("CreateIp", "IP type to reserve (either 'routed_ipv4' or 'routed_ipv6').") in (
        descriptions
    )
    assert ("UpdateIp", "Should have no effect.") in descriptions


def test_un_enum_decrit_par_son_schema_garde_sa_description() -> None:
    """Le contre-exemple, sans lequel le correctif pourrait tout effacer.

    Aucun enum des contrats versionnés n'est décrit par son schéma aujourd'hui ;
    le cas se fabrique donc, et il est le seul de ce fichier à l'être.
    """
    document = {
        "openapi": "3.0.3",
        "info": {"title": "Sonde", "version": "v1"},
        "components": {
            "schemas": {
                "scaleway.sonde.v1.Etat": {
                    "type": "string",
                    "enum": ["a", "b"],
                    "description": "Celle du schéma, la seule qui vaille.",
                },
                "scaleway.sonde.v1.Chose": {
                    "type": "object",
                    "properties": {
                        "etat": {
                            "description": "Celle du champ, qui ne décrit que lui.",
                            "$ref": "#/components/schemas/scaleway.sonde.v1.Etat",
                        }
                    },
                },
            }
        },
        "paths": {
            "/sonde/v1/choses/{id}": {
                "get": {
                    "operationId": "GetChose",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/scaleway.sonde.v1.Chose"
                                    }
                                }
                            }
                        }
                    },
                }
            }
        },
    }
    service = parse_document(
        SpecDocument(product="sonde", version="v1", path=Path("sonde.v1.yml"), document=document)
    )

    etat = next(e for e in service.enums if e.name.endswith("Etat"))
    assert etat.description == "Celle du schéma, la seule qui vaille."
