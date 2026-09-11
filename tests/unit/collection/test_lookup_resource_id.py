"""Le lookup traduit entre Ansible et la table, et ne décide rien d'autre.

Ce qui est mesuré ici est la traduction : ce que le plugin fait d'un appel mal
formé, et ce qu'il dit quand la réponse est « non ». La décision de résolution,
elle, est mesurée dans `test_resolution_runtime.py`, et il n'y a aucune raison
de la remesurer sous une autre forme.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

NOM_COMPLET = "stephrobert.scaleway.resource_id"


@pytest.fixture(scope="module")
def plugin(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.lookup import resource_id

    return resource_id


@pytest.fixture()
def lookup(plugin: Any) -> Any:
    """Un plugin dont les options documentées sont enregistrées, comme à l'exécution.

    **Sans cet enregistrement, `get_option` lève `KeyError`** : les options d'un
    plugin ne vivent pas dans son instance, elles vivent dans la configuration
    d'Ansible, et c'est le chargeur qui les y met. Un test qui instancierait
    `LookupModule()` tout seul mesurerait un chemin que personne n'emprunte.

    **Et pourtant on n'appelle pas `init_plugin_loader`.** Mesuré : il installe
    le chercheur de collections *globalement*, et tous les tests qui importent
    ensuite `ansible_collections...` par `sys.path` cessent de trouver leur
    module. Le premier essai a rougi des fichiers entiers qui n'ont rien à voir
    avec ce plugin, et c'est `/falsify` qui l'a dit, parce qu'il rejoue toute la
    suite avant de mesurer quoi que ce soit. On enregistre donc les définitions,
    et rien d'autre.
    """
    import yaml
    from ansible import constants as C

    C.config.initialize_plugin_configuration_definitions(
        "lookup", NOM_COMPLET, yaml.safe_load(plugin.DOCUMENTATION)["options"]
    )
    instance = plugin.LookupModule()
    instance._load_name = NOM_COMPLET
    return instance


def _executer(lookup: Any, terms: list[str], **kwargs: Any) -> Any:
    return lookup.run(terms, variables={}, **kwargs)


# --- ce que le plugin refuse avant même de regarder la table ---------------


def test_deux_identifiants_dans_un_appel_sont_refuses(plugin: Any, lookup: Any) -> None:
    """Deux identifiants ne pourraient pas dire quelle portée appartient auquel."""
    from ansible.errors import AnsibleLookupError

    with pytest.raises(AnsibleLookupError) as erreur:
        _executer(lookup, ["server_id", "volume_id"], name="web")

    assert "exactement un identifiant" in str(erreur.value)


def test_aucun_identifiant_est_refuse(plugin: Any, lookup: Any) -> None:
    from ansible.errors import AnsibleLookupError

    with pytest.raises(AnsibleLookupError):
        _executer(lookup, [], name="web")


# --- les trois cas de la table, et ils ne se confondent pas ----------------


def test_un_identifiant_inconnu_liste_ce_qui_est_resoluble(plugin: Any, lookup: Any) -> None:
    from ansible.errors import AnsibleLookupError

    with pytest.raises(AnsibleLookupError) as erreur:
        _executer(lookup, ["widget_id"], name="web")

    message = str(erreur.value)
    assert "n'est pas un identifiant" in message
    # La liste sert à corriger l'appel sans aller lire la documentation.
    assert "server_id" in message and "backend_id" in message


def test_un_identifiant_non_resoluble_rend_la_raison_du_contrat(plugin: Any, lookup: Any) -> None:
    """« Inconnu » enverrait chercher une faute de frappe dans un nom correct.

    `ip_id` est correctement orthographié, existe, et ne se résout pas : c'est
    l'objet `Ip` qui ne porte pas de champ `name`.
    """
    from ansible.errors import AnsibleLookupError

    with pytest.raises(AnsibleLookupError) as erreur:
        _executer(lookup, ["ip_id"], name="web")

    message = str(erreur.value)
    assert "ne se résout pas par un nom" in message
    assert "ne porte pas de champ name" in message
    assert "module d'information" in message


def test_un_nom_absent_est_refuse_par_ansible_lui_meme(plugin: Any, lookup: Any) -> None:
    """`required: true` est tenu par le chargeur, pas par le plugin."""
    from ansible.errors import AnsibleRequiredOptionError

    with pytest.raises(AnsibleRequiredOptionError):
        _executer(lookup, ["server_id"], zone="fr-par-1")


def test_un_nom_vide_est_refuse_par_le_plugin(plugin: Any, lookup: Any) -> None:
    """Une variable non définie repliée sur `''` traverse la déclaration.

    Ansible la considère fournie ; lister avec elle ne sélectionnerait rien, et
    le message doit dire pourquoi plutôt que de rendre une liste vide.
    """
    from ansible.errors import AnsibleLookupError

    with pytest.raises(AnsibleLookupError) as erreur:
        _executer(lookup, ["server_id"], zone="fr-par-1", name="")

    assert "exige `name`" in str(erreur.value)


# --- le chemin qui aboutit -------------------------------------------------


def test_la_portee_et_la_zone_arrivent_ensemble_au_runtime(
    plugin: Any, lookup: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le runtime rend le chemin depuis un seul dictionnaire.

    Il n'a pas à savoir si `zone` vient d'une option déclarée et `lb_id` d'un
    argument libre : c'est le plugin qui les réunit.
    """
    vus: dict[str, Any] = {}

    def _resolve(api: Any, table: Any, *, name: str, values: dict[str, Any]) -> str:
        vus["name"] = name
        vus["values"] = values
        vus["operation"] = table.operation.id
        return "uuid-trouve"

    monkeypatch.setattr(
        plugin, "ScalewayApi", type("Faux", (), {"from_values": staticmethod(dict)})
    )
    monkeypatch.setattr(plugin, "resolve_resource_id", _resolve)

    rendu = _executer(lookup, ["backend_id"], zone="fr-par-1", lb_id="uuid-lb", name="api")

    assert rendu == ["uuid-trouve"]
    assert vus["operation"] == "ListBackends"
    assert vus["name"] == "api"
    assert vus["values"] == {"zone": "fr-par-1", "lb_id": "uuid-lb"}


