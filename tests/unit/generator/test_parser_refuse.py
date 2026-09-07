"""Le parser refuse un contrat malformé, il ne casse pas dessus.

Un fuzzer du parser a trouvé **douze** défauts au premier passage, tous de la
même famille : une forme supposée sans être vérifiée. Aucun n'était théorique.
Une clé YAML déclarée sans valeur vaut `None` et pas `{}` ; un `$ref` peut
porter autre chose qu'une chaîne ; un `type` peut être un objet.

Ce qui rend ces défauts coûteux n'est pas le plantage, c'est **où** il sort. Un
`operationId` non textuel traversait tout le parsing et sortait au tri final,
sur un `TypeError: '<' not supported` qui ne nomme ni l'opération, ni le
fichier, ni le contrat. Un nom de paramètre non textuel cassait un `set`
construit trois fonctions plus loin.

Chaque cas ci-dessous est donc écrit deux fois : le parser doit **refuser**, et
son refus doit **nommer** ce qu'il refuse.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from generator.parser.openapi import ParseError, parse_document
from generator.source.base import SpecDocument


def _contrat(**remplacements: Any) -> dict[str, Any]:
    """Un contrat minimal et valide, dans lequel on remplace une pièce."""
    document: dict[str, Any] = {
        "info": {"title": "Widget API"},
        "paths": {
            "/widget/v1/things": {
                "get": {
                    "operationId": "ListThings",
                    "parameters": [{"name": "zone", "in": "path", "schema": {"type": "string"}}],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ListThingsResponse"}
                                }
                            }
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "ListThingsResponse": {
                    "type": "object",
                    "properties": {"things": {"type": "array", "items": {"type": "string"}}},
                }
            }
        },
    }
    document.update(remplacements)
    return document


def _parse(document: dict[str, Any]) -> Any:
    return parse_document(
        SpecDocument(product="widget", version="v1", path=Path("widget.v1.yml"), document=document)
    )


def test_le_contrat_de_reference_se_parse() -> None:
    """Sans lui, tous les tests ci-dessous passeraient pour la mauvaise raison.

    Un contrat de référence qui ne se parse pas rendrait chaque refus
    indiscernable d'un refus dû au contrat lui-même.
    """
    service = _parse(_contrat())
    assert [operation.id for operation in service.operations] == ["ListThings"]


@pytest.mark.parametrize(
    ("nom", "operation_id"),
    [("absent", None), ("liste", ["ListThings"]), ("vide", "")],
)
def test_un_identifiant_doperation_invalide_est_refuse(nom: str, operation_id: Any) -> None:
    """Il sert de clé de tri : le défaut sortait à la fin, sans rien nommer."""
    document = _contrat()
    operation = document["paths"]["/widget/v1/things"]["get"]
    if operation_id is None:
        del operation["operationId"]
    else:
        operation["operationId"] = operation_id

    with pytest.raises(ParseError) as erreur:
        _parse(document)
    assert "/widget/v1/things" in str(erreur.value)


def test_un_nom_de_parametre_invalide_est_refuse() -> None:
    """Il cassait un `set` construit trois fonctions plus loin."""
    document = _contrat()
    document["paths"]["/widget/v1/things"]["get"]["parameters"][0]["name"] = ["zone"]
    with pytest.raises(ParseError, match="ListThings"):
        _parse(document)


def test_un_emplacement_de_parametre_inconnu_est_refuse() -> None:
    """Un `ValueError` nu parlait de l'enum, pas du contrat."""
    document = _contrat()
    document["paths"]["/widget/v1/things"]["get"]["parameters"][0]["in"] = "nulle-part"
    with pytest.raises(ParseError) as erreur:
        _parse(document)
    assert "nulle-part" in str(erreur.value) and "zone" in str(erreur.value)


def test_une_reference_vers_un_non_schema_est_refusee() -> None:
    """`dict(target)` sortait en « dictionary update sequence », sans nommer la référence."""
    document = _contrat()
    document["components"]["schemas"]["ListThingsResponse"] = "une chaîne"
    with pytest.raises(ParseError, match="ListThingsResponse"):
        _parse(document)


@pytest.mark.parametrize(
    ("ou", "valeur"),
    [
        ("content", None),
        ("responses", None),
        ("parameters", None),
        # Pas seulement `None` : une clé peut aussi porter un scalaire. Une
        # garde qui ne testerait que `is not None` laisserait passer celui-ci,
        # et c'est ce que la mutation déclarée vérifie.
        ("content", "une chaîne"),
        ("responses", "une chaîne"),
    ],
)
def test_une_cle_declaree_sans_valeur_ne_fait_pas_planter(ou: str, valeur: Any) -> None:
    """En YAML, une clé vide vaut `None`, et le défaut d'un `.get` n'en protège pas.

    C'est la famille la plus nombreuse de ce que le premier passage de fuzzing
    a trouvé. `noeud.get("x", {})` protège de la clé **absente**, jamais de la
    clé déclarée sans rien dessous, et un document écrit à la main produit la
    seconde sans effort.
    """
    document = _contrat()
    operation = document["paths"]["/widget/v1/things"]["get"]
    if ou == "content":
        operation["responses"]["200"]["content"] = valeur
    else:
        operation[ou] = valeur

    service = _parse(document)
    assert [op.id for op in service.operations] == ["ListThings"]


@pytest.mark.parametrize(
    "declaration",
    [
        {"type": {"un": "objet"}},
        {"type": ["null"]},
        {"$ref": {"un": "objet"}},
        {"enum": None},
    ],
)
def test_un_type_que_le_parser_ne_sait_pas_lire_est_signale(declaration: dict[str, Any]) -> None:
    """Signalé dans les avertissements, jamais deviné ni tu.

    C'est la règle 3 du dépôt : ce que le contrat ne dit pas se dit dans les
    limites du rapport. Un `TypeError` ne le dit à personne.
    """
    document = _contrat()
    document["paths"]["/widget/v1/things"]["get"]["parameters"][0]["schema"] = declaration
    service = _parse(document)
    assert service.warnings, "un type illisible doit laisser une trace"


def test_une_operation_qui_nest_pas_un_mapping_est_ignoree_avec_sa_trace() -> None:
    document = _contrat()
    document["paths"]["/widget/v1/things"]["post"] = "une chaîne"
    service = _parse(document)
    assert [op.id for op in service.operations] == ["ListThings"]
    assert any("mapping" in avertissement for avertissement in service.warnings)


def test_une_description_qui_nest_pas_une_chaine_vaut_une_absence() -> None:
    """Une description n'est pas porteuse : elle ne doit pas faire tomber un produit.

    Le rapport compte déjà les paramètres qui n'en ont pas, et c'est là que le
    trou se voit.
    """
    document = _contrat()
    document["paths"]["/widget/v1/things"]["get"]["parameters"][0]["description"] = {"mdx": "..."}
    service = _parse(document)
    parametre = service.operations[0].parameters[0]
    assert parametre.description is None
