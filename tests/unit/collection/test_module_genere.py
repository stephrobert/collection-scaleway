"""Le module produit s'importe, et Ansible accepte son `argument_spec`.

Un fichier qui s'analyse syntaxiquement n'est pas un fichier qui s'exécute :
`ast.parse` accepte un module dont une substitution a effacé une variable, et
il lève `NameError` au premier appel. Ces tests importent réellement le module
par le chemin qu'Ansible utilise, et font valider son `argument_spec` par le
validateur d'Ansible lui-même.

Ils ne remplacent pas `mise run sanity` ni `mise run integration` : ils sont ce qui
rougit en une seconde, avant eux.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import yaml
from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

from generator.ansible.collection import Collection, find_collection
from generator.ansible.mapping import COMMON_PARAMETERS

MODULE_NAME = "instance_server_info"

#: **Dérivé de `galaxy.yml`, et non écrit segment par segment.** La version
#: précédente assemblait `"ansible_collections" / "local" / "scaleway"` ; un
#: renommage de namespace ne pouvait pas la voir, parce qu'aucune recherche
#: textuelle de `local/scaleway` ne trouve un chemin découpé en morceaux. Le
#: symptôme était un `FileNotFoundError` dans le harnais de falsification,
#: c'est-à-dire loin de la cause.
SOURCE = find_collection() / "plugins" / "modules" / f"{MODULE_NAME}.py"


@pytest.fixture(scope="module")
def module(collection_root: Path) -> Any:
    """Le module généré, importé par le chemin qu'Ansible résout."""
    from ansible_collections.stephrobert.scaleway.plugins.modules import instance_server_info

    return instance_server_info


@pytest.fixture(scope="module")
def documentation() -> dict[str, Any]:
    """Le bloc `DOCUMENTATION` du fichier produit, relu comme du YAML."""
    arbre = ast.parse(SOURCE.read_text(encoding="utf-8"))
    for noeud in arbre.body:
        cible = noeud.targets[0] if isinstance(noeud, ast.Assign) else None
        if isinstance(cible, ast.Name) and cible.id == "DOCUMENTATION":
            return dict(yaml.safe_load(noeud.value.value))  # type: ignore[attr-defined,union-attr]
    raise AssertionError("le module produit ne porte pas de DOCUMENTATION")


# --- il s'exécute ----------------------------------------------------------


def test_le_module_produit_simporte(module: Any) -> None:
    assert module.MODULE.selector == "server_id"
    assert module.MODULE.get_operation.id == "GetServer"
    assert module.MODULE.list_operation.id == "ListServers"


def test_ansible_accepte_largument_spec(module: Any) -> None:
    """La preuve qui compte : le validateur d'Ansible, pas une relecture."""
    resultat = ArgumentSpecValidator(module.ARGUMENT_SPEC).validate(
        {"zone": "fr-par-1", "access_key": "SCW00000000000000000", "secret_key": "x"}
    )
    assert resultat.error_messages == []
    assert resultat.validated_parameters["zone"] == "fr-par-1"


def test_une_zone_hors_du_contrat_est_refusee(module: Any) -> None:
    resultat = ArgumentSpecValidator(module.ARGUMENT_SPEC).validate({"zone": "fr-par-9"})
    assert resultat.error_messages


def test_la_zone_est_obligatoire(module: Any) -> None:
    assert ArgumentSpecValidator(module.ARGUMENT_SPEC).validate({}).error_messages


def test_lidentifiant_du_serveur_est_facultatif(module: Any) -> None:
    """Sans lui le module liste : l'exiger interdirait la moitié du module."""
    resultat = ArgumentSpecValidator(module.ARGUMENT_SPEC).validate({"zone": "fr-par-1"})
    assert resultat.error_messages == []
    assert resultat.validated_parameters["server_id"] is None


# --- ce qu'il déclare ------------------------------------------------------


def test_aucun_parametre_commun_nest_redeclare(module: Any) -> None:
    assert not COMMON_PARAMETERS & set(module.MODULE_ARGUMENT_SPEC)
    assert {"access_key", "secret_key", "api_url"} <= set(module.ARGUMENT_SPEC)


def test_la_zone_porte_les_dix_valeurs_du_contrat(module: Any) -> None:
    assert len(module.ARGUMENT_SPEC["zone"]["choices"]) == 10


