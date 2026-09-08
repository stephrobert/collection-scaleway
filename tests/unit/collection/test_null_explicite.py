"""Un `null` explicite efface, et une option omise ne touche à rien.

Le runtime construisait sa demande depuis les valeurs non nulles, donc
`description: null` et `description` absent produisaient la même requête, et
le module rendait `ok` sur une description toujours là. C'était un faux
succès, avant toute la mécanique de preuve : lecture, comparaison, écriture,
relecture, vérification.

Ansible ne distingue pas les deux dans `module.params` : il porte `None` dans
les deux cas. Ce qui les sépare est un **témoin d'omission**, qu'Ansible
n'appelle que sur une clé absente de l'invocation (ADR-016). Ces tests portent
sur les deux moitiés : que le témoin dise vrai, et que le runtime en fasse un
effacement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


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


def _spec(runtime: Any, *effacables: str, comparaisons: dict[str, str] | None = None) -> Any:
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
        nullable_params=effacables,
        comparisons=tuple((comparaisons or {}).items()),
    )


# --- le témoin dit-il vrai ? --------------------------------------------------


def test_le_temoin_ne_se_declenche_que_sur_une_cle_absente(runtime: Any) -> None:
    """La mesure sur laquelle tout le reste repose, faite sur Ansible lui-même.

    Elle n'est pas recopiée d'une documentation : elle interroge le validateur
    qu'`AnsibleModule` utilise, avec l'`argument_spec` que le module publie. Si
    une version d'Ansible appelait le fallback sur une clé présente à `null`,
    ce test rougirait, et c'est exactement le jour où il faut le savoir.
    """
    from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

    spec = {"description": {"type": "str"}, "port": {"type": "int"}}
    omissions = runtime.poser_les_temoins(spec, ("description", "port"))

    ArgumentSpecValidator(spec).validate({"description": None})

    assert omissions == {"port"}, "`description: null` est écrit, `port` est omis"


def test_le_temoin_laisse_loption_publier_son_type(runtime: Any) -> None:
    """Poser le témoin ne doit rien retirer à l'entrée : ni type, ni choix.

    C'est ce que le mécanisme précédent coûtait, et la raison d'en changer.
    """
    spec = {"mode": {"type": "str", "choices": ["fast", "slow"]}}
    runtime.poser_les_temoins(spec, ("mode",))

    assert spec["mode"]["type"] == "str"
    assert spec["mode"]["choices"] == ["fast", "slow"]


def test_un_champ_effacable_absent_de_largument_spec_est_refuse(runtime: Any) -> None:
    """Le contre-exemple du désaccord : un module qui nomme un champ que sa
    propre `argument_spec` ne porte pas n'a pas été produit par ce générateur,
    et poser le témoin ailleurs ne servirait à rien."""
    with pytest.raises(ValueError, match="absent de l'`argument_spec`"):
        runtime.poser_les_temoins({"description": {"type": "str"}}, ("reverse",))


def test_un_defaut_ferait_lire_un_null_comme_une_valeur_vide(runtime: Any) -> None:
    """La mesure qui motive le refus du générateur, faite ici plutôt qu'affirmée.

    Avec un `default`, Ansible convertit un `null` explicite vers le type de
    l'option : `description: null` arrive sous la forme d'une chaîne vide, et
    l'effacement devient indistinguable de l'écriture d'une valeur vide.
    `_effacables` refuse donc de produire un tel module.
    """
    from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

    spec = {"description": {"type": "str", "default": "du contrat"}}
    runtime.poser_les_temoins(spec, ("description",))
    resultat = ArgumentSpecValidator(spec).validate({"description": None})

    assert resultat.validated_parameters["description"] == ""


# --- ce que le runtime en fait ------------------------------------------------


def test_un_null_explicite_part_dans_le_corps(runtime: Any, monkeypatch: Any) -> None:
    """La requête porte `{"description": null}`, ce que le contrat sanctionne
    en déclarant le champ effaçable."""
    api = _ApiFactice(
        [
            {"id": "c1", "name": "web", "description": "encore là"},
            {"id": "c1", "name": "web", "description": None},
        ]
    )
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, "description"), omissions=set())

    assert api.ecritures == [{"description": None}]
    assert module.resultat is not None
    assert module.resultat["changed"] is True


def test_un_champ_effacable_omis_ne_part_pas(runtime: Any, monkeypatch: Any) -> None:
    """Le contre-exemple qui sépare les deux moitiés du mécanisme.

    Sans lui, un runtime qui prendrait tout `None` pour un effacement passerait
    le test précédent, et effacerait tout ce qu'un playbook ne nomme pas.
    """
    api = _ApiFactice([{"id": "c1", "name": "web", "description": "encore là"}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, "description"), omissions={"description"})

    assert api.ecritures == []
    assert module.resultat is not None
    assert module.resultat["changed"] is False


def test_effacer_un_champ_deja_vide_ne_reecrit_pas(runtime: Any, monkeypatch: Any) -> None:
    """Le second passage d'un playbook qui efface doit rendre `changed=false`.

    C'est la propriété que l'issue demande de prouver, et c'est la comparaison
    ordinaire qui la donne : rien n'a été ajouté pour ce cas.
    """
    api = _ApiFactice([{"id": "c1", "name": "web", "description": None}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, "description"), omissions=set())

    assert api.ecritures == []
    assert module.resultat is not None
    assert module.resultat["changed"] is False


def test_un_effacement_que_lapi_nappligue_pas_fait_echouer(runtime: Any, monkeypatch: Any) -> None:
    """La vérification d'après écriture couvre l'effacement sans exception.

    Une API qui accepte la requête et rend le champ intact ressortirait sinon
    en `changed=true` à chaque exécution, indéfiniment (ADR-010).
    """
    api = _ApiFactice([{"id": "c1", "name": "web", "description": "toujours là"}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, "description"), omissions=set())

    assert module.resultat is not None
    assert module.resultat["changed"] is True, "l'API a accepté : la ressource a bougé"
    assert "description" in module.resultat["msg"]
    assert "description" in module.resultat["failed_postconditions"]


def test_plusieurs_champs_seffacent_dans_la_meme_requete(runtime: Any, monkeypatch: Any) -> None:
    """Un effacement par requête ferait deux écritures là où l'API en accepte une."""
    api = _ApiFactice(
        [
            {"id": "c1", "name": "web", "description": "là", "reverse": "aussi"},
            {"id": "c1", "name": "web", "description": None, "reverse": None},
        ]
    )
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=None, reverse=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, "description", "reverse"), omissions=set())

    assert api.ecritures == [{"description": None, "reverse": None}]


# --- le désaccord entre le module et le runtime ------------------------------


def test_un_module_sans_temoin_fait_echouer_plutot_que_tout_effacer(
    runtime: Any, monkeypatch: Any
) -> None:
    """`None` en guise d'omissions n'est pas un ensemble vide.

    Le premier dit qu'aucun témoin n'a été posé, le second qu'aucune option n'a
    été omise. Les confondre ferait passer chaque option omise pour un
    effacement demandé, ce qui est le pire des deux mondes : le module écrirait
    `null` sur des champs que le playbook n'a jamais nommés.
    """
    api = _ApiFactice([{"id": "c1", "name": "web", "description": "encore là"}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, "description"))

    assert module.resultat is not None
    assert "témoin d'omission" in module.resultat["msg"]
    assert api.ecritures == []


def test_un_module_sans_champ_effacable_na_pas_besoin_de_temoin(runtime: Any) -> None:
    """Le contre-exemple : la garde ne doit pas rendre les autres modules bavards."""
    assert runtime.explicit_nulls(_spec(runtime), {"description": None}, None) == []
