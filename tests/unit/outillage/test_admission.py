"""Ce qu'un produit doit passer pour entrer dans la collection.

`mise run report` dit qu'un produit est classé, `parser:coverage` ce que le
parser ne sait pas lire, `docs:quality` si la page se comprend. Aucun ne répond
à la question qu'on pose vraiment en ajoutant un troisième contrat : **est-il
sûr d'ajouter RDB ?**

Ces tests portent sur les étapes une par une, avec des plans fabriqués : ce qui
compte est ce que chaque étape refuse et ce qu'elle laisse passer, pas le
verdict du jour sur les deux produits livrés. Le dernier test regarde le dépôt,
et il est nommé pour ça.
"""

from __future__ import annotations

import admission
import pytest

from generator.classifier.rules import Classification
from generator.ir.enums import (
    ApiType,
    GenerationMode,
    HTTPMethod,
    OperationKind,
    ParameterLocation,
    Scope,
)
from generator.ir.models import ApiOperation, ApiParameter, ApiService
from generator.overrides.loader import OverrideSet
from generator.plan import OperationPlan, ProductPlan


def _plan(
    *,
    kind: OperationKind = OperationKind.MANAGE,
    module: str | None = "widget_widget",
    nullable: bool = False,
    orphelins: tuple[str, ...] = (),
    contraintes: tuple[tuple[str, int], ...] = (("x-one-of", 0), ("maxLength", 0)),
    avertissements: tuple[str, ...] = (),
) -> ProductPlan:
    operation = ApiOperation(
        id="UpdateWidget",
        service="widget",
        version="v1",
        resource="widget",
        http_method=HTTPMethod.PUT,
        path="/widget/v1/widgets/{widget_id}",
        scope=Scope.ZONE,
        parameters=(
            ApiParameter(
                name="description",
                type=ApiType.STRING,
                required=False,
                location=ParameterLocation.BODY,
                nullable=nullable,
            ),
        ),
    )
    service = ApiService(
        name="widget",
        version="v1",
        operations=(operation,),
        constraint_keywords=contraintes,
        warnings=avertissements,
    )
    item = OperationPlan(
        operation=operation,
        classification=Classification(
            key=operation.key, kind=kind, mode=GenerationMode.AUTO, reason="fixture"
        ),
        module=module,
        resource="widget",
    )
    return ProductPlan(
        service=service,
        operations=(item,),
        overrides=OverrideSet(source=None),
        orphan_overrides=orphelins,
    )


class _SpecFactice:
    def __init__(self, nom: str, geres=(), comparaisons=()) -> None:
        self.name = nom
        self.managed_params = geres
        self.comparisons = comparaisons


# --- classification : la règle de sécurité du projet -----------------------


def test_un_override_orphelin_refuse_le_produit() -> None:
    """Une clé d'override qui ne désigne rien est un arbitrage devenu inerte.

    Le contrôle a attrapé le cas dès sa première exécution sur ce dépôt : la
    clé dépend de la ressource déduite, et corriger une ressource la déplace.
    """
    etape = admission.etape_classification(_plan(orphelins=("widget.v1.Widget.Disparue",)))

    assert etape.bloquante is True
    assert etape.tenue is False
    assert "orphelin" in etape.detail


def test_un_plan_complet_passe_la_classification() -> None:
    """Le contre-exemple, sans lequel le test précédent passerait aussi sur une
    étape qui refuserait tout."""
    assert admission.etape_classification(_plan()).tenue is True


# --- écritures : écarté avec sa raison n'est pas manquant ------------------


def test_un_module_de_gestion_ecarte_avec_sa_raison_passe() -> None:
    """C'est la doctrine du dépôt, et la porte la confondait.

    `instance_server_user_data` n'est pas écrit parce que le contrat ne décrit
    aucun champ du corps de `SetServerUserData`. La raison est portée et
    publiée. La première version de cette étape le refusait, sur un produit
    livré.
    """
    etape = admission.etape_ecritures(
        _plan(), specs=[], ecartes=(("widget_widget", "le contrat ne décrit aucun champ"),)
    )

    assert etape.tenue is True
    assert "écarté(s) avec sa raison" in etape.detail


