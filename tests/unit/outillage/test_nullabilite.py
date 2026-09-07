"""Ce qu'un module ne sait pas dire : « efface ce champ ».

Le contrat marque un champ effaçable, et le runtime construit sa demande depuis
les valeurs qui ne sont pas `None` :

```yaml
description: null        # « efface la description »
# description absente    # « n'y touche pas »
```

Les deux produisent la même requête. Un playbook qui veut effacer ne le peut
pas, et le module rend `ok` sans avoir rien effacé.

Ce relevé compte et nomme les champs concernés. Il ne refuse rien : compter
n'est pas refuser, et une porte bloquerait la collection sur une limite connue.
Ces tests portent donc sur ce qu'il **compte**, et sur ce qu'il écarte.
"""

from __future__ import annotations

import nullabilite
import pytest

from generator.ir.enums import ApiType, HTTPMethod, OperationKind, ParameterLocation, Scope
from generator.ir.models import ApiOperation, ApiParameter, ApiService
from generator.plan import OperationPlan, ProductPlan


def _parametre(nom: str, nullable: bool, ou: ParameterLocation) -> ApiParameter:
    return ApiParameter(
        name=nom, type=ApiType.STRING, required=False, location=ou, nullable=nullable
    )


def _plan(module: str | None, *parametres: ApiParameter) -> ProductPlan:
    operation = ApiOperation(
        id="UpdateWidget",
        service="widget",
        version="v1",
        resource="widget",
        http_method=HTTPMethod.PUT,
        path="/widget/v1/widgets/{widget_id}",
        scope=Scope.ZONE,
        parameters=parametres,
    )
    service = ApiService(name="widget", version="v1", operations=(operation,))
    from generator.classifier.rules import Classification
    from generator.ir.enums import GenerationMode

    item = OperationPlan(
        operation=operation,
        classification=Classification(
            key=operation.key,
            kind=OperationKind.MANAGE,
            mode=GenerationMode.AUTO,
            reason="fixture de test",
        ),
        module=module,
        resource="widget",
    )
    from generator.overrides.loader import OverrideSet

    return ProductPlan(
        service=service,
        operations=(item,),
        overrides=OverrideSet(source=None),
        orphan_overrides=(),
    )


def test_un_champ_de_corps_effacable_est_compte() -> None:
    """Le cas de l'issue, réduit à sa forme minimale."""
    champs = nullabilite.effacables(
        _plan("widget_widget", _parametre("description", True, ParameterLocation.BODY))
    )

    assert [champ.champ for champ in champs] == ["description"]


def test_un_champ_non_effacable_nest_pas_compte() -> None:
    """Le contre-exemple. Sans lui, le relevé pourrait tout compter."""
    champs = nullabilite.effacables(
        _plan("widget_widget", _parametre("name", False, ParameterLocation.BODY))
    )

    assert champs == []


@pytest.mark.parametrize("ou", [ParameterLocation.PATH, ParameterLocation.QUERY])
def test_un_champ_hors_du_corps_ne_pose_pas_la_question(ou: ParameterLocation) -> None:
    """Personne n'efface une zone, ni un filtre de liste.

    Les compter gonflerait la dette d'un travail que personne n'a l'intention
    de faire, ce qui rendrait le nombre inutilisable pour chiffrer quoi que ce
    soit.
    """
    champs = nullabilite.effacables(_plan("widget_widget", _parametre("zone", True, ou)))

    assert champs == []


def test_une_operation_sans_module_nest_pas_comptee() -> None:
    """Un champ qu'aucun module n'écrit ne peut pas être effacé par un playbook.

    Le relevé chiffre le travail restant sur la collection livrée, pas sur le
    contrat : un compte pris sur le contrat serait juste et sans rapport.
    """
    champs = nullabilite.effacables(
        _plan(None, _parametre("description", True, ParameterLocation.BODY))
    )

    assert champs == []


def test_le_releve_est_trie() -> None:
    """La sortie sert de bloc dérivé, donc elle doit être déterministe.

    Deux exécutions qui rendraient le même relevé dans deux ordres feraient
    rougir `readme:check` sans qu'aucun champ n'ait bougé.
    """
    champs = nullabilite.effacables(
        _plan(
            "widget_widget",
            _parametre("zzz", True, ParameterLocation.BODY),
            _parametre("aaa", True, ParameterLocation.BODY),
        )
    )

    assert [champ.champ for champ in champs] == ["aaa", "zzz"]


def test_le_depot_publie_un_compte_non_nul() -> None:
    """Ce que le relevé dit du dépôt aujourd'hui.

    Le seul test du fichier qui le regarde. Il n'affirme pas un nombre, qui
    vieillirait : il affirme que la question se pose, ce qui est ce que le bloc
    dérivé publie.
    """
    champs = nullabilite.auditer()

    assert champs, "si le compte tombe à zéro, le bloc dérivé doit le dire autrement"
    assert all(champ.module for champ in champs)
