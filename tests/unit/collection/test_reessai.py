"""Ce qu'une opération se permet de rejouer, et ce qu'elle refuse.

Le runtime n'avait aucune politique : une requête, une réponse. Un `Retry(total=5)`
global aurait été pire que rien, parce qu'il aurait rejoué le POST qui redémarre
une machine. La politique appartient donc à l'opération (ADR-018).

Ces tests ne dorment pas : `time.sleep` est remplacé, et ce qu'il reçoit est
justement ce qu'on mesure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pytest


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

    return scaleway


class _Reponse:
    """Le strict nécessaire d'une réponse `requests`."""

    def __init__(self, status: int, entetes: dict[str, str] | None = None) -> None:
        self.status_code = status
        self.headers = entetes or {}
        self.content = b"{}"

    def json(self) -> dict[str, Any]:
        return {}


@pytest.fixture
def horloge(monkeypatch: pytest.MonkeyPatch, runtime: Any) -> list[float]:
    """Les attentes demandées, sans les subir."""
    attentes: list[float] = []
    monkeypatch.setattr(runtime.time, "sleep", attentes.append)
    return attentes


def _api(runtime: Any, monkeypatch: pytest.MonkeyPatch, reponses: list[Any]) -> list[str]:
    """Une API qui rend les réponses données, et note les méthodes reçues."""
    recus: list[str] = []

    def _requete(**kwargs: Any) -> Any:
        recus.append(str(kwargs["method"]))
        reponse = reponses[min(len(recus) - 1, len(reponses) - 1)]
        if isinstance(reponse, Exception):
            raise reponse
        return reponse

    monkeypatch.setattr(runtime.requests, "request", _requete)
    return recus


