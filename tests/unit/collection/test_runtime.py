"""Le runtime commun : pagination, chemins, filtres, erreurs.

Ces tests ne touchent pas le réseau. Ils portent sur les fonctions pures du
`module_utils`, qui existent sous cette forme précisément pour être mesurables
sans client ni serveur.

La preuve de bout en bout, elle, se joue contre un émulateur local :
`mise run integration`.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.local.scaleway.plugins.module_utils import scaleway

    return scaleway


# --- pagination ------------------------------------------------------------


def test_la_pagination_va_jusquau_bout(runtime: Any) -> None:
    """Rendre la première page en silence est le pire défaut possible ici."""
    pages = {
        1: {"servers": [f"a{i}" for i in range(3)]},
        2: {"servers": [f"b{i}" for i in range(3)]},
        3: {"servers": ["c0"]},
    }
    resultats = runtime.paginate(lambda page: pages[page], payload_field="servers", per_page=3)
    assert len(resultats) == 7
    assert resultats[-1] == "c0"


def test_une_page_pleine_puis_vide_termine_proprement(runtime: Any) -> None:
    """Le cas limite : le total est un multiple exact de la taille de page."""
    pages = {1: {"servers": ["a", "b"]}, 2: {"servers": []}}
    assert runtime.paginate(lambda page: pages[page], payload_field="servers", per_page=2) == [
        "a",
        "b",
    ]


def test_le_total_annonce_arrete_la_pagination(runtime: Any) -> None:
    """`total_count` n'est pas dans le contrat, mais le SDK le reconstitue."""
    appels: list[int] = []

    def page(numero: int) -> dict[str, Any]:
        appels.append(numero)
        return {"servers": ["x", "y"], "total_count": 2}

    assert runtime.paginate(page, payload_field="servers", per_page=2) == ["x", "y"]
    assert appels == [1]


def test_une_api_qui_ignore_la_taille_de_page_fait_echouer(runtime: Any) -> None:
    """Sans cette garde, la boucle tournerait indéfiniment sans rien dire."""
    with pytest.raises(runtime.ScalewayApiError):
        runtime.paginate(
            lambda page: {"servers": ["toujours", "la", "meme"]},
            payload_field="servers",
            per_page=3,
            max_pages=5,
        )


# --- chemins ---------------------------------------------------------------


def test_un_chemin_se_remplit_avec_les_parametres(runtime: Any) -> None:
    rendu = runtime.render_path(
        "/instance/v1/zones/{zone}/servers/{server_id}",
        {"zone": "fr-par-1", "server_id": "abc", "name": "ignoré"},
    )
    assert rendu == "/instance/v1/zones/fr-par-1/servers/abc"


def test_une_valeur_de_chemin_est_encodee(runtime: Any) -> None:
    """Un identifiant fourni ne doit pas pouvoir sortir de son segment."""
    rendu = runtime.render_path("/v1/things/{id}", {"id": "a/../b"})
    assert rendu == "/v1/things/a%2F..%2Fb"


def test_un_segment_non_resolu_est_refuse(runtime: Any) -> None:
    with pytest.raises(runtime.ScalewayApiError):
        runtime.render_path("/v1/zones/{zone}/things/{id}", {"zone": "fr-par-1"})


# --- filtres ---------------------------------------------------------------


def test_un_filtre_absent_nest_pas_envoye(runtime: Any) -> None:
    """Le module ne doit jamais restreindre ce que personne n'a restreint."""
    operation = runtime.Operation(
        id="ListServers",
        method="GET",
        path="/servers",
        query_params=("state", "name"),
    )
    assert runtime.build_query(operation, {"state": "stopped", "name": None}) == {
        "state": "stopped"
    }


def test_un_booleen_part_sous_sa_forme_json(runtime: Any) -> None:
    operation = runtime.Operation(
        id="ListServers", method="GET", path="/servers", query_params=("without_ip",)
    )
    assert runtime.build_query(operation, {"without_ip": False}) == {"without_ip": "false"}


# --- erreurs ---------------------------------------------------------------


class _Reponse:
    """Réponse d'API minimale, suffisante pour mesurer le message construit."""

    def __init__(self, payload: Any, status_code: int = 400) -> None:
        self.status_code = status_code
        self.headers = {"x-request-id": "req-42"}
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def test_une_erreur_porte_de_quoi_diagnostiquer(runtime: Any) -> None:
    operation = runtime.Operation(id="GetServer", method="GET", path="/servers/{id}")
    erreur = runtime._error_from_response(
        operation, _Reponse({"message": "resource is not found", "type": "not_found"}, 404)
    )
    assert erreur.details() == {
        "operation": "GetServer",
        "status_code": 404,
        "request_id": "req-42",
        "api_type": "not_found",
    }


