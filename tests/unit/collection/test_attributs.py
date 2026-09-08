"""Ce qu'un module **annonce** savoir faire, confronté à ce qu'il fait.

`attributes` est une promesse formelle : `antsibull-docs` la publie et des
outils la lisent. Une page qui annonce `check_mode: full` sur un module qui agit
en check mode est un faux vert de la famille corrigée en 0.4.0, en pire.

Chaque test de ce fichier tient les deux bouts : la valeur **déclarée** dans
`generator/ansible/attributes.py`, et le comportement **exercé** du runtime.
Vérifier l'un sans l'autre ne prouverait rien : une table de constantes se
teste toute seule, et un runtime correct dont la page ment reste une page qui
ment.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import yaml

from generator.ansible.attributes import PAR_CLASSE, SUPPORTS, pour
from generator.ir.enums import OperationKind

ROOT = Path(__file__).resolve().parents[3]
MODULES = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "plugins" / "modules"


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

    return scaleway


class _Module:
    """Le strict nécessaire de l'interface d'AnsibleModule, en check mode."""

    def __init__(self, **params: Any) -> None:
        self.params = {"wait": True, "wait_timeout": 300, **params}
        self.check_mode = True
        self.resultat: dict[str, Any] | None = None

    def exit_json(self, **resultat: Any) -> None:
        self.resultat = resultat
        raise SystemExit(0)

    def fail_json(self, **resultat: Any) -> None:  # pragma: no cover - aucun test n'y passe
        self.resultat = resultat
        raise SystemExit(1)


class _Api:
    """Une API qui note ce qu'on lui écrit, et rend ce qu'on lui dit de rendre."""

    def __init__(self, lecture: dict[str, Any]) -> None:
        self._lecture = lecture
        self.ecritures: list[dict[str, Any]] = []

    def fetch_one(self, _operation: Any) -> dict[str, Any]:
        return self._lecture

    def fetch_all(self, _operation: Any) -> list[dict[str, Any]]:
        return [self._lecture]

    def request(self, _operation: Any, *, params: Any = None, body: Any = None) -> dict[str, Any]:
        self.ecritures.append(dict(body or {}))
        return {}


# --- INFO : ce qui est annoncé, et ce qui est tenu -------------------------


def test_un_module_dinformation_annonce_un_check_mode_plein_et_le_tient(
    runtime: Any, monkeypatch: Any
) -> None:
    """Il ne modifie rien : le check mode ne change donc pas son comportement."""
    assert pour(OperationKind.INFO)["check_mode"]["support"] == "full"

    api = _Api({"id": "c1", "name": "web"})
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    spec = runtime.InfoModule(
        get_operation=runtime.Operation(
            id="GetChose", method="GET", path="/x/{chose_id}", payload_field="chose"
        ),
        selector="chose_id",
    )
    module = _Module(chose_id="c1")

    with pytest.raises(SystemExit):
        runtime.run_info_module(module, spec)

    assert api.ecritures == [], "une lecture n'écrit rien, en check mode comme ailleurs"
    assert module.resultat is not None
    assert module.resultat["chose"] == {"id": "c1", "name": "web"}
    assert module.resultat.get("changed", False) is False


def test_un_module_dinformation_nannonce_aucun_diff_et_nen_rend_aucun(
    runtime: Any, monkeypatch: Any
) -> None:
    assert pour(OperationKind.INFO)["diff_mode"]["support"] == "none"

    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: _Api({"id": "c1"}))
    spec = runtime.InfoModule(
        get_operation=runtime.Operation(
            id="GetChose", method="GET", path="/x/{chose_id}", payload_field="chose"
        ),
        selector="chose_id",
    )
    module = _Module(chose_id="c1")

    with pytest.raises(SystemExit):
        runtime.run_info_module(module, spec)

    assert module.resultat is not None
    assert "diff" not in module.resultat


# --- ACTION ----------------------------------------------------------------


def test_un_module_daction_annonce_un_check_mode_plein_et_ne_declenche_rien(
    runtime: Any, monkeypatch: Any
) -> None:
    """La preuve est structurelle : le client est construit après la branche.

    Le faire exploser suffit donc à montrer qu'elle n'est pas franchie.
    """
    assert pour(OperationKind.ACTION)["check_mode"]["support"] == "full"

    def interdit(_module: Any) -> None:
        raise AssertionError("le client d'API ne doit pas être construit en check mode")

    monkeypatch.setattr(runtime, "ScalewayApi", interdit)
    spec = runtime.ActionModule(
        operation=runtime.Operation(id="ServerAction", method="POST", path="/x"),
        wait_states={"poweroff": "stopped"},
    )
    module = _Module(action="poweroff")

    with pytest.raises(SystemExit):
        runtime.run_action_module(module, spec)

    assert module.resultat is not None
    assert module.resultat["changed"] is True
    assert module.resultat["expected_state"] == "stopped"


def test_un_module_daction_nannonce_aucun_diff_et_nen_rend_aucun(
    runtime: Any, monkeypatch: Any
) -> None:
    """Un déclenchement n'a pas d'avant et d'après comparables."""
    assert pour(OperationKind.ACTION)["diff_mode"]["support"] == "none"

    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: _Api({}))
    spec = runtime.ActionModule(
        operation=runtime.Operation(id="ServerAction", method="POST", path="/x"),
    )
    module = _Module(action="poweroff")

    with pytest.raises(SystemExit):
        runtime.run_action_module(module, spec)

    assert module.resultat is not None
    assert "diff" not in module.resultat


