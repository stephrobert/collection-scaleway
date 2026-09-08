"""Un `null` explicite est refusé, et la valeur vide efface.

Le runtime construisait sa demande depuis les valeurs non nulles, donc
`description: null` et `description` absent produisaient la même requête, et
le module rendait `ok` sur une description toujours là. C'était un faux
succès, avant toute la mécanique de preuve.

Ansible ne distingue pas les deux dans `module.params` : il porte `None` dans
les deux cas. Ce qui les sépare est un **témoin d'omission**, qu'Ansible
n'appelle que sur une clé absente de l'invocation.

Ce que le refus dit ensuite vient d'une mesure sur le compte réel, pas du
contrat : l'API accepte `{"description": null}`, répond 200, et ne change
rien ; c'est `{"description": ""}` qui efface, et `{"tags": []}` pour un
tableau. Le `oneOf: [T, null]` du contrat vient des types d'enveloppe
protobuf, où `null` veut dire « champ non fourni » (ADR-016).
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


def _omissions(runtime: Any, **types: str) -> Any:
    """Un témoin déjà posé, dont rien n'a encore été omis.

    Les tests renseignent les types à la main plutôt que de construire un
    `argument_spec` : ce que `poser_les_temoins` en fait est mesuré ailleurs,
    sur Ansible lui-même.
    """
    return runtime.Omissions(absents=set(), types=dict(types))


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

    assert omissions.absents == {"port"}, "`description: null` est écrit, `port` est omis"


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


def test_un_null_explicite_est_refuse_sans_rien_lire(runtime: Any, monkeypatch: Any) -> None:
    """Refuser avant la lecture n'est pas une économie.

    C'est ce qui rend le refus identique contre l'émulateur et contre le vrai
    cloud, sans dépendre de ce que l'un ou l'autre émule.
    """
    api = _ApiFactice([{"id": "c1", "name": "web", "description": "encore là"}])
    _ApiFactice.constructions = 0
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(
            module, _spec(runtime, "description"), omissions=_omissions(runtime, description="str")
        )

    assert module.resultat is not None
    assert _ApiFactice.constructions == 0, "rien ne doit être lu ni écrit"
    assert api.ecritures == []


def test_le_refus_nomme_la_valeur_vide_du_type(runtime: Any, monkeypatch: Any) -> None:
    """Un refus qui ne dit pas quoi écrire oblige à chercher ailleurs.

    La valeur dépend du type, et le message l'écrit littéralement plutôt que de
    parler de « la valeur vide » : elle est faite pour être copiée.
    """
    api = _ApiFactice([{"id": "c1"}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", description=None, tags=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(
            module,
            _spec(runtime, "description", "tags"),
            omissions=_omissions(runtime, description="str", tags="list"),
        )

    message = module.resultat["msg"]
    assert '`description: ""`' in message
    assert "`tags: []`" in message
    assert "omettre l'option" in message


def test_le_refus_ne_promet_pas_un_effacement_impossible(runtime: Any, monkeypatch: Any) -> None:
    """Un entier n'a pas de valeur vide : `0` est une valeur, pas une absence.

    Le contre-exemple du test précédent : sans lui, un message qui inventerait
    une valeur vide pour chaque type passerait aussi.
    """
    api = _ApiFactice([{"id": "c1"}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", port=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(
            module, _spec(runtime, "port"), omissions=_omissions(runtime, port="int")
        )

    message = module.resultat["msg"]
    assert "n'a pas de valeur vide" in message
    assert "`port: " not in message


def test_un_champ_effacable_omis_ne_declenche_aucun_refus(runtime: Any, monkeypatch: Any) -> None:
    """Le contre-exemple qui sépare les deux moitiés du mécanisme.

    Sans lui, un runtime qui refuserait tout `None` passerait les tests
    ci-dessus, et refuserait chaque playbook qui n'écrit pas toutes ses options.
    """
    api = _ApiFactice([{"id": "c1", "name": "web", "description": "encore là"}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description=None)
    omissions = _omissions(runtime, description="str")
    omissions.absents.add("description")

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec(runtime, "description"), omissions=omissions)

    assert api.ecritures == []
    assert module.resultat is not None
    assert module.resultat["changed"] is False


def test_la_valeur_vide_efface_et_ne_demande_aucun_mecanisme(
    runtime: Any, monkeypatch: Any
) -> None:
    """Ce qui efface vraiment, mesuré sur le compte réel : la valeur vide.

    Elle traverse le chemin ordinaire, sans exception : c'est ce qui rend le
    reste inutile, et c'est la raison pour laquelle le runtime n'envoie jamais
    de `null`.
    """
    api = _ApiFactice(
        [
            {"id": "c1", "name": "web", "description": "encore là"},
            {"id": "c1", "name": "web", "description": ""},
        ]
    )
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description="")

    with pytest.raises(SystemExit):
        runtime.run_manage_module(
            module, _spec(runtime, "description"), omissions=_omissions(runtime, description="str")
        )

    assert api.ecritures == [{"description": ""}]
    assert module.resultat["changed"] is True


def test_vider_un_champ_deja_vide_ne_reecrit_pas(runtime: Any, monkeypatch: Any) -> None:
    """Le second passage d'un playbook qui vide rend `changed=false`.

    C'est la propriété que l'issue demande de prouver, et c'est la comparaison
    ordinaire qui la donne : rien n'a été ajouté pour ce cas.
    """
    api = _ApiFactice([{"id": "c1", "name": "web", "description": ""}])
    monkeypatch.setattr(runtime, "ScalewayApi", api.fabrique)
    module = _ModuleFactice(chose_id="c1", name="web", description="")

    with pytest.raises(SystemExit):
        runtime.run_manage_module(
            module, _spec(runtime, "description"), omissions=_omissions(runtime, description="str")
        )

    assert api.ecritures == []
    assert module.resultat["changed"] is False


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


def test_un_null_sort_avec_le_type_de_son_option(runtime: Any) -> None:
    """Le message de refus en a besoin, et le lui faire rechercher ensuite ferait
    un second endroit où l'oublier."""
    nuls = runtime.explicit_nulls(
        _spec(runtime, "description"),
        {"description": None},
        _omissions(runtime, description="str"),
    )

    assert nuls == [("description", "str")]


def test_le_temoin_retient_le_type_de_chaque_champ(runtime: Any) -> None:
    """Le type vient de l'entrée publiée, lu au moment de poser le témoin.

    Le décrire une seconde fois dans le module ferait deux descriptions du même
    type, qui finiraient par diverger, et le message de refus nommerait alors
    une valeur vide qui n'est pas celle de l'option.
    """
    spec = {"description": {"type": "str"}, "tags": {"type": "list", "elements": "str"}}
    omissions = runtime.poser_les_temoins(spec, ("description", "tags"))

    assert omissions.types == {"description": "str", "tags": "list"}
