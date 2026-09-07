"""Un outil qui prouve la couverture du parser ne doit pas la sous-décrire.

`parser_coverage` regroupait `allOf`, `oneOf` et `anyOf` sous une ligne, et les
qualifiait toutes de « non géré ». C'était faux depuis ADR-008 : le parser
traduit `oneOf: [T, null]`, en tire le type utile et porte la nullabilité, et
c'est ce qui a permis à `lb_subscriber` d'exister. La porte d'admission
consommait ce compte, et faisait payer aux deux produits un prix qui n'existait
pas.

Une preuve pessimiste est fausse au même titre qu'une preuve optimiste. Ces
tests portent sur la séparation des formes, et sur ce que la porte en fait.

**Ce que l'issue affirmait, et ce qui est mesuré.** L'issue disait que le
contrat de laboratoire déclare les deux formes de `oneOf`. Il n'en déclare
qu'une, la forme optionnelle : l'union de formes est construite ici, dans un
document réduit, parce qu'aucun contrat versionné ne l'emploie et que le parser
la refuse.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import admission
import parser_coverage
import pytest

from generator.parser.openapi import parse_document
from generator.source.base import SpecDocument

REPO_ROOT = Path(__file__).resolve().parents[3]
WIDGET_INPUT = REPO_ROOT / "tests" / "fixtures" / "widget" / "input"

FORMES = ("allOf", "oneOf [T, null]", "oneOf union réelle", "anyOf", "x-one-of")


def _lignes(produit: str, version: str, racine: Path) -> dict[str, tuple[int, str]]:
    _, lignes = parser_coverage.relever(produit, version, racine=racine)
    return {nom: (compte, etat) for nom, compte, etat in lignes}


def _document_avec_une_union() -> dict[str, Any]:
    """Un contrat réduit dont le seul `oneOf` est une union de deux formes."""
    return {
        "openapi": "3.1.0",
        "paths": {
            "/widget/v1/zones/{zone}/widgets": {
                "post": {
                    "operationId": "CreateWidget",
                    "parameters": [
                        {
                            "name": "zone",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "target": {
                                            "oneOf": [
                                                {"type": "string"},
                                                {"type": "integer"},
                                            ]
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }


# --- les formes de oneOf, séparées ----------------------------------------


def test_un_oneof_avec_null_est_compte_comme_traduit() -> None:
    """La forme optionnelle n'est plus « non géré » : elle est traduite, et le
    compte le dit avec son état."""
    lignes = _lignes("widget", "v1", WIDGET_INPUT)

    compte, etat = lignes["oneOf [T, null]"]
    assert compte == 2
    assert not etat.startswith("non")
    assert lignes["oneOf union réelle"][0] == 0


def test_x_one_of_est_compte_comme_traduit() -> None:
    """`x-one-of` devient `mutually_exclusive` (ADR-008), et se compte à part."""
    compte, etat = _lignes("widget", "v1", WIDGET_INPUT)["x-one-of"]

    assert compte == 2
    assert "mutually_exclusive" in etat


def test_une_union_reelle_est_comptee_a_part_et_le_parser_la_signale() -> None:
    """Le seul `oneOf` qui produirait un `UNKNOWN`, donc le seul dont la
    présence dans un contrat neuf serait une mauvaise nouvelle.

    Le compte du script et l'avertissement du parser sont deux lecteurs du même
    critère : ce test les tient ensemble, pour qu'ils ne divergent pas au
    premier contrat malformé.
    """
    document = _document_avec_une_union()

    _, lignes = parser_coverage.compter(document)
    comptes = {nom: (compte, etat) for nom, compte, etat in lignes}
    service = parse_document(
        SpecDocument(product="widget", version="v1", path=Path("widget.v1.yml"), document=document)
    )
    signalees = [w for w in service.warnings if "union non traduite" in w]

    assert comptes["oneOf union réelle"][0] == 1
    assert comptes["oneOf union réelle"][1].startswith("non")
    assert comptes["oneOf [T, null]"][0] == 0
    assert len(signalees) == 1


@pytest.mark.parametrize(("produit", "version"), [("instance", "v1"), ("lb", "v1")])
def test_les_contrats_livres_comptent_chaque_forme_separement(produit: str, version: str) -> None:
    """Sur les deux contrats, les cinq formes sortent chacune sur sa ligne."""
    lignes = _lignes(produit, version, parser_coverage.SPEC_ROOT)

    assert all(forme in lignes for forme in FORMES)
    assert "allOf / oneOf / anyOf" not in lignes


# --- ce que la porte d'admission en fait ------------------------------------


def test_la_porte_ne_fait_pas_payer_une_construction_que_le_parser_traduit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le contrat de laboratoire porte des `oneOf: [T, null]` et des `x-one-of` ;
    aucun des deux n'entre au prix d'admission."""
    relever = parser_coverage.relever
    monkeypatch.setattr(parser_coverage, "relever", lambda p, v: relever(p, v, racine=WIDGET_INPUT))

    etape = admission.etape_syntaxe("widget", "v1")

    assert "oneOf [T, null]" not in etape.detail
    assert "x-one-of" not in etape.detail


def test_la_porte_fait_payer_une_union_reelle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le contre-exemple, sans lequel le test précédent passerait aussi sur une
    porte qui ne compterait plus rien."""
    monkeypatch.setattr(
        parser_coverage,
        "relever",
        lambda _p, _v: parser_coverage.compter(_document_avec_une_union()),
    )

    etape = admission.etape_syntaxe("widget", "v1")

    assert etape.tenue is False
    assert "oneOf union réelle" in etape.detail