# --- MANAGE ----------------------------------------------------------------


def test_un_module_de_gestion_annonce_un_check_mode_plein_et_necrit_rien(
    runtime: Any, monkeypatch: Any
) -> None:
    assert pour(OperationKind.MANAGE)["check_mode"]["support"] == "full"

    api = _Api({"id": "c1", "name": "web", "tags": ["a"]})
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    module = _Module(chose_id="c1", name="api", tags=["a"])

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec_gestion(runtime))

    assert api.ecritures == [], "le check mode ne doit rien écrire"
    assert module.resultat is not None
    assert module.resultat["changed"] is True


def test_un_module_de_gestion_annonce_un_diff_plein_et_le_rend(
    runtime: Any, monkeypatch: Any
) -> None:
    """`before` et `after`, tous les deux, et sur le champ qui change."""
    assert pour(OperationKind.MANAGE)["diff_mode"]["support"] == "full"

    api = _Api({"id": "c1", "name": "web", "tags": ["a"]})
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    module = _Module(chose_id="c1", name="api", tags=["a"])

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec_gestion(runtime))

    assert module.resultat is not None
    diff = module.resultat["diff"]
    assert diff["before"] == {"name": "web"}
    assert diff["after"] == {"name": "api"}


def _spec_gestion(runtime: Any) -> Any:
    return runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetChose", method="GET", path="/x/{chose_id}", payload_field="chose"
        ),
        update_operation=runtime.Operation(
            id="UpdateChose",
            method="PATCH",
            path="/x/{chose_id}",
            body_params=("name", "tags"),
            payload_field="chose",
        ),
        managed_params=("name", "tags"),
    )


# --- ce que la collection livrée publie ------------------------------------


def _classe(nom: str) -> OperationKind:
    """La classe d'un module, lue dans son nom, comme la convention l'impose."""
    if nom.endswith("_info"):
        return OperationKind.INFO
    if nom.endswith("_action"):
        return OperationKind.ACTION
    return OperationKind.MANAGE


def _documentation(source: Path) -> dict[str, Any]:
    arbre = ast.parse(source.read_text(encoding="utf-8"))
    for noeud in arbre.body:
        if isinstance(noeud, ast.Assign) and any(
            getattr(cible, "id", None) == "DOCUMENTATION" for cible in noeud.targets
        ):
            return yaml.safe_load(ast.literal_eval(noeud.value))
    raise AssertionError(f"{source.name} ne porte pas de bloc DOCUMENTATION")


def test_tout_support_publie_est_un_niveau_quansible_reconnait() -> None:
    """Une valeur hors vocabulaire passerait `ansible-test sanity` sans rien dire."""
    for kind, attributs in PAR_CLASSE.items():
        for nom, attribut in attributs.items():
            assert attribut.support in SUPPORTS, f"{kind.value}.{nom} : {attribut.support}"
            assert attribut.description.endswith("."), f"{kind.value}.{nom} : phrase inachevée"


def test_aucun_attribut_ne_porte_de_version_added() -> None:
    """Le comportement existe depuis la première version, seule la déclaration est neuve.

    Dater la déclaration ferait croire à un support nouveau, ce qui serait la
    seconde façon de mentir sur une date après celle qu'ADR-013 vient de
    corriger.
    """
    for fichier in sorted(MODULES.glob("*.py")):
        if fichier.name == "__init__.py":
            continue
        for corps in (_documentation(fichier).get("attributes") or {}).values():
            assert "version_added" not in corps, fichier.stem
