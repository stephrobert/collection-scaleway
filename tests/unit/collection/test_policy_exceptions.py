"""Une exception change un statut, elle n'efface pas un constat.

Le mode de défaillance que ce filtre existe pour éviter n'est pas qu'une
exception manque : c'est qu'un problème disparaisse du rapport et que plus
personne ne sache qu'il existe.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]
PLUGIN = (
    RACINE
    / "ansible_collections"
    / "stephrobert"
    / "scaleway"
    / "plugins"
    / "filter"
    / "policy_exceptions.py"
)

MAINTENANT = "2026-09-14T12:00:00Z"

BASTION = {
    "kind": "instance",
    "id": "11111111-1111-4111-8111-111111111111",
    "name": "bastion-01",
    "zone": "fr-par-1",
    "state": "running",
    "tags": ["role=bastion"],
    "public_addresses": ["51.0.0.1"],
    "last_change": "2026-09-14T11:00:00Z",
}

BASE = {
    **BASTION,
    "id": "22222222-2222-4222-8222-222222222222",
    "name": "db-01",
    "tags": ["role=database"],
    "public_addresses": ["51.0.0.2"],
}


def _constat(ressource, regle="public_ip", severite="fail"):
    return {
        "id": f"{regle}:{ressource['kind']}:{ressource['id']}",
        "name": f"{ressource['kind']}/{ressource['name']}",
        "rule": regle,
        "field": "public_addresses",
        "severity": severite,
        "detail": f"public address: {ressource['public_addresses'][0]}",
    }


def _module():
    spec = importlib.util.spec_from_file_location("policy_exceptions", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["policy_exceptions"] = module
    spec.loader.exec_module(module)
    return module


def _exception(**reste):
    base = {
        "rule": "public_ip",
        "selector": {"id": BASTION["id"]},
        "reason": "Public bastion, reachable on purpose",
        "owner": "platform-team",
        "expires_at": "2026-12-31",
    }
    return base | reste


def _juger(exceptions, constats=None, ressources=None):
    return _module().audit_exceptions(
        constats if constats is not None else [_constat(BASTION), _constat(BASE)],
        exceptions=exceptions,
        resources=ressources if ressources is not None else [BASTION, BASE],
        now=MAINTENANT,
    )


def test_une_exception_change_le_statut_et_nefface_rien() -> None:
    """Le constat reste observable, compté à part, avec ce qui le couvre.

    Un constat effacé est un problème dont plus personne ne sait qu'il existe :
    c'est la raison d'être de ce filtre, énoncée en un test.
    """
    juge = _juger([_exception()])

    assert len(juge["findings"]) == 2
    assert juge["suppressed"] == 1
    assert juge["open"] == 1

    couvert = next(c for c in juge["findings"] if c["name"] == "instance/bastion-01")
    assert couvert["status"] == "suppressed"
    assert "platform-team" in couvert["suppressed_by"]
    # Le détail du constat est intact : on peut toujours lire ce qu'il dit.
    assert couvert["detail"] == "public address: 51.0.0.1"


def test_une_exception_ne_couvre_que_la_regle_quelle_nomme() -> None:
    """Le voisin qui ne doit pas bouger : excuser une chose n'excuse pas l'autre."""
    constats = [_constat(BASTION), _constat(BASTION, regle="required_tags")]

    juge = _juger([_exception()], constats=constats, ressources=[BASTION])

    statuts = {c["rule"]: c["status"] for c in juge["findings"]}
    assert statuts == {"public_ip": "suppressed", "required_tags": "open"}


@pytest.mark.parametrize("manquant", ["rule", "reason", "owner", "expires_at"])
def test_une_exception_incomplete_est_refusee(manquant: str) -> None:
    """Chacun de ces champs empêche une chose précise.

    Sans raison, c'est une règle désactivée qui se cache. Sans propriétaire,
    personne à qui demander si elle vaut encore. Sans échéance, ce n'est plus
    une exception mais une modification de la politique.
    """
    incomplete = {cle: valeur for cle, valeur in _exception().items() if cle != manquant}

    with pytest.raises(Exception, match=manquant):
        _juger([incomplete])


def test_une_exception_sans_selecteur_est_refusee() -> None:
    """Sans sélecteur elle couvrirait tout le parc, donc la règle serait retirée.

    **Le refus ne suffit pas, il doit dire pourquoi.** La grammaire partagée
    refuse déjà un sélecteur absent, mais elle ne sait pas qu'il s'agit d'une
    exception : « couvrirait tout le parc » est une raison qu'elle ne peut pas
    connaître, et c'est celle qui fait comprendre à son auteur ce qu'il vient
    d'écrire. `/falsify` l'a dit, en laissant ce test vert quand la garde
    spécifique était neutralisée.
    """
    sans = {cle: valeur for cle, valeur in _exception().items() if cle != "selector"}

    with pytest.raises(Exception, match="couvrirait alors tout le parc"):
        _juger([sans])


def test_un_selecteur_a_deux_criteres_est_refuse() -> None:
    """Deux critères posent deux questions, et la réponse dépendrait de l'ordre.

    Le message vient de la grammaire partagée ; le rang de l'exception vient
    d'ici, et c'est ce qu'une politique qui en porte plusieurs rend
    indispensable.
    """
    with pytest.raises(Exception, match="l'exception 1 : sélecteur qui porte"):
        _juger([_exception(selector={"name": "bastion-01", "tags": ["role=bastion"]})])


def test_une_cle_de_selecteur_inconnue_est_refusee() -> None:
    """Une faute de frappe qui ne couvre rien se lirait comme une exception inutile."""
    with pytest.raises(Exception, match="l'exception 1 : clé\\(s\\) de sélecteur inconnue"):
        _juger([_exception(selector={"nom": "bastion-01"})])


def test_un_nom_porte_par_deux_ressources_est_refuse() -> None:
    """Mesuré sur le compte réel : deux machines acceptent le même nom.

    Couvrir les deux excuserait une ressource que personne n'a désignée ;
    n'en couvrir qu'une dépendrait de l'ordre de lecture.
    """
    jumelle = {**BASTION, "id": "33333333-3333-4333-8333-333333333333"}

    with pytest.raises(Exception, match="n'est pas une identité"):
        _juger(
            [_exception(selector={"name": "bastion-01"})],
            constats=[_constat(BASTION)],
            ressources=[BASTION, jumelle],
        )


def test_un_nom_unique_designe_sans_ambiguite() -> None:
    """Le voisin : le nom reste utilisable quand il ne désigne qu'une chose."""
    juge = _juger([_exception(selector={"name": "bastion-01"})])

    assert juge["suppressed"] == 1


