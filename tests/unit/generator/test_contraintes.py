"""Les contraintes que le contrat déclare, portées jusqu'au module.

Le parser voyait `x-one-of` et le laissait tomber, avec un commentaire disant
que c'était un travail à part. Résultat : `lb_subscriber` acceptait
`email_config` **et** `webhook_config`, l'API répondait 400, et rien dans la
chaîne ne le disait. Le défaut ne se voyait qu'au premier playbook.

Ces tests portent sur le contrat de laboratoire, pas sur Instance : ils ne
doivent pas rougir le jour où Scaleway ajoute un serveur.
"""

from __future__ import annotations

import pytest

from generator.ir.enums import ApiType, HTTPMethod, ParameterLocation, Scope
from generator.ir.models import ApiOperation, ApiParameter, ApiService


def _parametre(nom: str, groupe: str | None = None, nullable: bool = False) -> ApiParameter:
    return ApiParameter(
        name=nom,
        type=ApiType.STRING,
        required=False,
        location=ParameterLocation.BODY,
        one_of_group=groupe,
        nullable=nullable,
    )


def _operation(*parametres: ApiParameter) -> ApiOperation:
    return ApiOperation(
        id="UpdateWidget",
        service="widget",
        version="v1",
        resource="widget",
        http_method=HTTPMethod.PUT,
        path="/widget/v1/widgets/{widget_id}",
        scope=Scope.ZONE,
        parameters=parametres,
    )


# --- ce que le parser lit du contrat --------------------------------------


def test_le_groupe_dexclusion_du_contrat_est_conserve(widget_service: ApiService) -> None:
    """`x-one-of` nomme le groupe auquel un champ appartient.

    Sans lui, le module accepte deux paramètres que l'API interdit ensemble, et
    `ansible-test sanity` n'a aucun moyen de le savoir.
    """
    operation = widget_service.operation("UpdateWidget")

    assert operation.mutually_exclusive == (("email_config", "webhook_config"),)


def test_un_champ_effacable_est_signale_comme_tel(widget_service: ApiService) -> None:
    """`oneOf: [X, null]` dit « un X, ou rien ».

    Le parser réduisait le champ à son type non nul et perdait l'information.
    Un champ effaçable et un champ absent ne sont pas la même demande, et le
    générateur ne sait pas encore les distinguer : le fait est porté pour être
    compté avant d'être traité.
    """
    operation = widget_service.operation("UpdateWidget")
    config = operation.parameter("email_config")

    assert config is not None
    assert config.nullable is True
    assert config.type is ApiType.OBJECT, "le type utile ne doit pas être perdu"


def test_la_forme_3_1_dit_la_meme_chose(widget_service: ApiService) -> None:
    """`type: [string, "null"]` est l'autre écriture autorisée.

    Les deux formes cohabitent dans les contrats réels. N'en reconnaître qu'une
    ferait dépendre le compte de la façon dont l'amont a écrit son document.
    """
    jeton = widget_service.operation("UpdateWidget").parameter("secret_token")

    assert jeton is not None
    assert jeton.nullable is True
    assert jeton.type is ApiType.STRING


def test_le_document_est_compte_pour_ce_quil_porte(widget_service: ApiService) -> None:
    """Une absence mesurée n'est pas une absence déclarée.

    Le rapport annonce les contraintes que le contrat ne porte pas. Écrire
    cette liste à la main resterait vrai à l'écran et faux dans le document le
    jour où l'amont ajoute la contrainte, et le paramètre passerait sans elle.
    """
    comptes = dict(widget_service.constraint_keywords)

    assert comptes["x-one-of"] == 2, "les deux membres du groupe sont comptés"
    assert comptes["maxLength"] == 0, "le contrat n'en déclare pas, et on l'a vérifié"


# --- ce que l'IR en fait ---------------------------------------------------


def test_un_groupe_dun_seul_membre_nexclut_rien() -> None:
    """Ansible refuse de charger un `mutually_exclusive` à un élément.

    Le cas se produit : un corps de requête peut ne reprendre qu'un champ d'un
    groupe déclaré sur le schéma complet.
    """
    operation = _operation(_parametre("email_config", groupe="config"))

    assert operation.mutually_exclusive == ()


def test_deux_groupes_sortent_dans_un_ordre_stable() -> None:
    """La génération est déterministe, donc le regroupement doit l'être.

    Un dictionnaire parcouru dans l'ordre d'insertion d'un YAML suffit à casser
    la propriété, et le golden le dirait, tard.
    """
    operation = _operation(
        _parametre("zzz", groupe="beta"),
        _parametre("aaa", groupe="alpha"),
        _parametre("bbb", groupe="alpha"),
        _parametre("yyy", groupe="beta"),
    )

    assert operation.mutually_exclusive == (("aaa", "bbb"), ("zzz", "yyy"))


@pytest.mark.parametrize("marqueur", [123, {"groupe": "config"}, ["config"], ""])
def test_un_marqueur_qui_nest_pas_un_nom_est_ignore(marqueur: object) -> None:
    """`x-one-of` est une extension, et personne ne la valide en amont.

    Un objet glissé là produirait un `mutually_exclusive` illisible par
    Ansible, donc un module qui ne se charge plus du tout : le refus vaut mieux
    que la recopie.
    """
    from generator.parser.openapi import _groupe_dexclusion

    assert _groupe_dexclusion({"x-one-of": marqueur}) is None