def test_un_module_de_gestion_disparu_sans_raison_refuse_le_produit() -> None:
    """Un module qui disparaît en silence est indiscernable d'un module oublié."""
    etape = admission.etape_ecritures(_plan(), specs=[], ecartes=())

    assert etape.bloquante is True
    assert etape.tenue is False
    assert "widget_widget" in etape.detail


def test_une_raison_vide_nexcuse_rien() -> None:
    """Une exclusion sans raison est une disparition qui se donne un nom."""
    etape = admission.etape_ecritures(_plan(), specs=[], ecartes=(("widget_widget", ""),))

    assert etape.tenue is False


# --- comparaisons : décidées, pas subies ----------------------------------


def test_un_parametre_gere_sans_strategie_refuse_le_produit() -> None:
    """Il serait comparé strictement sans que personne l'ait décidé.

    C'est la différence entre un `ordered_list` posé et un repli subi : le
    premier est compté et visible, le second ne l'est pas.
    """
    etape = admission.etape_comparaisons(
        _plan(), specs=[_SpecFactice("widget_widget", geres=("description",))]
    )

    assert etape.bloquante is True
    assert etape.tenue is False


def test_un_parametre_gere_avec_sa_strategie_passe() -> None:
    etape = admission.etape_comparaisons(
        _plan(),
        specs=[
            _SpecFactice(
                "widget_widget",
                geres=("description",),
                comparaisons=(("description", "scalar"),),
            )
        ],
    )

    assert etape.tenue is True


# --- contraintes : traduite, nommée, ou refus -----------------------------


def test_une_contrainte_trouvee_et_tue_refuse_le_produit() -> None:
    """Un module qui accepte ce que l'API refuse ne se voit qu'au premier playbook."""
    etape = admission.etape_contraintes(_plan(contraintes=(("maxLength", 12),)))

    assert etape.bloquante is True
    assert etape.tenue is False
    assert "maxLength" in etape.detail


def test_une_contrainte_trouvee_et_nommee_passe() -> None:
    """Nommer n'est pas traduire, et c'est ADR-008 : ce qui est signalé est
    connu, donc ce n'est pas un défaut silencieux."""
    etape = admission.etape_contraintes(
        _plan(
            contraintes=(("maxLength", 12),),
            avertissements=("contrainte `maxLength` déclarée 12 fois et non traduite",),
        )
    )

    assert etape.tenue is True


# --- le prix, qui se mesure sans interdire --------------------------------


def test_les_champs_effacables_se_paient_sans_interdire() -> None:
    """En faire un refus bloquerait la collection sur un travail déjà planifié.

    La limite est connue, documentée, chiffrée, et #114 la porte. Une porte qui
    refuserait dessus punirait la mesure au lieu de la récompenser.
    """
    etape = admission.etape_effacables(_plan(nullable=True))

    assert etape.bloquante is False
    assert etape.tenue is False
    assert etape.symbole == "~ "


# --- ce que la porte dit du dépôt aujourd'hui -----------------------------


def test_les_produits_livres_sont_admis() -> None:
    """Le seul test du fichier qui regarde le dépôt.

    Les autres prouvent que la porte sait refuser ; celui-ci est ce qui empêche
    un produit refusé d'entrer dans `products.txt` : l'y ajouter rend
    `mise run check` rouge.
    """
    for produit, version in admission.VendoredSpecSource(root=admission.SPECS).available():
        etapes = admission.examiner(produit, version)
        refus = [etape.nom for etape in etapes if etape.bloquante and not etape.tenue]

        assert refus == [], f"{produit} {version} : {refus}"


def test_une_porte_qui_nexamine_rien_echoue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une porte qui n'examine rien admet tout (ADR-004)."""
    monkeypatch.setattr(admission.VendoredSpecSource, "available", lambda _self: [])

    assert admission.main(["--tous"]) == admission.EXIT_ERREUR