def test_un_refus_du_runtime_devient_une_erreur_ansible(
    plugin: Any, lookup: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le message du runtime traverse : c'est lui qui nomme les candidats."""
    from ansible.errors import AnsibleLookupError

    def _resolve(api: Any, table: Any, *, name: str, values: dict[str, Any]) -> str:
        raise plugin.ResolutionError("2 ressources portent exactement le nom « web »")

    monkeypatch.setattr(
        plugin, "ScalewayApi", type("Faux", (), {"from_values": staticmethod(dict)})
    )
    monkeypatch.setattr(plugin, "resolve_resource_id", _resolve)

    with pytest.raises(AnsibleLookupError) as erreur:
        _executer(lookup, ["server_id"], zone="fr-par-1", name="web")

    assert "2 ressources portent exactement" in str(erreur.value)


def test_une_configuration_refusee_devient_une_erreur_ansible(
    plugin: Any, lookup: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un module sort par `fail_json` ; un lookup doit rendre l'erreur à Ansible."""
    from ansible.errors import AnsibleLookupError

    def _from_values(valeurs: dict[str, Any]) -> Any:
        raise plugin.ScalewayConfigurationError("identifiants Scaleway absents")

    monkeypatch.setattr(
        plugin, "ScalewayApi", type("Faux", (), {"from_values": staticmethod(_from_values)})
    )

    with pytest.raises(AnsibleLookupError) as erreur:
        _executer(lookup, ["server_id"], zone="fr-par-1", name="web")

    assert "identifiants Scaleway absents" in str(erreur.value)


# --- ce que le plugin déclare ---------------------------------------------


def test_les_options_du_client_portent_leur_variable_d_environnement(plugin: Any) -> None:
    """Une option sans `env` verrait son défaut écraser l'environnement.

    C'est la raison pour laquelle ces options sont redéclarées ici plutôt
    qu'héritées du fragment des modules, et c'est la même que pour l'inventaire.
    """
    import yaml

    documentation = yaml.safe_load(plugin.DOCUMENTATION)
    options = documentation["options"]

    for nom, variable in (
        ("access_key", "SCW_ACCESS_KEY"),
        ("secret_key", "SCW_SECRET_KEY"),
        ("api_url", "SCW_API_URL"),
        ("profile", "SCW_PROFILE"),
    ):
        declarees = [entree["name"] for entree in options[nom].get("env", [])]
        assert variable in declarees, f"{nom} ne lit pas {variable}"


def test_toutes_les_valeurs_du_client_sont_des_options_declarees(plugin: Any) -> None:
    """Sinon `get_option` lèverait au moment le plus inutile : à l'exécution."""
    import yaml

    options = yaml.safe_load(plugin.DOCUMENTATION)["options"]

    for nom in plugin.VALEURS_DU_CLIENT:
        assert nom in options, f"{nom} est lu mais pas déclaré"
        assert nom in plugin.DECLAREES, f"{nom} ne serait pas transmis à set_options"
