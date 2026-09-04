"""Le runtime commun : pagination, chemins, filtres, erreurs.

Ces tests ne touchent pas le réseau. Ils portent sur les fonctions pures du
`module_utils`, qui existent sous cette forme précisément pour être mesurables
sans client ni serveur.

La preuve de bout en bout, elle, se joue contre un émulateur local :
`mise run integration`.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

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


def test_une_api_qui_plafonne_la_taille_de_page_ne_tronque_pas(runtime: Any) -> None:
    """Une page courte ne veut pas dire dernière page quand `total_count` est là.

    C'est le cas que l'ordre des conditions d'arrêt décidait : l'API plafonne
    `per_page` à 50 alors qu'on demande 100, et annonce 120 éléments. Tester
    « la page est plus courte que demandée » en premier rend 50 éléments, une
    seule page, et aucun avertissement.
    """
    appels: list[int] = []

    def page(numero: int) -> dict[str, Any]:
        appels.append(numero)
        debut = (numero - 1) * 50
        return {
            "servers": [f"s{i}" for i in range(debut, min(debut + 50, 120))],
            "total_count": 120,
        }

    resultats = runtime.paginate(page, payload_field="servers", per_page=100)
    assert len(resultats) == 120
    assert appels == [1, 2, 3]


def test_un_total_annonce_que_lapi_ne_tient_pas_est_une_erreur(runtime: Any) -> None:
    """Rendre une liste incomplète en silence est exactement ce qu'on refuse."""

    def page(numero: int) -> dict[str, Any]:
        if numero == 1:
            return {"servers": ["a", "b"], "total_count": 120}
        return {"servers": [], "total_count": 120}

    with pytest.raises(runtime.ScalewayApiError) as erreur:
        runtime.paginate(page, payload_field="servers", per_page=2)
    assert "120" in str(erreur.value)
    assert "incomplète" in str(erreur.value)


def test_une_api_qui_ignore_la_taille_de_page_fait_echouer(runtime: Any) -> None:
    """Sans cette garde, la boucle tournerait indéfiniment sans rien dire."""
    with pytest.raises(runtime.ScalewayApiError):
        runtime.paginate(
            lambda page: {"servers": ["toujours", "la", "meme"]},
            payload_field="servers",
            per_page=3,
            max_pages=5,
        )


# --- filtres joints par virgules -------------------------------------------


def test_un_filtre_csv_part_en_une_seule_valeur(runtime: Any) -> None:
    """L'API attend `tags=a,b`, pas `tags=a&tags=b` ni `tags=['a', 'b']`.

    Le contrat déclare `tags` en `string` et décrit la virgule dans sa propre
    description. Le module l'expose en liste parce que c'est ce que le
    paramètre est ; la jointure appartient donc au runtime.
    """
    operation = runtime.Operation(
        id="ListServers",
        method="GET",
        path="/instance/v1/zones/{zone}/servers",
        query_params=("tags",),
        csv_params=("tags",),
    )
    assert runtime.build_query(operation, {"tags": ["a", "b"]}) == {"tags": "a,b"}
    assert runtime.build_query(operation, {"tags": ["seul"]}) == {"tags": "seul"}


def test_un_filtre_non_csv_nest_pas_joint(runtime: Any) -> None:
    """Le cas voisin : sans déclaration, la valeur passe telle quelle.

    Sans cette distinction, une valeur qui contient une virgule serait
    silencieusement coupée en deux filtres.
    """
    operation = runtime.Operation(
        id="ListServers",
        method="GET",
        path="/instance/v1/zones/{zone}/servers",
        query_params=("name",),
    )
    assert runtime.build_query(operation, {"name": "un,nom"}) == {"name": "un,nom"}


def test_un_filtre_csv_recu_en_chaine_reste_intact(runtime: Any) -> None:
    """Ansible convertit un scalaire en liste d'un élément, mais pas toujours.

    Une chaîne déjà écrite avec ses virgules doit traverser sans être
    retouchée : la joindre reviendrait à la couper puis la recoller.
    """
    operation = runtime.Operation(
        id="ListServers",
        method="GET",
        path="/instance/v1/zones/{zone}/servers",
        query_params=("tags",),
        csv_params=("tags",),
    )
    assert runtime.build_query(operation, {"tags": "a,b"}) == {"tags": "a,b"}


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
    assert api_url["fallback"][1] == ["SCW_API_URL"]


