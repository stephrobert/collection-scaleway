"""Une réponse dont l'enveloppe porte une map, et ce que la page en dit.

Des pages livrées affirmaient « The API contract names no payload field for
this operation », et le contrat nomme pourtant `servers` ou `volumes`.
`test_les_trois_pages_en_map_publient_ce_quelles_contiennent` les nomme. Le
parser ne traitait que deux formes d'enveloppe, un tableau et un `$ref` : une
propriété `type: object` avec `additionalProperties` ne correspondait ni à
l'une ni à l'autre, et le champ porteur restait `None`.

La page publiait donc une affirmation sur le contrat qui était le contraire de
ce qu'il dit, et `contains: {}` avec elle.
"""

from __future__ import annotations

from pathlib import Path

from generator.parser.openapi import parse_document
from generator.source.base import SpecDocument


def _parse(schemas: dict, enveloppe: str) -> object:  # type: ignore[no-untyped-def]
    document = {
        "openapi": "3.0.3",
        "info": {"title": "Sonde", "version": "v1"},
        "components": {"schemas": schemas},
        "paths": {
            "/sonde/v1/choses": {
                "get": {
                    "operationId": "ListChoses",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": f"#/components/schemas/{enveloppe}"}
                                }
                            }
                        }
                    },
                }
            }
        },
    }
    return parse_document(
        SpecDocument(product="sonde", version="v1", path=Path("sonde.v1.yml"), document=document)
    )


CHOSE = {"scaleway.sonde.v1.Chose": {"type": "object", "properties": {"id": {"type": "string"}}}}


def _map(valeur: dict) -> dict:
    """L'enveloppe telle que Scaleway l'écrit : gabarit entre chevrons."""
    return {
        "scaleway.sonde.v1.ListChosesResponse": {
            "type": "object",
            "properties": {
                "choses": {
                    "type": "object",
                    "properties": {"<choseKey>": valeur},
                    "additionalProperties": True,
                }
            },
        },
        **CHOSE,
    }


def test_une_enveloppe_en_map_nomme_son_champ_porteur() -> None:
    """Le défaut exact : le contrat nomme `choses`, et l'IR portait `None`."""
    service = _parse(
        _map({"$ref": "#/components/schemas/scaleway.sonde.v1.Chose"}),
        "scaleway.sonde.v1.ListChosesResponse",
    )
    reponse = service.operations[0].response

    assert reponse.payload_field == "choses"
    assert reponse.payload_schema == "scaleway.sonde.v1.Chose"


def test_une_map_nest_pas_une_liste() -> None:
    """Elle est indexée par des clés, pas parcourue par rang.

    Le confondre ferait paginer un module d'information sur une réponse qui
    n'a pas de pages, et rendre une liste là où l'API rend un dictionnaire.
    """
    service = _parse(
        _map({"$ref": "#/components/schemas/scaleway.sonde.v1.Chose"}),
        "scaleway.sonde.v1.ListChosesResponse",
    )

    assert service.operations[0].response.is_list is False


def test_une_map_de_scalaires_nomme_le_champ_sans_inventer_un_schema() -> None:
    """`Dashboard.servers_by_types` compte des entiers : il n'y a rien à nommer.

    Rendre un schéma ici serait en inventer un ; ne pas nommer le champ serait
    répéter le défaut. La page dira `type: dict` sans prétendre décrire ce
    qu'on y trouve.
    """
    service = _parse(_map({"type": "integer"}), "scaleway.sonde.v1.ListChosesResponse")
    reponse = service.operations[0].response

    assert reponse.payload_field == "choses"
    assert reponse.payload_schema is None


def test_une_map_sans_cle_de_gabarit_nomme_quand_meme_le_champ() -> None:
    """La convention des chevrons est celle de Scaleway, pas celle d'OpenAPI.

    Un contrat qui ne la suivrait pas ne doit pas faire perdre le champ
    porteur, qui lui est déclaré par OpenAPI seul.
    """
    schemas = {
        "scaleway.sonde.v1.ListChosesResponse": {
            "type": "object",
            "properties": {"choses": {"type": "object", "additionalProperties": True}},
        },
        **CHOSE,
    }
    reponse = _parse(schemas, "scaleway.sonde.v1.ListChosesResponse").operations[0].response

    assert reponse.payload_field == "choses"
    assert reponse.payload_schema is None