def test_la_pagination_reste_au_runtime(module: Any) -> None:
    assert "page" not in module.ARGUMENT_SPEC
    assert "per_page" not in module.ARGUMENT_SPEC
    assert module.MODULE.list_operation.page_param == "page"


def test_aucun_filtre_ne_porte_de_valeur_par_defaut(module: Any) -> None:
    """Un défaut hérité du contrat filtrerait une liste sans qu'on l'ait demandé."""
    assert all("default" not in entree for entree in module.MODULE_ARGUMENT_SPEC.values())


def test_la_documentation_et_largument_spec_disent_la_meme_chose(
    module: Any, documentation: dict[str, Any]
) -> None:
    assert set(documentation["options"]) == set(module.MODULE_ARGUMENT_SPEC)
    for nom, declaree in module.MODULE_ARGUMENT_SPEC.items():
        documentee = documentation["options"][nom]
        assert documentee["type"] == declaree["type"]
        assert documentee.get("choices") == declaree.get("choices")
        assert documentee.get("required") == declaree.get("required")


def test_la_documentation_etend_le_fragment_des_parametres_communs(
    documentation: dict[str, Any], collection: Collection
) -> None:
    assert documentation["extends_documentation_fragment"] == [collection.doc_fragment]


def test_le_module_dit_quil_est_genere() -> None:
    assert "# This file is generated." in SOURCE.read_text(encoding="utf-8")


def test_le_module_ne_porte_ni_client_ni_pagination() -> None:
    """Tout cela vit dans le module_utils, et un module ne le duplique pas."""
    source = SOURCE.read_text(encoding="utf-8")
    for interdit in ("import requests", "scaleway_core", "def paginate", "x-auth-token"):
        assert interdit not in source


# --- le module d'action ----------------------------------------------------

ACTION_SOURCE = SOURCE.with_name("instance_server_action.py")


@pytest.fixture(scope="module")
def module_action(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.modules import instance_server_action

    return instance_server_action


def test_le_module_daction_simporte(module_action: Any) -> None:
    assert module_action.MODULE.operation.id == "ServerAction"
    assert module_action.MODULE.action_parameter == "action"


def test_il_nexpose_ni_suppression_ni_creation(module_action: Any) -> None:
    """`terminate` supprime l'Instance, `backup` crée une image."""
    choix = module_action.ARGUMENT_SPEC["action"]["choices"]
    assert choix == ["poweron", "poweroff", "reboot", "stop_in_place"]
    assert "terminate" not in choix
    assert "backup" not in choix


def test_ansible_refuse_une_action_hors_de_la_liste(module_action: Any) -> None:
    resultat = ArgumentSpecValidator(module_action.ARGUMENT_SPEC).validate(
        {"zone": "fr-par-1", "server_id": "x", "action": "terminate"}
    )
    assert resultat.error_messages


def test_ansible_accepte_un_arret(module_action: Any) -> None:
    resultat = ArgumentSpecValidator(module_action.ARGUMENT_SPEC).validate(
        {"zone": "fr-par-1", "server_id": "x", "action": "poweroff"}
    )
    assert resultat.error_messages == []
    assert resultat.validated_parameters["wait"] is True
    assert resultat.validated_parameters["wait_timeout"] == 300


def test_laction_est_obligatoire(module_action: Any) -> None:
    resultat = ArgumentSpecValidator(module_action.ARGUMENT_SPEC).validate(
        {"zone": "fr-par-1", "server_id": "x"}
    )
    assert resultat.error_messages


def test_il_declare_les_etats_quil_attend(module_action: Any) -> None:
    assert module_action.MODULE.wait_states["poweroff"] == "stopped"
    assert module_action.MODULE.read_operation.id == "GetServer"


def test_le_module_daction_ne_porte_aucune_logique() -> None:
    arbre = ast.parse(ACTION_SOURCE.read_text(encoding="utf-8"))
    fonctions = [n.name for n in ast.walk(arbre) if isinstance(n, ast.FunctionDef)]
    assert fonctions == ["main"]
    main = next(n for n in ast.walk(arbre) if isinstance(n, ast.FunctionDef))
    assert len(main.body) == 2