def test_lurl_de_lapi_ne_porte_pas_de_defaut_dans_largument_spec(runtime: Any) -> None:
    """Un défaut n'est jamais `None`, donc il écrase toujours le profil.

    Avec un défaut ici, un utilisateur dont le fichier de configuration pointe
    vers un émulateur voyait son playbook partir en production : l'ordre de
    priorité annoncé, paramètre puis environnement puis fichier, ne pouvait pas
    être tenu. Le défaut s'applique après la lecture du profil.
    """
    spec = runtime.scaleway_argument_spec()
    assert "default" not in spec["api_url"]
    assert "default" not in spec["api_allow_insecure"]


def test_le_fichier_de_configuration_impose_son_url(runtime: Any, monkeypatch: Any) -> None:
    """Le scénario exact du défaut : un profil qui déclare un émulateur."""
    profil = SimpleNamespace(
        api_url="http://localhost:8080",
        api_allow_insecure=True,
        user_agent=None,
        access_key="SCWXXXXXXXXXXXXXXXXX",
        secret_key="00000000-0000-0000-0000-000000000000",
        default_organization_id=None,
        default_project_id=None,
    )
    monkeypatch.setattr(
        runtime.Profile, "from_config_file_and_env", staticmethod(lambda *_a: profil)
    )
    monkeypatch.setattr(runtime.Client, "from_profile", staticmethod(lambda p: p))

    # Ce qu'un AnsibleModule pose quand l'option n'a pas de défaut : None.
    client = runtime.build_client_from_values({"api_url": None, "api_allow_insecure": None})

    assert client.api_url == "http://localhost:8080"
    assert client.api_allow_insecure is True


def test_sans_rien_de_declare_le_defaut_reste_la_production(runtime: Any, monkeypatch: Any) -> None:
    """Le contre-exemple : retirer le défaut ne doit pas le supprimer."""
    profil = SimpleNamespace(
        api_url=None,
        api_allow_insecure=None,
        user_agent=None,
        access_key=None,
        secret_key=None,
        default_organization_id=None,
        default_project_id=None,
    )
    monkeypatch.setattr(
        runtime.Profile, "from_config_file_and_env", staticmethod(lambda *_a: profil)
    )
    monkeypatch.setattr(runtime.Client, "from_profile", staticmethod(lambda p: p))

    client = runtime.build_client_from_values({})

    assert client.api_url == runtime.PRODUCTION_API_URL
    assert client.api_allow_insecure is False


def test_une_cle_refusee_par_le_sdk_ne_sort_jamais_dans_le_message(runtime: Any) -> None:
    """`Client.validate()` lève « Invalid secret key format 'SCW...' », valeur
    comprise. Ansible censure les valeurs venues des paramètres du module, pas
    celles lues dans ~/.config/scw/config.yaml : la clé atterrissait en clair
    dans le journal du playbook."""
    secret = "SCW-SECRET-QUI-NE-DOIT-PAS-SORTIR"
    erreur = ValueError(f"Invalid secret key format '{secret}', expected a UUID")

    message = runtime._safe_reason(erreur)

    assert secret not in message
    assert "secret key" in message


def test_lattente_a_les_valeurs_de_la_collection_officielle(runtime: Any) -> None:
    """Un utilisateur qui change de collection ne doit pas réapprendre."""
    spec = runtime.scaleway_waitable_argument_spec()
    assert spec["wait"]["default"] is True
    assert spec["wait_timeout"]["default"] == 300


# --- la surface du SDK sur laquelle le runtime s'appuie --------------------


