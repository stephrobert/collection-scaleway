"""Quand la requête prend des identifiants et que la lecture rend les objets.

`UpdateServer` accepte `public_ips: ["id1", "id2"]` ; `GetServer` répond
`public_ips: [{"id": "id1", "address": ...}, ...]`. Comparer les deux
directement rend « différent » à tous les coups : le module réécrit à **chaque**
exécution et annonce `changed`, indéfiniment.

C'est le défaut de `lb_frontend.backend_id` dans sa forme plurielle, que
`_valeur_courante` ne traitait qu'au singulier. Reproduit hors ligne avant
d'être corrigé, et ce fichier est cette reproduction, gardée.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

DEUX_IP = [
    {"id": "aaaa", "address": "51.15.0.1", "dynamic": False},
    {"id": "bbbb", "address": "51.15.0.2", "dynamic": False},
]


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

    return scaleway


def test_une_liste_didentifiants_egale_la_liste_dobjets_quelle_designe(runtime: Any) -> None:
    """Le cas qui rendait le module non idempotent."""
    assert runtime._identique("id_list", ["aaaa", "bbbb"], DEUX_IP) is True


def test_le_meme_essai_en_comparaison_de_liste_ordinaire_echoue(runtime: Any) -> None:
    """La preuve que la stratégie fait le travail, et pas autre chose.

    Sans ce contre-essai, le test précédent pourrait passer parce que la
    comparaison est devenue laxiste plutôt que parce qu'elle projette.
    """
    assert runtime._identique("ordered_list", ["aaaa", "bbbb"], DEUX_IP) is False
    assert runtime._identique("set", ["aaaa", "bbbb"], DEUX_IP) is False


def test_un_ordre_different_reste_un_changement(runtime: Any) -> None:
    """La projection ne décide pas de l'ordre : elle ramène aux identifiants.

    Tant que personne n'a observé l'API réordonner cette liste, un ordre
    différent est un changement, comme pour tout tableau (ADR-009).
    """
    assert runtime._identique("id_list", ["bbbb", "aaaa"], DEUX_IP) is False


def test_une_reference_de_plus_est_un_changement(runtime: Any) -> None:
    assert runtime._identique("id_list", ["aaaa", "bbbb", "cccc"], DEUX_IP) is False


def test_une_liste_deja_faite_didentifiants_traverse_sans_dommage(runtime: Any) -> None:
    """L'API peut rendre les identifiants eux-mêmes : rien à projeter."""
    assert runtime._identique("id_list", ["a", "b"], ["a", "b"]) is True


def test_des_objets_sans_id_ne_sont_pas_projetes(runtime: Any) -> None:
    """La projection ne s'applique qu'à ce qui est une liste de références.

    Écraser autre chose ferait perdre à la comparaison ce qu'elle doit voir, et
    le module tairait un changement réel, ce qui est pire qu'un `changed` de
    trop.
    """
    assert runtime._identique("id_list", ["a"], [{"address": "x"}]) is False


def test_le_diff_montre_ce_que_la_comparaison_a_lu(runtime: Any, monkeypatch: Any) -> None:
    """L'invariant d'ADR-009 : projeter pour comparer, c'est projeter pour montrer.

    Un `before` qui montrerait les objets entiers face à un `after` qui montre
    des identifiants ferait lire un changement là où il n'y en a pas.
    """

    class _Api:
        def __init__(self) -> None:
            self.ecritures: list[dict[str, Any]] = []

        def fetch_one(self, _operation: Any) -> dict[str, Any]:
            return {"id": "s1", "public_ips": DEUX_IP}

        def request(self, _o: Any, *, params: Any = None, body: Any = None) -> dict[str, Any]:
            self.ecritures.append(dict(body or {}))
            return {}

    class _Module:
        def __init__(self, **params: Any) -> None:
            self.params = {"wait": True, "wait_timeout": 300, **params}
            self.check_mode = True
            self.resultat: dict[str, Any] | None = None

        def exit_json(self, **resultat: Any) -> None:
            self.resultat = resultat
            raise SystemExit(0)

        def fail_json(self, **resultat: Any) -> None:  # pragma: no cover
            self.resultat = resultat
            raise SystemExit(1)

    api = _Api()
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    spec = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetServer", method="GET", path="/s/{server_id}", payload_field="server"
        ),
        update_operation=runtime.Operation(
            id="UpdateServer",
            method="PATCH",
            path="/s/{server_id}",
            body_params=("public_ips",),
            payload_field="server",
        ),
        managed_params=("public_ips",),
        comparisons=(("public_ips", "id_list"),),
    )
    module = _Module(server_id="s1", public_ips=["bbbb", "aaaa"])

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, spec)

    assert module.resultat is not None
    diff = module.resultat["diff"]
    assert diff["before"] == {"public_ips": ["aaaa", "bbbb"]}
    assert diff["after"] == {"public_ips": ["bbbb", "aaaa"]}


def test_un_serveur_deja_dans_letat_demande_nest_pas_reecrit(
    runtime: Any, monkeypatch: Any
) -> None:
    """Le défaut, mesuré à l'endroit où il coûtait : une écriture par exécution."""

    class _Api:
        def __init__(self) -> None:
            self.ecritures: list[dict[str, Any]] = []

        def fetch_one(self, _operation: Any) -> dict[str, Any]:
            return {"id": "s1", "public_ips": DEUX_IP}

        def request(self, _o: Any, *, params: Any = None, body: Any = None) -> dict[str, Any]:
            self.ecritures.append(dict(body or {}))
            return {}

    class _Module:
        def __init__(self, **params: Any) -> None:
            self.params = {"wait": True, "wait_timeout": 300, **params}
            self.check_mode = False
            self.resultat: dict[str, Any] | None = None

        def exit_json(self, **resultat: Any) -> None:
            self.resultat = resultat
            raise SystemExit(0)

        def fail_json(self, **resultat: Any) -> None:  # pragma: no cover
            self.resultat = resultat
            raise SystemExit(1)

    api = _Api()
    monkeypatch.setattr(runtime, "ScalewayApi", lambda _module: api)
    spec = runtime.ManageModule(
        read_operation=runtime.Operation(
            id="GetServer", method="GET", path="/s/{server_id}", payload_field="server"
        ),
        update_operation=runtime.Operation(
            id="UpdateServer",
            method="PATCH",
            path="/s/{server_id}",
            body_params=("public_ips",),
            payload_field="server",
        ),
        managed_params=("public_ips",),
        comparisons=(("public_ips", "id_list"),),
    )
    module = _Module(server_id="s1", public_ips=["aaaa", "bbbb"])

    with pytest.raises(SystemExit):
        runtime.run_manage_module(module, spec)

    assert api.ecritures == [], "l'état demandé est déjà celui de l'API"
    assert module.resultat is not None
    assert module.resultat["changed"] is False