def test_une_erreur_ne_recopie_pas_le_corps_de_la_reponse(runtime: Any) -> None:
    """Un message de module finit dans un journal, et un journal se partage."""
    operation = runtime.Operation(id="GetServer", method="GET", path="/servers/{id}")
    erreur = runtime._error_from_response(
        operation,
        _Reponse(
            {
                "message": "denied",
                "type": "permissions_denied",
                "secret_key": "11111111-2222-3333-4444-555555555555",
                "request": {"x-auth-token": "un-jeton"},
            },
            403,
        ),
    )
    rendu = erreur.message + str(erreur.details())
    assert "11111111-2222-3333-4444-555555555555" not in rendu
    assert "un-jeton" not in rendu
    assert erreur.message == "denied"


# --- paramètres communs ----------------------------------------------------


def test_les_cles_dapi_sont_marquees_no_log(runtime: Any) -> None:
    spec = runtime.scaleway_argument_spec()
    assert spec["access_key"]["no_log"] is True
    assert spec["secret_key"]["no_log"] is True


def test_lurl_de_lapi_est_surchargeable_par_lenvironnement(runtime: Any) -> None:
    """Règle 7 du projet : c'est ce qui permet de tester sans credentials."""
    api_url = runtime.scaleway_argument_spec()["api_url"]
    assert api_url["default"] == "https://api.scaleway.com"
    assert api_url["fallback"][1] == ["SCW_API_URL"]


def test_lattente_a_les_valeurs_de_la_collection_officielle(runtime: Any) -> None:
    """Un utilisateur qui change de collection ne doit pas réapprendre."""
    spec = runtime.scaleway_waitable_argument_spec()
    assert spec["wait"]["default"] is True
    assert spec["wait_timeout"]["default"] == 300


# --- la surface du SDK sur laquelle le runtime s'appuie --------------------


def test_le_sdk_expose_toujours_le_point_dexecution_attendu(runtime: Any) -> None:
    """Garde de dérive : le runtime exécute la méthode et le chemin du contrat.

    C'est ce qui évite de deviner un nom de méthode SDK depuis un
    `operationId`. Le prix est une dépendance à `API._request` ; si le SDK la
    déplace, c'est ce test qui doit le dire, pas un playbook en production.
    """
    from scaleway_core.api import API

    signature = inspect.signature(API._request)
    assert list(signature.parameters) == ["self", "method", "path", "params", "headers", "body"]
    assert runtime.HAS_SDK is True


# --- ce qu'une action attend, et ce qu'elle refuse d'attendre --------------


def test_lattente_se_termine_quand_letat_est_atteint(runtime: Any) -> None:
    etats = iter(["stopping", "stopping", "stopped"])
    observe = runtime.poll_until(
        lambda: {"state": next(etats)},
        expected="stopped",
        field_name="state",
        timeout=5,
        interval=0,
    )
    assert observe == "stopped"


def test_une_attente_qui_expire_nomme_le_dernier_etat_vu(runtime: Any) -> None:
    """Rendre la main sans le dire ferait passer une attente pour une preuve."""
    with pytest.raises(runtime.ScalewayApiError) as erreur:
        runtime.poll_until(
            lambda: {"state": "stopping"},
            expected="stopped",
            field_name="state",
            timeout=0.05,
            interval=0,
        )
    assert "stopping" in str(erreur.value)
    assert "stopped" in str(erreur.value)


class _ModuleFactice:
    """Le strict nécessaire de l'interface d'AnsibleModule pour ce test."""

    def __init__(self, **params: Any) -> None:
        self.params = {"wait": True, "wait_timeout": 300, **params}
        self.check_mode = bool(params.get("_check_mode"))
        self.resultat: dict[str, Any] | None = None

    def exit_json(self, **resultat: Any) -> None:
        self.resultat = resultat
        raise SystemExit(0)

    def fail_json(self, **resultat: Any) -> None:
        self.resultat = resultat
        raise SystemExit(1)