def test_le_runtime_ne_depend_plus_du_point_dexecution_prive_du_sdk(runtime: Any) -> None:
    """Le runtime composait sa requête par `API._request`, méthode privée.

    Elle n'a jamais été un contrat public, et surtout elle appelle
    `requests.request()` **sans timeout** : une connexion muette figeait le
    module indéfiniment. La collection compose donc sa requête elle-même.

    Ce test garde le sens du changement : `API` ne doit plus être importé.
    """
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    assert "_request(" not in source, "le runtime rappelle la méthode privée du SDK"
    assert not hasattr(runtime, "API"), "le runtime importe encore API"
    assert runtime.HAS_SDK is True


def test_le_runtime_depend_du_client_du_sdk_et_le_dit(runtime: Any) -> None:
    """Ce dont il dépend désormais : les champs du client, qui sont publics.

    Garde de dérive : si le SDK renomme l'un d'eux, c'est ce test qui doit le
    dire, pas un playbook en production.
    """
    from scaleway_core.client import Client

    champs = {champ.name for champ in dataclasses.fields(Client)}
    for attendu in ("api_url", "secret_key", "user_agent", "api_allow_insecure"):
        assert attendu in champs, f"le SDK n'expose plus Client.{attendu}"


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


# --- ce qui borne un appel, et ce qu'il fait d'une panne réseau ------------


class _ReponseFactice:
    """Le strict nécessaire d'une réponse `requests`."""

    def __init__(self, contenu: bytes = b"{}", entetes: dict[str, str] | None = None) -> None:
        self.status_code = 200
        self.headers = entetes or {}
        self._content = contenu

    @property
    def content(self) -> bytes:
        return self._content

    def json(self) -> Any:
        import json as _json

        return _json.loads(self._content)


def _api_factice(runtime: Any, monkeypatch: Any, module: Any) -> Any:
    """Un `ScalewayApi` dont le client est posé à la main, sans réseau."""
    api = runtime.ScalewayApi.__new__(runtime.ScalewayApi)
    api._module = module
    api._client = SimpleNamespace(
        api_url="http://127.0.0.1:1",
        secret_key="secret",
        user_agent="test",
        api_allow_insecure=False,
    )
    return api


def test_un_appel_dapi_est_borne_dans_le_temps(runtime: Any, monkeypatch: Any) -> None:
    """Le SDK appelait `requests` sans timeout : une connexion muette figeait
    le module indéfiniment. Le délai est désormais passé, et configurable."""
    vus: dict[str, Any] = {}

    def faux_request(**kwargs: Any) -> Any:
        vus.update(kwargs)
        return _ReponseFactice()

    monkeypatch.setattr(runtime.requests, "request", faux_request)
    module = _ModuleFactice(api_timeout=7)
    api = _api_factice(runtime, monkeypatch, module)

    api._send(runtime.Operation(id="X", method="GET", path="/x"), "/x", {}, None)

    assert vus["timeout"] == 7


def test_le_delai_a_un_defaut_quand_le_module_ne_le_dit_pas(runtime: Any, monkeypatch: Any) -> None:
    vus: dict[str, Any] = {}
    monkeypatch.setattr(
        runtime.requests, "request", lambda **kw: (vus.update(kw), _ReponseFactice())[1]
    )
    api = _api_factice(runtime, monkeypatch, _ModuleFactice())

    api._send(runtime.Operation(id="X", method="GET", path="/x"), "/x", {}, None)

    assert vus["timeout"] == runtime.DEFAULT_REQUEST_TIMEOUT


def test_une_api_injoignable_donne_une_erreur_nommee_pas_une_trace(
    runtime: Any, monkeypatch: Any
) -> None:
    """Sans traduction, Ansible affiche MODULE FAILURE et l'utilisateur ne sait
    pas si son playbook est fautif ou si le réseau l'est."""

    def refuse(**_kwargs: Any) -> Any:
        raise runtime.requests.exceptions.ConnectionError("connexion refusée")

    monkeypatch.setattr(runtime.requests, "request", refuse)
    api = _api_factice(runtime, monkeypatch, _ModuleFactice())

    with pytest.raises(runtime.ScalewayApiError) as erreur:
        api._send(runtime.Operation(id="X", method="GET", path="/x"), "/x", {}, None)

    assert "injoignable" in str(erreur.value)


