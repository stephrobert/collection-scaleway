"""Une attente d'état sur une ressource que l'override renomme.

L'IR porte la ressource **déduite du chemin** ; le plan la corrige quand le
chemin la nomme mal, et cette correction ne redescend pas dans
`service.operations`. La garde qui vérifie les états attendus cherchait donc la
lecture unitaire sous le **nouveau** nom dans un IR qui porte l'**ancien** : elle
ne trouvait rien, et accusait le contrat de ne pas déclarer ce qu'il déclare.

Le défaut était latent : aucun override d'attente n'existe sur un produit
renommé, donc rien ne rougissait. Ces tests le reproduisent sur le contrat de
laboratoire, où le renommage est explicite plutôt que subi.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generator.ansible.collection import Collection
from generator.ansible.models import UnreachableState, build_module_spec
from generator.ir.models import ApiService
from generator.overrides.loader import OperationOverride, OverrideSet, WaitOverride
from generator.plan import plan_service

COLLECTION = Collection(
    namespace="stephrobert",
    name="scaleway",
    version="0.1.0",
    path=Path("ansible_collections/stephrobert/scaleway"),
    authors=("Quelqu'un (@quelquun)",),
)


def _overrides(service: ApiService, *, renommer: str | None, etats: dict[str, str]) -> OverrideSet:
    """Une attente sur l'action, et le renommage de toutes les opérations.

    Le renommage porte sur **toutes** les opérations de la ressource, comme le
    fait l'override réel du Load Balancer : renommer la seule action laisserait
    la lecture unitaire sous l'ancien nom, et le test passerait pour la mauvaise
    raison.
    """
    operations: dict[str, OperationOverride] = {}
    for operation in service.operations:
        if operation.resource != "widget":
            continue
        attente = (
            WaitOverride(field="state", states=etats, reason="essai")
            if operation.id == "WidgetAction"
            else None
        )
        if renommer is None and attente is None:
            continue
        operations[operation.key] = OperationOverride(
            key=operation.key,
            resource=renommer,
            wait=attente,
            reason="essai",
        )
    return OverrideSet(source=None, operations=operations)


def _module_daction(service: ApiService, overrides: OverrideSet):  # type: ignore[no-untyped-def]
    plan = plan_service(service, overrides)
    nom = next(nom for nom in plan.modules() if nom.endswith("_action"))
    return build_module_spec(nom, plan.modules()[nom], plan.service, COLLECTION, plan.overrides)


def test_une_attente_sur_une_ressource_renommee_construit_son_module(
    widget_service: ApiService,
) -> None:
    """Le cas que l'issue reproduit, et que la garde refusait à tort."""
    overrides = _overrides(widget_service, renommer="gadget", etats={"poweron": "running"})

    spec = _module_daction(widget_service, overrides)

    assert spec.wait_states == (("poweron", "running"),)
    assert spec.state_field == "state"
    assert spec.read_operation is not None, "la lecture unitaire doit être trouvée"


def test_une_attente_sur_une_ressource_non_renommee_marche_toujours(
    widget_service: ApiService,
) -> None:
    """Le contre-exemple : le correctif ne doit pas ne marcher que renommé."""
    overrides = _overrides(widget_service, renommer=None, etats={"poweron": "running"})

    spec = _module_daction(widget_service, overrides)

    assert spec.wait_states == (("poweron", "running"),)


def test_un_etat_que_le_contrat_ne_declare_pas_est_toujours_refuse(
    widget_service: ApiService,
) -> None:
    """La raison d'être de la garde, qui ne doit pas disparaître avec son défaut.

    `stop_in_place` attendait `stopped` alors que le contrat déclare `stopped in
    place`, un état distinct : le module attendait un état jamais atteint et
    échouait après `wait_timeout` sur une ressource qui avait pourtant changé.
    """
    overrides = _overrides(widget_service, renommer="gadget", etats={"poweron": "demarre"})

    with pytest.raises(UnreachableState, match="demarre"):
        _module_daction(widget_service, overrides)


def test_le_refus_nomme_les_etats_que_le_contrat_declare(
    widget_service: ApiService,
) -> None:
    """Un refus qui ne dit pas ce qui existe oblige à ouvrir le contrat.

    C'est aussi ce qui prouve que la lecture unitaire a bien été trouvée : sans
    elle, le message parlerait de schéma introuvable, pas d'états.
    """
    overrides = _overrides(widget_service, renommer="gadget", etats={"poweron": "demarre"})

    with pytest.raises(UnreachableState) as erreur:
        _module_daction(widget_service, overrides)

    assert "running" in str(erreur.value)
    assert "stopped" in str(erreur.value)
