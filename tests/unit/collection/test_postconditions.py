"""Ce que l'écriture a produit se vérifie, au lieu d'être annoncé.

La chaîne était déjà saine : lire, comparer, écrire, relire. Le second read
existe parce que l'API normalise, complète, et parfois refuse en silence, et le
runtime le disait lui-même. Mais après ce read, le module annonçait
`changed=true` sans regarder ce qu'il avait relu.

Une valeur que l'API n'applique pas passait donc inaperçue, et ressortait au
playbook suivant sous la forme d'un `changed=true` éternel que personne ne relie
à sa cause. Découvrir l'écart maintenant coûte un message ; le découvrir plus
tard coûte une enquête.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

    return scaleway


def _spec(runtime: Any, **surcharges: Any) -> Any:
    base = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetChose", method="GET", path="/x/{chose_id}", payload_field="chose"
        ),
        update_operation=runtime.Operation(
            id="UpdateChose",
            method="PATCH",
            path="/x/{chose_id}",
            body_params=("name", "tags", "secret"),
            payload_field="chose",
        ),
        managed_params=("name", "tags", "secret"),
        secret_params=("secret",),
    )
    return dataclasses.replace(base, **surcharges) if surcharges else base


def _non_tenues(runtime: Any, spec: Any, demande: dict, observe: dict, strategies=None) -> dict:
    return runtime._postconditions_non_tenues(spec, demande, observe, strategies or {})


# --- le défaut que la vérification attrape --------------------------------


def test_un_champ_que_lapi_na_pas_applique_est_nomme(runtime: Any) -> None:
    """C'est le cas de l'issue : l'API accepte la requête et rend autre chose."""
    ecarts = _non_tenues(
        runtime,
        _spec(runtime),
        demande={"name": "api"},
        observe={"name": "web"},
    )

    assert ecarts == {"name": {"requested": "api", "observed": "web"}}


def test_un_etat_conforme_ne_signale_rien(runtime: Any) -> None:
    """Le contre-exemple. Sans lui, le test précédent passerait aussi sur une
    fonction qui signalerait tout."""
    assert _non_tenues(runtime, _spec(runtime), {"name": "api"}, {"name": "api"}) == {}


def test_la_verification_emploie_la_meme_comparaison_que_laller(runtime: Any) -> None:
    """C'est ce qui la rend utilisable.

    Comparer en ensemble pour décider d'écrire puis strictement pour vérifier
    ferait échouer sur un ordre que la première comparaison venait justement
    d'accepter, ce qui est le défaut qu'ADR-009 corrige.
    """
    ecarts = _non_tenues(
        runtime,
        _spec(runtime),
        demande={"tags": ["production", "web"]},
        observe={"tags": ["web", "production"]},
        strategies={"tags": "set"},
    )

    assert ecarts == {}


def test_en_egalite_stricte_le_meme_ordre_serait_un_ecart(runtime: Any) -> None:
    """Le contre-exemple du test précédent."""
    ecarts = _non_tenues(
        runtime,
        _spec(runtime),
        demande={"tags": ["production", "web"]},
        observe={"tags": ["web", "production"]},
        strategies={"tags": "scalar"},
    )

    assert "tags" in ecarts


# --- ce qui sort de la mesure, et pourquoi --------------------------------


def test_un_secret_nest_pas_verifie(runtime: Any) -> None:
    """L'API ne le rend jamais.

    Le vérifier reviendrait à comparer une valeur à `None` et à conclure
    « non tenu » à chaque exécution, ce qui ressemble à une mesure et n'en est
    pas une.
    """
    ecarts = _non_tenues(
        runtime,
        _spec(runtime),
        demande={"secret": "s3cr3t"},
        observe={},
    )

    assert ecarts == {}


def test_un_champ_ecarte_par_override_nest_pas_verifie(runtime: Any) -> None:
    """Le cas prévu est une API qui applique le champ de façon différée.

    Échouer dessus ferait échouer un playbook correct sur un délai plutôt que
    sur une erreur. La liste est vide sur les contrats d'aujourd'hui : le
    mécanisme existe pour le jour où quelqu'un observera le cas.
    """
    ecarts = _non_tenues(
        runtime,
        _spec(runtime, unverified_params=("name",)),
        demande={"name": "api"},
        observe={"name": "web"},
    )

    assert ecarts == {}


def test_un_champ_absent_de_la_relecture_est_un_ecart(runtime: Any) -> None:
    """Ne pas rendre un champ n'est pas l'avoir appliqué.

    Sans cette assertion, une API qui omettrait le champ passerait pour l'avoir
    accepté.
    """
    ecarts = _non_tenues(runtime, _spec(runtime), {"name": "api"}, {})

    assert ecarts == {"name": {"requested": "api", "observed": None}}


# --- de bout en bout -------------------------------------------------------


def test_le_module_echoue_en_disant_changed(runtime: Any, monkeypatch: Any) -> None:
    """L'API a accepté : la ressource a bougé, et l'échec doit le dire.

    Un `fail_json` sans `changed` ferait croire à un playbook rejoué qu'il n'a
    rien fait, alors que la machine, elle, a changé.
    """
    from tests.unit.collection.test_runtime import _ApiGestionFactice, _ModuleFactice

    api = _ApiGestionFactice(
        [
            {"id": "c1", "name": "web"},
            # L'API accepte l'écriture et rend l'ancienne valeur.
            {"id": "c1", "name": "web"},
        ]
    )
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    module = _ModuleFactice(chose_id="c1", name="api")

    with pytest.raises(SystemExit) as sortie:
        runtime.run_manage_module(module, _spec(runtime))

    # Le double factice distingue `exit_json` de `fail_json` par son code : le
    # `failed: true` que porte le vrai `AnsibleModule` vient de lui, pas du
    # runtime, et l'assertion doit porter sur ce que le runtime décide.
    assert sortie.value.code == 1, "le module doit échouer, pas sortir en succès"
    assert module.resultat is not None
    assert module.resultat["changed"] is True, "la ressource a bougé, il faut le dire"
    assert module.resultat["failed_postconditions"] == {
        "name": {"requested": "api", "observed": "web"}
    }