def test_un_depassement_de_delai_nomme_le_delai(runtime: Any, monkeypatch: Any) -> None:
    def trop_long(**_kwargs: Any) -> Any:
        raise runtime.requests.exceptions.Timeout("trop long")

    monkeypatch.setattr(runtime.requests, "request", trop_long)
    api = _api_factice(runtime, monkeypatch, _ModuleFactice(api_timeout=3))

    with pytest.raises(runtime.ScalewayApiError) as erreur:
        api._send(runtime.Operation(id="X", method="GET", path="/x"), "/x", {}, None)

    assert "3 s" in str(erreur.value)


def test_le_total_est_reverse_de_lentete_vers_le_corps(runtime: Any) -> None:
    """Le contrat ne déclare pas `total_count` sur les listes : c'est l'en-tête
    qui le porte, et la pagination s'en sert comme garde-fou. Le SDK le
    reversait discrètement ; ici c'est explicite, donc testable."""
    reponse = _ReponseFactice(b'{"servers": []}', {"x-total-count": "150"})

    runtime._carry_total_count(reponse)

    assert reponse.json()["total_count"] == "150"


def test_un_total_deja_present_dans_le_corps_nest_pas_ecrase(runtime: Any) -> None:
    reponse = _ReponseFactice(b'{"servers": [], "total_count": 7}', {"x-total-count": "150"})

    runtime._carry_total_count(reponse)

    assert reponse.json()["total_count"] == 7


def test_une_valeur_de_liste_devient_des_paires_repetees(runtime: Any, monkeypatch: Any) -> None:
    vus: dict[str, Any] = {}
    monkeypatch.setattr(
        runtime.requests, "request", lambda **kw: (vus.update(kw), _ReponseFactice())[1]
    )
    api = _api_factice(runtime, monkeypatch, _ModuleFactice())

    api._send(
        runtime.Operation(id="X", method="GET", path="/x"),
        "/x",
        {"tags": ["a", "b"], "zone": "fr-par-1", "vide": None},
        None,
    )

    assert vus["params"] == [("tags", "a"), ("tags", "b"), ("zone", "fr-par-1")]


# --- un module de gestion n'écrit que la différence -------------------------


class _ApiGestionFactice:
    """Une API qui note ce qu'on lui écrit, et rend ce qu'on lui a dit de rendre."""

    def __init__(self, lectures: list[dict[str, Any]]) -> None:
        self._lectures = lectures
        self.ecritures: list[dict[str, Any]] = []

    def fetch_one(self, _operation: Any) -> dict[str, Any]:
        return self._lectures[min(len(self.ecritures), len(self._lectures) - 1)]

    def request(self, _operation: Any, *, params: Any = None, body: Any = None) -> dict[str, Any]:
        self.ecritures.append(dict(body or {}))
        return {}


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


def test_une_ressource_deja_conforme_ne_declenche_aucune_ecriture(
    runtime: Any, monkeypatch: Any
) -> None:
    """C'est l'idempotence, et c'est la seule raison d'être de la lecture préalable.

    Un module qui enverrait tous ses paramètres à chaque exécution rendrait
    `changed` à chaque fois, et écraserait des champs que personne n'a demandé
    de changer.
    """
    api = _ApiGestionFactice([{"id": "c1", "name": "web", "tags": ["a"]}])
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    module = _ModuleFactice(chose_id="c1", name="web", tags=["a"])

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec_gestion(runtime))

    assert api.ecritures == [], "rien ne devait être écrit"
    assert module.resultat is not None
    assert module.resultat["changed"] is False
    assert module.resultat["chose"]["name"] == "web"


def test_seuls_les_champs_differents_sont_envoyes(runtime: Any, monkeypatch: Any) -> None:
    """Envoyer tout le corps écraserait ce qu'un autre playbook gère."""
    api = _ApiGestionFactice(
        [
            {"id": "c1", "name": "web", "tags": ["a"]},
            {"id": "c1", "name": "api", "tags": ["a"]},
        ]
    )
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    module = _ModuleFactice(chose_id="c1", name="api", tags=["a"])

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec_gestion(runtime))

    assert api.ecritures == [{"name": "api"}], "seul `name` diffère"
    assert module.resultat is not None
    assert module.resultat["changed"] is True
    assert module.resultat["diff"] == {"before": {"name": "web"}, "after": {"name": "api"}}


