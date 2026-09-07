"""Un `null` explicite ne disparaît plus en silence.

Le runtime construisait sa demande depuis les valeurs non nulles, donc
`description: null` et `description` absent produisaient la même requête, et
le module rendait `ok` sur une description toujours là. C'était un faux
succès, avant toute la mécanique de preuve : lecture, comparaison, écriture,
relecture, vérification.

Ansible ne distingue pas les deux : `module.params` porte `None` dans les deux
cas. Le générateur pose donc un défaut marqueur, `UNCHANGED`, sur une option
`raw` pour chaque champ que le contrat déclare effaçable (ADR-012). Ces tests
portent sur ce que le runtime en fait : refuser le `null`, retirer le marqueur,
et rendre à la valeur fournie le type que `raw` lui a retiré.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from generator.ansible.mapping import UNCHANGED


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

    return scaleway


class _ModuleFactice:
    """Le strict nécessaire d'`AnsibleModule` : des paramètres et deux sorties."""

    def __init__(self, **params: Any) -> None:
        self.params = dict(params)
        self.check_mode = False
        self.resultat: dict[str, Any] | None = None

    def exit_json(self, **resultat: Any) -> None:
        self.resultat = resultat
        raise SystemExit(0)

    def fail_json(self, **resultat: Any) -> None:
        self.resultat = resultat
        raise SystemExit(1)


class _ApiFactice:
    """Une API qui compte ses constructions, et note ce qu'on lui écrit."""

    constructions = 0

    def __init__(self, lectures: list[dict[str, Any]]) -> None:
        self._lectures = lectures
        self.ecritures: list[dict[str, Any]] = []

    def fabrique(self, _module: Any) -> _ApiFactice:
        type(self).constructions += 1
        return self

    def fetch_one(self, _operation: Any) -> dict[str, Any]:
        return self._lectures[min(len(self.ecritures), len(self._lectures) - 1)]

    def request(self, _operation: Any, *, params: Any = None, body: Any = None) -> dict[str, Any]:
        self.ecritures.append(dict(body or {}))
        return {}


def _spec(runtime: Any, **effacables: dict[str, Any]) -> Any:
    geres = ("name", *effacables)
    return runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetChose", method="GET", path="/x/{chose_id}", payload_field="chose"
        ),
        update_operation=runtime.Operation(
            id="UpdateChose",
            method="PATCH",
            path="/x/{chose_id}",
            body_params=geres,
            payload_field="chose",
        ),
        managed_params=geres,
        nullable_params=tuple(effacables.items()),
    )


# --- le refus ----------------------------------------------------------------


def test_un_null_explicite_sur_un_champ_effacable_fait_echouer_sans_rien_lire(
    runtime: Any, monkeypatch: Any
) -> None:
    """Le module nomme le champ, dit quoi faire à la place, et ne touche pas à l'API.

    Refuser avant la lecture n'est pas une économie : c'est ce qui rend le refus
    identique contre l'émulateur et contre le vrai cloud, sans dépendre de ce
    que l'un ou l'autre émule.
    """
    api = _ApiFactice([{"id": "c1", "name": "web", "description": "encore là"}])
    _ApiFactice.constructions = 0
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, description={"type": "str"}))

    assert module.resultat is not None
    assert module.resultat.get("failed", True) is not False
    assert "description" in module.resultat["msg"]
    assert "null" in module.resultat["msg"]
    assert "Omettre" in module.resultat["msg"]
    assert _ApiFactice.constructions == 0, "rien ne doit être lu ni écrit"
    assert api.ecritures == []


def test_plusieurs_null_explicites_sont_tous_nommes(runtime: Any, monkeypatch: Any) -> None:
    """Un refus qui n'en nommerait qu'un ferait corriger le playbook en deux fois."""
    api = _ApiFactice([{"id": "c1"}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", description=None, reverse=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(
            module, _spec(runtime, description={"type": "str"}, reverse={"type": "str"})
        )

    assert module.resultat is not None
    assert "description" in module.resultat["msg"]
    assert "reverse" in module.resultat["msg"]


def test_un_champ_effacable_omis_porte_le_marqueur_et_nest_pas_gere(
    runtime: Any, monkeypatch: Any
) -> None:
    """Omis, le champ vaut `UNCHANGED` : il ne part pas, et `invocation` le relit `None`."""
    api = _ApiFactice([{"id": "c1", "name": "web", "description": "encore là"}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=UNCHANGED)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, description={"type": "str"}))

    assert module.resultat is not None
    assert module.resultat["changed"] is False
    assert api.ecritures == []
    assert module.params["description"] is None, "le marqueur ne doit pas sortir du module"


def test_un_null_sur_un_champ_que_le_runtime_sait_effacer_nest_pas_refuse(runtime: Any) -> None:
    """Le jour où un champ s'effacera (#114), son `null` sera une demande, pas une faute.

    Rien ne s'efface aujourd'hui, et le paramètre existe pour que le refus ne
    soit pas écrit en dur sur « tout champ effaçable ».
    """
    spec = _spec(runtime, description={"type": "str"})
    params = {"chose_id": "c1", "description": None}

    assert runtime.explicit_nulls(spec, params) == ["description"]
    assert runtime.explicit_nulls(spec, params, clearable=frozenset({"description"})) == []


# --- ce que `raw` a retiré, le runtime le rend -------------------------------


def test_une_valeur_fournie_sur_un_champ_effacable_garde_son_type(
    runtime: Any, monkeypatch: Any
) -> None:
    """`stateful: "no"` reste un booléen, comme si l'option était typée `bool`.

    L'option est `raw` pour laisser passer le marqueur ; elle laisserait donc
    passer une chaîne là où l'API attend un booléen. La valeur repasse par le
    validateur d'Ansible, avec son type réel.
    """
    api = _ApiFactice([{"id": "c1", "stateful": True}, {"id": "c1", "stateful": False}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", stateful="no")

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, stateful={"type": "bool"}))

    assert api.ecritures == [{"stateful": False}]
    assert module.resultat is not None
    assert module.resultat["changed"] is True


def test_une_valeur_du_mauvais_type_est_refusee_comme_ansible_le_ferait(
    runtime: Any, monkeypatch: Any
) -> None:
    """Le message est celui d'Ansible : même vocabulaire que sur une option typée."""
    api = _ApiFactice([{"id": "c1"}])
    _ApiFactice.constructions = 0
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", email_config="pas-un-dictionnaire")

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, email_config={"type": "dict"}))

    assert module.resultat is not None
    assert "email_config" in module.resultat["msg"]
    assert "dictionary" in module.resultat["msg"]
    assert _ApiFactice.constructions == 0


def test_le_marqueur_du_runtime_est_celui_du_generateur(runtime: Any) -> None:
    """Le générateur l'écrit dans le module, le runtime le retire : deux copies,
    un seul sens. Un désaccord ferait passer chaque option omise pour une valeur."""
    assert runtime.UNCHANGED == UNCHANGED