def test_des_etiquettes_couvrent_toutes_les_machines_qui_les_portent() -> None:
    """Une exception peut porter sur une classe, pas seulement sur une machine."""
    juge = _juger([_exception(selector={"tags": ["role=bastion"]})])

    assert juge["suppressed"] == 1
    assert juge["open"] == 1


def test_une_exception_expiree_devient_un_constat_et_ne_couvre_plus() -> None:
    """L'échéance est l'information, pas un refus.

    Refuser toute la politique parce qu'une ligne a expiré éteindrait l'audit
    entier, ce qui est exactement le contraire de ce qu'on veut le jour où une
    exception se périme.
    """
    juge = _juger([_exception(expires_at="2026-01-01")])

    assert juge["suppressed"] == 0
    assert juge["open"] == 2
    assert len(juge["expired_exceptions"]) == 1
    expiree = juge["expired_exceptions"][0]
    assert expiree["severity"] == "fail"
    assert "platform-team" in expiree["detail"]
    # La même forme qu'un constat de parc : les rendus les affichent ensemble,
    # et un rendu qui aurait deux formes à traiter finirait par en oublier une.
    assert set(juge["findings"][0]) <= set(expiree)


def test_une_exception_qui_ne_designe_rien_est_signalee_et_non_refusee() -> None:
    """Une exception pour une machine détruite est du ménage, pas une erreur."""
    juge = _juger([_exception(selector={"id": "00000000-0000-4000-8000-000000000000"})])

    assert juge["suppressed"] == 0
    assert len(juge["exceptions_without_target"]) == 1
    assert "matches no resource" in juge["exceptions_without_target"][0]["detail"]


def test_sans_exception_tout_reste_ouvert() -> None:
    """Le cas nominal, et il ne doit rien coûter."""
    juge = _juger([])

    assert juge["open"] == 2
    assert juge["suppressed"] == 0
    assert all(c["status"] == "open" for c in juge["findings"])


def test_une_echeance_qui_nest_pas_une_date_est_refusee() -> None:
    """Une échéance illisible ne se lit pas « pas encore expirée »."""
    with pytest.raises(Exception, match="ISO 8601"):
        _juger([_exception(expires_at="la semaine prochaine")])