def test_un_parametre_non_fourni_nest_pas_gere(runtime: Any, monkeypatch: Any) -> None:
    """La convention d'Ansible, et ce qui permet à deux playbooks de coexister.

    Un paramètre absent n'est pas « à vider » : il n'est pas géré. Sans cette
    règle, un playbook qui règle les tags effacerait le nom.
    """
    api = _ApiGestionFactice([{"id": "c1", "name": "web", "tags": ["a"]}])
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    module = _ModuleFactice(chose_id="c1", name=None, tags=["a"])

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec_gestion(runtime))

    assert api.ecritures == []
    assert module.resultat is not None
    assert module.resultat["changed"] is False


def test_en_check_mode_une_gestion_ne_declenche_rien_et_dit_quoi(
    runtime: Any, monkeypatch: Any
) -> None:
    """Un check mode qui annonce un changement sans dire lequel n'aide personne."""
    api = _ApiGestionFactice([{"id": "c1", "name": "web", "tags": ["a"]}])
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    module = _ModuleFactice(chose_id="c1", name="api", tags=["a"], _check_mode=True)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, _spec_gestion(runtime))

    assert api.ecritures == [], "le check mode ne doit rien écrire"
    assert module.resultat is not None
    assert module.resultat["changed"] is True
    assert module.resultat["diff"]["after"] == {"name": "api"}


def test_un_secret_est_ecrit_sans_avoir_ete_compare(runtime: Any, monkeypatch: Any) -> None:
    """L'API ne rend jamais un secret : le comparer serait comparer à `None`.

    Le module l'écrit dès qu'il est fourni, et `changed` dit alors qu'on a
    écrit, pas qu'on a constaté une différence. C'est la seule chose vraie
    qu'on puisse dire, et la valeur ne fuit pas dans le `diff`.
    """
    api = _ApiGestionFactice(
        [
            {"id": "c1", "name": "web", "tags": ["a"]},
            {"id": "c1", "name": "web", "tags": ["a"]},
        ]
    )
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    spec = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetChose", method="GET", path="/x/{chose_id}", payload_field="chose"
        ),
        update_operation=runtime.Operation(
            id="UpdateChose", method="PATCH", path="/x/{chose_id}", body_params=("jeton",)
        ),
        managed_params=("jeton",),
        secret_params=("jeton",),
    )
    module = _ModuleFactice(chose_id="c1", jeton="s3cr3t")

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, spec)

    assert api.ecritures == [{"jeton": "s3cr3t"}]
    assert module.resultat is not None
    assert module.resultat["changed"] is True
    assert "s3cr3t" not in str(module.resultat["diff"]), "le secret ne doit pas fuir"


def test_un_secret_ne_fuit_pas_dans_le_diff_du_check_mode(runtime: Any, monkeypatch: Any) -> None:
    """C'est là, et là seulement, que la valeur peut fuir.

    Hors check mode, le `diff` montre ce que l'API **rend**, et elle ne rend
    jamais un secret : rien ne fuit même sans masquage. En check mode il montre
    ce que le playbook **demande**, donc la valeur en clair. Mon premier test
    croyait mesurer la fuite et ne mesurait rien, ce que la mutation a dit.
    """
    api = _ApiGestionFactice([{"id": "c1"}])
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    spec = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetChose", method="GET", path="/x/{chose_id}", payload_field="chose"
        ),
        update_operation=runtime.Operation(
            id="UpdateChose", method="PATCH", path="/x/{chose_id}", body_params=("jeton",)
        ),
        managed_params=("jeton",),
        secret_params=("jeton",),
    )
    module = _ModuleFactice(chose_id="c1", jeton="s3cr3t", _check_mode=True)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, spec)

    assert api.ecritures == []
    assert module.resultat is not None
    assert module.resultat["changed"] is True
    assert "s3cr3t" not in str(module.resultat["diff"]), "le secret ne doit pas fuir"