def _client(runtime: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Un `ScalewayApi` dont le client est un profil minimal."""

    class _Module:
        params: ClassVar[dict[str, Any]] = {"api_timeout": 5}

    class _Client:
        api_url = "https://api.test"
        api_allow_insecure = False
        user_agent = "test"
        secret_key = "s"

    api = runtime.ScalewayApi.__new__(runtime.ScalewayApi)
    api._module = _Module()
    api._client = _Client()
    return api


def _operation(runtime: Any, retry: str, methode: str = "GET") -> Any:
    return runtime.Operation(id="Op", method=methode, path="/x", retry=retry)


# --- ce que la politique interdit --------------------------------------------


def test_une_action_nest_jamais_rejouee_sur_un_503(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """La propriété que l'issue demande de prouver, et la raison d'être du champ.

    Un redémarrage joué deux fois n'est pas un redémarrage. Aucun code de
    statut ne change ça : après un `503`, l'action a peut-être été déclenchée.
    """
    api = _client(runtime, monkeypatch)
    recus = _api(runtime, monkeypatch, [_Reponse(503)])

    reponse = api._send(_operation(runtime, "never", "POST"), "/x", {}, None)

    assert reponse.status_code == 503
    assert len(recus) == 1, "l'action ne doit partir qu'une fois"
    assert horloge == []


def test_une_action_nest_pas_rejouee_non_plus_sur_un_429(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """Le contre-exemple du test suivant.

    Un `429` dit que la requête n'a pas été traitée, et une écriture ordinaire
    se le permet. Une action non : c'est la politique qui décide, pas le code.
    """
    api = _client(runtime, monkeypatch)
    recus = _api(runtime, monkeypatch, [_Reponse(429, {"Retry-After": "1"})])

    api._send(_operation(runtime, "never", "POST"), "/x", {}, None)

    assert len(recus) == 1


def test_une_ecriture_nest_pas_rejouee_sur_un_502(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """Après un `502`, l'écriture a peut-être abouti.

    Le module préfère échouer bruyamment plutôt que rendre un état qu'il n'a
    pas observé : c'est ce qui sépare `limited` de `safe`.
    """
    api = _client(runtime, monkeypatch)
    recus = _api(runtime, monkeypatch, [_Reponse(502)])

    api._send(_operation(runtime, "limited", "PATCH"), "/x", {}, None)

    assert len(recus) == 1


# --- ce que la politique autorise --------------------------------------------


def test_une_ecriture_est_rejouee_sur_un_429(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """Le refus vient du limiteur, avant l'API : la requête n'a pas eu lieu."""
    api = _client(runtime, monkeypatch)
    recus = _api(runtime, monkeypatch, [_Reponse(429, {"Retry-After": "2"}), _Reponse(200)])

    reponse = api._send(_operation(runtime, "limited", "PATCH"), "/x", {}, None)

    assert reponse.status_code == 200
    assert len(recus) == 2
    assert horloge == [2.0]


def test_une_lecture_est_rejouee_sur_un_503(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """Rejouer une lecture ne peut rien casser, donc l'ambiguïté ne coûte rien."""
    api = _client(runtime, monkeypatch)
    recus = _api(runtime, monkeypatch, [_Reponse(503), _Reponse(200)])

    reponse = api._send(_operation(runtime, "safe"), "/x", {}, None)

    assert reponse.status_code == 200
    assert len(recus) == 2
    assert horloge == [runtime.ATTENTES[0]]


def test_les_reessais_sont_bornes(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """Au-delà, un playbook attend sans que personne sache pourquoi."""
    api = _client(runtime, monkeypatch)
    recus = _api(runtime, monkeypatch, [_Reponse(503)])

    reponse = api._send(_operation(runtime, "safe"), "/x", {}, None)

    assert reponse.status_code == 503
    assert len(recus) == runtime.MAX_REESSAIS + 1


# --- ce que `Retry-After` demande --------------------------------------------


def test_un_retry_after_en_secondes_est_respecte(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """La seconde propriété que l'issue demande de prouver.

    Attendre moins que ce que le serveur demande aggrave la saturation qu'il
    signale, et c'est exactement ce qu'un réessai naïf fait.
    """
    api = _client(runtime, monkeypatch)
    _api(runtime, monkeypatch, [_Reponse(429, {"Retry-After": "7"}), _Reponse(200)])

    api._send(_operation(runtime, "safe"), "/x", {}, None)

    assert horloge == [7.0]


def test_un_retry_after_en_date_http_est_respecte(runtime: Any) -> None:
    """RFC 9110 en autorise deux formes, et n'en lire qu'une ignore l'autre.

    Ignorer une date en silence ferait rejouer tout de suite sur une API qui
    vient de dire non, ce qui est le comportement que le réessai doit éviter.
    """
    from datetime import UTC, datetime, timedelta
    from email.utils import format_datetime

    dans_dix = format_datetime(datetime.now(UTC) + timedelta(seconds=10))

    secondes = runtime._secondes_de_retry_after(dans_dix)

    assert secondes is not None
    assert 8.0 <= secondes <= 11.0


def test_un_retry_after_illisible_retombe_sur_lattente_par_defaut(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """Le serveur a déjà dit l'essentiel en rendant 429.

    Échouer sur un en-tête mal formé transformerait une saturation passagère en
    playbook rouge, pour une raison qui n'a rien à voir avec l'utilisateur.
    """
    api = _client(runtime, monkeypatch)
    _api(runtime, monkeypatch, [_Reponse(429, {"Retry-After": "bientôt"}), _Reponse(200)])

    api._send(_operation(runtime, "safe"), "/x", {}, None)

    assert horloge == [runtime.ATTENTES[0]]


def test_un_retry_after_trop_long_nest_pas_attendu(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """Le module aurait l'air figé, et l'erreur porte déjà l'information."""
    api = _client(runtime, monkeypatch)
    recus = _api(runtime, monkeypatch, [_Reponse(429, {"Retry-After": "600"})])

    reponse = api._send(_operation(runtime, "safe"), "/x", {}, None)

    assert reponse.status_code == 429
    assert len(recus) == 1
    assert horloge == []


# --- ce qui n'est pas une réponse --------------------------------------------


def test_une_panne_de_transport_ne_rejoue_quune_lecture(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """Le cas le plus ambigu qui soit : la requête est peut-être partie."""
    panne = runtime.requests.exceptions.ConnectionError("réseau")
    api = _client(runtime, monkeypatch)
    recus = _api(runtime, monkeypatch, [panne, _Reponse(200)])

    reponse = api._send(_operation(runtime, "safe"), "/x", {}, None)

    assert reponse.status_code == 200
    assert len(recus) == 2


def test_une_panne_de_transport_sur_une_ecriture_echoue_tout_de_suite(
    runtime: Any, monkeypatch: pytest.MonkeyPatch, horloge: list[float]
) -> None:
    """Le contre-exemple : sans lui, le test précédent passerait aussi sur un
    runtime qui rejouerait toutes les pannes de transport."""
    panne = runtime.requests.exceptions.ConnectionError("réseau")
    api = _client(runtime, monkeypatch)
    recus = _api(runtime, monkeypatch, [panne, _Reponse(200)])

    with pytest.raises(runtime.ScalewayApiError, match="injoignable"):
        api._send(_operation(runtime, "limited", "PATCH"), "/x", {}, None)

    assert len(recus) == 1


# --- ce que les modules livrés déclarent -------------------------------------


def test_aucune_action_livree_nautorise_un_reessai(runtime: Any, collection_root: Path) -> None:
    """Le seul test du fichier qui regarde ce qui est livré, et c'est voulu.

    Les autres prouvent que la boucle décide bien ; celui-ci dit ce que les
    modules publiés déclarent. Il les **importe** plutôt que de relire le plan :
    un fichier qui s'analyse n'est pas un fichier qui s'exécute, et c'est ce
    fichier-là qu'un playbook chargera.

    Les créneaux sont nommés par classe et non cherchés au jugé : un attribut
    mal orthographié rendrait `None`, le test compterait zéro action, et il
    passerait au vert en ne mesurant plus rien. Les compteurs finaux existent
    pour cette raison.
    """
    import importlib

    #: Par classe de déclaration, le champ et la politique qu'il doit porter.
    creneaux: dict[type, tuple[tuple[str, str], ...]] = {
        runtime.InfoModule: (("get_operation", "safe"), ("list_operation", "safe")),
        runtime.ActionModule: (("operation", "never"), ("read_operation", "safe")),
        runtime.ManageModule: (("update_operation", "limited"), ("read_operation", "safe")),
    }

    dossier = collection_root / "ansible_collections" / "stephrobert" / "scaleway"
    noms = sorted(chemin.stem for chemin in (dossier / "plugins" / "modules").glob("*.py"))
    assert noms, "aucun module livré : le test ne mesure plus rien"

    comptes = {"never": 0, "limited": 0, "safe": 0}
    for nom in noms:
        module = importlib.import_module(
            f"ansible_collections.stephrobert.scaleway.plugins.modules.{nom}"
        )
        declaration = module.MODULE
        attendus = creneaux.get(type(declaration))
        assert attendus is not None, f"{nom} : classe {type(declaration).__name__} non prévue ici"
        for champ, attendu in attendus:
            operation = getattr(declaration, champ)
            if operation is None:
                continue
            assert operation.retry == attendu, f"{nom}.{champ} rejoue {operation.retry!r}"
            comptes[attendu] += 1

    assert comptes["never"], "aucune action examinée : le test ne mesure plus rien"
    assert comptes["limited"], "aucune écriture examinée"
    assert comptes["safe"], "aucune lecture examinée"
