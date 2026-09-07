"""Ce que l'API interdit d'utiliser ensemble, le module le refuse aussi.

Le contrat du Load Balancer marque `email_config` et `webhook_config` d'un même
`x-one-of: config` : un abonné a une adresse ou un point d'entrée, jamais les
deux. Le module généré acceptait les deux, l'API répondait 400, et rien dans le
module ne le disait. Ni la documentation, ni l'`argument_spec`, ni
`ansible-test sanity`, qui n'a aucun moyen de le savoir : le défaut ne se voyait
qu'au premier playbook, sur un message de l'API.

La preuve qui compte est le **validateur d'Ansible**, pas une relecture de la
constante : c'est lui qui tournera chez l'utilisateur.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

COMMUNS = {"zone": "fr-par-1", "access_key": "SCW00000000000000000", "secret_key": "x"}


@pytest.fixture(scope="module")
def abonne(collection_root: Path) -> Any:
    """Le module de gestion d'un abonné, importé comme Ansible l'importe."""
    from ansible_collections.stephrobert.scaleway.plugins.modules import lb_subscriber

    return lb_subscriber


def _valider(module: Any, parametres: dict[str, Any]) -> Any:
    return ArgumentSpecValidator(
        module.ARGUMENT_SPEC, mutually_exclusive=module.MUTUALLY_EXCLUSIVE
    ).validate({**COMMUNS, **parametres})


def test_le_module_porte_la_contrainte_du_contrat(abonne: Any) -> None:
    """Le groupe vient du contrat, pas d'une liste écrite à la main."""
    assert abonne.MUTUALLY_EXCLUSIVE == [["email_config", "webhook_config"]]


def test_deux_configurations_ensemble_sont_refusees(abonne: Any) -> None:
    """Le défaut mesuré : le module les acceptait, l'API répondait 400."""
    resultat = _valider(
        abonne,
        {
            "subscriber_id": "11111111-1111-1111-1111-111111111111",
            "name": "alertes",
            "email_config": {"email": "ops@example.com"},
            "webhook_config": {"uri": "https://example.com/hook"},
        },
    )

    assert resultat.error_messages, "les deux configurations doivent être refusées"
    assert "mutually exclusive" in " ".join(resultat.error_messages)


def test_une_seule_configuration_passe(abonne: Any) -> None:
    """Le contre-exemple, sans lequel le test précédent passerait aussi sur un
    module qui refuserait tout."""
    resultat = _valider(
        abonne,
        {
            "subscriber_id": "11111111-1111-1111-1111-111111111111",
            "name": "alertes",
            "email_config": {"email": "ops@example.com"},
        },
    )

    assert resultat.error_messages == []


def test_aucune_configuration_passe(abonne: Any) -> None:
    """`mutually_exclusive` n'exige pas d'en fournir une.

    C'est `required_one_of` qui l'exigerait, et le contrat ne le déclare pas :
    le générateur ne l'invente donc pas. Un module qui exigerait un champ que
    l'API accepte d'omettre refuserait un playbook valide.
    """
    resultat = _valider(
        abonne,
        {"subscriber_id": "11111111-1111-1111-1111-111111111111", "name": "alertes"},
    )

    assert resultat.error_messages == []