def test_une_reference_ecrite_par_id_se_compare_a_lobjet_relu(
    runtime: Any, monkeypatch: Any
) -> None:
    """L'écriture prend `backend_id`, la lecture rend `backend`.

    Scaleway écrit une référence par son identifiant et la relit par l'objet
    entier. Chercher `backend_id` dans cette réponse ne trouve rien, la
    comparaison conclut « différent », et le module rend `changed` à **chaque**
    exécution. Trouvé en exerçant `lb_frontend` sur une plateforme réelle.
    """
    api = _ApiGestionFactice([{"id": "f1", "backend": {"id": "b1", "name": "web"}}])
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    spec = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetFrontend", method="GET", path="/x/{frontend_id}", payload_field="frontend"
        ),
        update_operation=runtime.Operation(
            id="UpdateFrontend",
            method="PATCH",
            path="/x/{frontend_id}",
            body_params=("backend_id",),
        ),
        managed_params=("backend_id",),
    )
    module = _ModuleFactice(frontend_id="f1", backend_id="b1")

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, spec)

    assert api.ecritures == [], "la référence est identique, rien ne doit partir"
    assert module.resultat is not None
    assert module.resultat["changed"] is False


def test_une_reference_qui_change_vraiment_est_ecrite(runtime: Any, monkeypatch: Any) -> None:
    """Le cas voisin : la règle ne doit pas rendre le module aveugle."""
    api = _ApiGestionFactice(
        [
            {"id": "f1", "backend": {"id": "b1"}},
            {"id": "f1", "backend": {"id": "b2"}},
        ]
    )
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    spec = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetFrontend", method="GET", path="/x/{frontend_id}", payload_field="frontend"
        ),
        update_operation=runtime.Operation(
            id="UpdateFrontend",
            method="PATCH",
            path="/x/{frontend_id}",
            body_params=("backend_id",),
        ),
        managed_params=("backend_id",),
    )
    module = _ModuleFactice(frontend_id="f1", backend_id="b2")

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, spec)

    assert api.ecritures == [{"backend_id": "b2"}]


def test_un_put_recoit_tout_ce_quon_veut_garder(runtime: Any, monkeypatch: Any) -> None:
    """Un PUT remplace : lui envoyer la seule différence efface le reste.

    Sept opérations du Load Balancer sont des PUT, et le contrat le dit dans sa
    propre description : « You must set all parameters ». Envoyer `{name: ...}`
    seul remettrait à zéro `timeout_client` et les certificats du frontend, en
    silence, ce qui est précisément ce que la doctrine refuse.
    """
    api = _ApiGestionFactice(
        [
            {"id": "f1", "name": "web", "inbound_port": 80, "timeout_client": "10s"},
            {"id": "f1", "name": "api", "inbound_port": 80, "timeout_client": "10s"},
        ]
    )
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    spec = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetFrontend", method="GET", path="/x/{id}", payload_field="frontend"
        ),
        update_operation=runtime.Operation(
            id="UpdateFrontend",
            method="PUT",
            path="/x/{id}",
            body_params=("name", "inbound_port", "timeout_client"),
        ),
        managed_params=("name", "inbound_port", "timeout_client"),
    )
    module = _ModuleFactice(name="api", inbound_port=None, timeout_client=None)

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, spec)

    assert api.ecritures == [{"name": "api", "inbound_port": 80, "timeout_client": "10s"}], (
        "le PUT doit porter les champs relus, pas seulement celui qui change"
    )


def test_un_patch_ne_recoit_que_la_difference(runtime: Any, monkeypatch: Any) -> None:
    """Le cas voisin, qui ne doit pas bouger : un PATCH modifie."""
    api = _ApiGestionFactice(
        [
            {"id": "s1", "name": "web", "tags": ["a"]},
            {"id": "s1", "name": "api", "tags": ["a"]},
        ]
    )
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    spec = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetServer", method="GET", path="/x/{id}", payload_field="server"
        ),
        update_operation=runtime.Operation(
            id="UpdateServer", method="PATCH", path="/x/{id}", body_params=("name", "tags")
        ),
        managed_params=("name", "tags"),
    )
    module = _ModuleFactice(name="api", tags=["a"])

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, spec)

    assert api.ecritures == [{"name": "api"}]