def test_une_enveloppe_en_tableau_reste_une_liste() -> None:
    """Le contre-exemple, sans lequel la branche map pourrait tout absorber."""
    schemas = {
        "scaleway.sonde.v1.ListChosesResponse": {
            "type": "object",
            "properties": {
                "choses": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/scaleway.sonde.v1.Chose"},
                }
            },
        },
        **CHOSE,
    }
    reponse = _parse(schemas, "scaleway.sonde.v1.ListChosesResponse").operations[0].response

    assert reponse.payload_field == "choses"
    assert reponse.payload_schema == "scaleway.sonde.v1.Chose"
    assert reponse.is_list is True


def test_une_ressource_rendue_telle_quelle_na_toujours_pas_de_champ_porteur() -> None:
    """L'autre contre-exemple, et celui qui garde la phrase là où elle est vraie.

    `GetBackend` rend un `Backend` sans enveloppe : la page a raison d'y écrire
    que le contrat ne nomme aucun champ porteur, et le correctif ne doit pas
    le lui faire dire à tort.
    """
    reponse = _parse(CHOSE, "scaleway.sonde.v1.Chose").operations[0].response

    assert reponse.payload_field is None
    assert reponse.payload_schema == "scaleway.sonde.v1.Chose"


# --- ce que les pages livrées publient ---------------------------------------


def test_aucune_page_livree_ne_ment_sur_le_champ_porteur() -> None:
    """La phrase ne doit sortir que sur la clé de repli, jamais sur une autre.

    Le seul test du fichier qui regarde ce qui est livré, et c'est voulu : il
    dit l'état du dépôt, là où les autres prouvent que la règle décide bien.

    Un module peut légitimement porter les deux : `result` pour une lecture
    unitaire que le contrat rend sans enveloppe, et une clé nommée pour la
    liste qui en a une. Ce qui serait faux, c'est que la phrase décrive une
    clé que le contrat nomme.
    """
    import yaml

    modules = Path("ansible_collections/stephrobert/scaleway/plugins/modules")
    PHRASE = "The API contract names no payload field"
    pages = sorted(modules.glob("*_info.py"))
    assert pages, "aucune page examinée : le test ne mesure plus rien"

    menteuses = []
    porteuses = 0
    for chemin in pages:
        texte = chemin.read_text(encoding="utf-8")
        if PHRASE not in texte:
            continue
        porteuses += 1
        retour = yaml.safe_load(texte.split('RETURN = r"""', 1)[1].split('"""', 1)[0]) or {}
        for cle, valeur in retour.items():
            decrit = " ".join(valeur.get("description") or ())
            if PHRASE in decrit and cle != "result":
                menteuses.append(f"{chemin.name} : la phrase décrit `{cle}`, que le contrat nomme")

    assert porteuses, "la phrase a disparu partout : le test ne mesure plus rien"
    assert menteuses == [], "\n".join(menteuses)


def test_les_trois_pages_en_map_publient_ce_quelles_contiennent() -> None:
    """Le cas de l'issue, mesuré sur les pages elles-mêmes.

    `contains: {}` était le corollaire du champ porteur perdu : la page nommait
    une clé sans dire ce qu'on y trouve.
    """
    import yaml

    modules = Path("ansible_collections/stephrobert/scaleway/plugins/modules")
    attendus = {
        "instance_server_type_info.py": "servers",
        "instance_volume_type_info.py": "volumes",
        "instance_server_type_availability_info.py": "servers",
    }
    for nom, cle in attendus.items():
        texte = (modules / nom).read_text(encoding="utf-8")
        retour = yaml.safe_load(texte.split('RETURN = r"""', 1)[1].split('"""', 1)[0]) or {}

        assert cle in retour, f"{nom} ne publie pas `{cle}`"
        assert retour[cle]["type"] == "dict", f"{nom} : une map n'est pas une liste"
        assert retour[cle].get("contains"), f"{nom} : `{cle}` ne dit pas ce qu'il contient"