def test_en_check_mode_rien_nest_declenche(runtime: Any, monkeypatch: Any) -> None:
    """Un module qui agit en check mode rend le mode inutile.

    La preuve est structurelle : le client d'API est construit **après** la
    branche de check mode, donc le faire exploser suffit à montrer qu'il n'est
    pas atteint.
    """

    def interdit(_module: Any) -> None:
        raise AssertionError("le client d'API ne doit pas être construit en check mode")

    monkeypatch.setattr(runtime, "ScalewayApi", interdit)

    spec = runtime.ActionModule(
        operation=runtime.Operation(id="ServerAction", method="POST", path="/x"),
        wait_states={"poweroff": "stopped"},
    )
    module = _ModuleFactice(action="poweroff", _check_mode=True)

    with pytest.raises(SystemExit):
        runtime.run_action_module(module, spec)

    assert module.resultat is not None
    assert module.resultat["changed"] is True
    assert module.resultat["action"] == "poweroff"
    assert module.resultat["expected_state"] == "stopped"


# --- ce que l'attente doit observer avant de conclure ----------------------


def test_une_action_qui_revient_a_son_etat_de_depart_exige_une_transition(
    runtime: Any,
) -> None:
    """Le cas de `reboot` : la machine est `running` avant, et `running` après.

    Sans cette exigence, la première lecture satisfait l'attente en zéro
    seconde et la tâche suivante s'exécute pendant que la machine redémarre.
    Une attente qui ne fait rien est pire que pas d'attente : elle promet.
    """
    lectures = iter(["running", "stopping", "starting", "running"])
    vues: list[str] = []

    def lire() -> dict[str, str]:
        etat = next(lectures)
        vues.append(etat)
        return {"state": etat}

    observe = runtime.poll_until(
        lire,
        expected="running",
        field_name="state",
        timeout=5,
        interval=0,
        leave_first="running",
    )

    assert observe == "running"
    # La première lecture, identique à l'état de départ, n'a pas suffi.
    assert vues == ["running", "stopping", "starting", "running"]


def test_un_etat_qui_ne_bouge_jamais_est_dit_comme_tel(runtime: Any) -> None:
    """Ne pas confondre « c'est revenu » et « ça n'est jamais parti »."""
    with pytest.raises(runtime.ScalewayApiError) as erreur:
        runtime.poll_until(
            lambda: {"state": "running"},
            expected="running",
            field_name="state",
            timeout=0.05,
            interval=0,
            leave_first="running",
        )

    message = str(erreur.value)
    assert "n'a jamais quitté" in message
    assert "rien ne permet de confirmer" in message


def test_sans_transition_a_exiger_la_premiere_lecture_suffit(runtime: Any) -> None:
    """Le contre-exemple : `poweroff` part de `running`, donc rien à exiger."""
    observe = runtime.poll_until(
        lambda: {"state": "stopped"},
        expected="stopped",
        field_name="state",
        timeout=5,
        interval=0,
        leave_first=None,
    )
    assert observe == "stopped"


# --- ce qu'une action rapporte quand l'attente échoue ----------------------


class _ApiFactice:
    """Un client qui accepte l'action, puis ne bouge plus."""

    def __init__(self, etat: str = "running") -> None:
        self.etat = etat
        self.actions = 0

    def request(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self.actions += 1
        return {}

    def fetch_one(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"state": self.etat}


def test_une_attente_qui_echoue_rapporte_quand_meme_le_changement(
    runtime: Any, monkeypatch: Any
) -> None:
    """L'API a accepté, donc la ressource a changé, quoi qu'il arrive ensuite.

    Un `fail_json` sans `changed` fait croire à un playbook rejoué qu'il n'a
    rien fait, alors que la machine a bougé. Ce chemin n'avait aucun test :
    c'est pour ça que le défaut a vécu.
    """
    api = _ApiFactice(etat="running")
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)

    spec = runtime.ActionModule(
        operation=runtime.Operation(id="ServerAction", method="POST", path="/x"),
        read_operation=runtime.Operation(id="GetServer", method="GET", path="/x"),
        wait_states={"poweroff": "stopped"},
    )
    module = _ModuleFactice(action="poweroff", wait_timeout=0.05)

    with pytest.raises(SystemExit):
        runtime.run_action_module(module, spec)

    assert api.actions == 1, "l'action a bien été envoyée"
    assert module.resultat is not None
    assert module.resultat.get("changed") is True, (
        "l'API a accepté l'action : le résultat doit le dire, même en échec"
    )
    assert "stopped" in module.resultat["msg"]
