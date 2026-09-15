"""Ce qui est nouveau, ce qui persiste, ce qui est résolu, et ce qu'on ignore."""

from __future__ import annotations

import pytest

from ansible_collections.stephrobert.scaleway.plugins.filter.audit_changes import (
    audit_changes,
    changes_verdict,
)

MAINTENANT = "2026-09-14T10:00:00Z"
HIER = "2026-09-13T10:00:00Z"
#: Les portées sont typées : `fr-par` est une région et `fr-par-1` une zone, et
#: rien dans la chaîne ne permet de les distinguer (#273).
PORTEES = [
    {"type": "zone", "name": "fr-par-1"},
    {"type": "zone", "name": "fr-par-2"},
]
REGION = {"type": "region", "name": "fr-par"}


def _constat(
    regle: str = "public_ip",
    identifiant: str = "aaaa-1111",
    portee: str = "fr-par-1",
    type_de_portee: str = "zone",
    severite: str = "warn",
    **reste: object,
) -> dict:
    return {
        "id": f"{regle}:instance:{identifiant}",
        "name": f"instance/{identifiant}",
        "scope": portee,
        "scope_type": type_de_portee,
        "rule": regle,
        "field": "public_addresses",
        "severity": severite,
        "detail": "a public address is attached",
        **reste,
    }


def _comparer(
    actuels: list[dict],
    anciens: list[dict] | None,
    portees: list[dict] | None = None,
) -> dict:
    return audit_changes(
        actuels,
        scopes_measured=PORTEES if portees is None else portees,
        now=MAINTENANT,
        previous=anciens,
    )


# ---- Les trois ensembles -------------------------------------------------


def test_deux_audits_sur_un_parc_inchange_ne_produisent_ni_nouveau_ni_resolu() -> None:
    """C'est la propriété qui rend l'outil lisible le lendemain."""
    constats = [_constat(), _constat(regle="required_tags")]

    changements = _comparer(constats, constats)

    assert changements["counts"]["new"] == 0
    assert changements["counts"]["resolved"] == 0
    assert changements["counts"]["persisting"] == 2


def test_un_constat_apparu_est_nouveau_et_porte_sa_premiere_vue() -> None:
    """Un constat neuf est daté d'aujourd'hui, puisque c'est aujourd'hui qu'il est vu."""
    changements = _comparer([_constat()], [])

    assert changements["counts"]["new"] == 1
    assert changements["new"][0]["first_seen"] == MAINTENANT


def test_un_constat_disparu_dans_une_portee_lue_est_resolu() -> None:
    """La zone a répondu et le constat n'y est plus : là, on peut conclure."""
    changements = _comparer([], [_constat()])

    assert changements["counts"]["resolved"] == 1
    assert changements["resolved"][0]["seen_resolved_at"] == MAINTENANT
    assert changements["counts"]["unmeasured"] == 0


# ---- Le refus central ----------------------------------------------------


def test_un_constat_dont_la_portee_na_pas_repondu_nest_pas_resolu() -> None:
    """**La pire ligne qu'un tel rapport puisse écrire.**

    Annoncer « résolu » dit à quelqu'un que son problème est réglé alors que
    personne n'a regardé. Le constat sort en non mesuré, avec ce qui l'y met.
    """
    ancien = _constat(portee="fr-par-2")

    changements = _comparer([], [ancien], portees=[{"type": "zone", "name": "fr-par-1"}])

    assert changements["counts"]["resolved"] == 0
    assert changements["counts"]["unmeasured"] == 1
    assert changements["unmeasured"][0]["reason"] == "its scope was not measured by this run"


def test_un_constat_conserve_sans_portee_ne_se_conclut_pas_non_plus() -> None:
    """Un rapport conservé trop pauvre pour être comparé le dit, il ne tranche pas."""
    ancien = _constat()
    del ancien["scope_type"]

    changements = _comparer([], [ancien])

    assert changements["counts"]["resolved"] == 0
    assert changements["unmeasured"][0]["reason"] == (
        "the kept finding does not say which scope it was in"
    )


# ---- Ce que les exceptions changent, et ce qu'elles ne changent pas -------


def test_un_constat_excuse_persiste_et_nest_pas_resolu() -> None:
    """Une exception change un statut, elle ne règle pas le problème (#235)."""
    hier = [_constat()]
    aujourdhui = [_constat(status="suppressed", suppressed_by="platform-team")]

    changements = _comparer(aujourdhui, hier)

    assert changements["counts"]["resolved"] == 0
    assert changements["counts"]["persisting"] == 1
    assert changements["persisting"][0]["status"] == "suppressed"


# ---- La première vue -----------------------------------------------------


def test_la_premiere_vue_remonte_aussi_loin_que_lappelant_a_garde() -> None:
    """Recopiée, jamais réécrite à la date du jour."""
    changements = _comparer([_constat()], [_constat(first_seen=HIER)])

    assert changements["persisting"][0]["first_seen"] == HIER


def test_une_premiere_vue_absente_nest_pas_inventee() -> None:
    """La collection ne tient pas d'historique : ce qu'elle n'a pas, elle ne le fabrique pas."""
    changements = _comparer([_constat()], [_constat()])

    assert "first_seen" not in changements["persisting"][0]


def test_aucun_resultat_ne_porte_de_champ_since() -> None:
    """« Depuis la dernière fois » ne se dérive de rien de ce qui est ici."""
    changements = _comparer([_constat()], [_constat(first_seen=HIER)])

    assert "since" not in changements


# ---- Le premier run ------------------------------------------------------


def test_le_premier_run_est_une_reference_et_le_dit() -> None:
    """Aucun run précédent n'est pas un run précédent sans constat.

    Tout annoncer comme nouveau noierait la première lecture sous ce qu'elle
    sert à établir ; tout annoncer comme persistant affirmerait l'avoir déjà vu.
    """
    changements = _comparer([_constat()], None)

    assert changements["baseline"] is True
    assert changements["counts"]["new"] == 0
    assert changements["counts"]["current"] == 1
    assert changements["current"][0]["first_seen"] == MAINTENANT


def test_un_run_precedent_sans_constat_nest_pas_une_reference() -> None:
    """Une liste vide dit « j'ai regardé et il n'y avait rien », `none` dit autre chose."""
    changements = _comparer([_constat()], [])

    assert changements["baseline"] is False
    assert changements["counts"]["new"] == 1


# ---- Les refus d'entrée --------------------------------------------------


def test_un_constat_sans_identite_est_refuse() -> None:
    """Sans identité il serait neuf à chaque run, et `nouveau` ne dirait plus rien."""
    with pytest.raises(Exception, match="sans `id`"):
        _comparer([{"name": "instance/web-01", "severity": "warn"}], [])


def test_deux_constats_de_meme_identite_dans_un_run_sont_refuses() -> None:
    """Une identité qui ne distingue plus rendrait le rapport dépendant de l'ordre."""
    with pytest.raises(Exception, match="deux fois l'identité"):
        _comparer([_constat(), _constat()], [])


def test_des_zones_mesurees_qui_ne_sont_pas_une_liste_sont_refusees() -> None:
    """Une chaîne passerait le test d'appartenance caractère par caractère."""
    with pytest.raises(Exception, match="portées mesurées sont une liste"):
        audit_changes([], scopes_measured="fr-par-1", now=MAINTENANT, previous=[])


# ---- Le verdict ----------------------------------------------------------


def test_un_parc_inchange_rend_quiet() -> None:
    """La propriété que le jalon exige : le second run ne produit presque rien."""
    constats = [_constat()]

    assert changes_verdict(_comparer(constats, constats)) == "quiet"


def test_un_nouveau_constat_bloquant_rend_action_required() -> None:
    assert changes_verdict(_comparer([_constat(severite="fail")], [])) == "action_required"


def test_une_portee_muette_pese_autant_quun_nouveau_constat_bloquant() -> None:
    """Une zone muette n'est pas une bonne nouvelle.

    La présenter comme un parc calme est le vert sur zéro fichier examiné.
    """
    changements = _comparer(
        [],
        [_constat(portee="fr-par-2")],
        portees=[{"type": "zone", "name": "fr-par-1"}],
    )

    assert changes_verdict(changements) == "action_required"


def test_un_nouveau_constat_deja_excuse_ne_reclame_pas_daction() -> None:
    """Quelqu'un l'a explicitement accepté : le remonter en action serait le nier."""
    neuf = [_constat(severite="fail", status="suppressed", suppressed_by="platform-team")]

    assert changes_verdict(_comparer(neuf, [])) == "changed"


def test_un_constat_resolu_rend_changed() -> None:
    assert changes_verdict(_comparer([], [_constat()])) == "changed"


def test_un_premier_run_ne_se_dit_ni_calme_ni_alarmant() -> None:
    assert changes_verdict(_comparer([_constat()], None)) == "baseline"


def test_un_verdict_ne_se_calcule_pas_sur_autre_chose() -> None:
    """Un appelant qui pourrait forcer le niveau produirait un rapport qui se ment."""
    with pytest.raises(Exception, match="audit_changes"):
        changes_verdict("quiet")


# ---- Le défaut de #272, dans les deux sens --------------------------------


def test_un_constat_kapsule_devient_resolu_quand_sa_region_a_repondu() -> None:
    """**Le défaut que la 0.8.0 portait avant #272.**

    `fleet_audit` ne transmettait que les zones Instance, donc la région d'un
    cluster n'était jamais dans les portées mesurées : un constat Kapsule
    disparu sortait en « non mesuré » alors que la lecture avait parfaitement
    répondu.
    """
    ancien = _constat(portee="fr-par", type_de_portee="region")

    changements = _comparer([], [ancien], portees=[REGION])

    assert changements["counts"]["resolved"] == 1
    assert changements["counts"]["unmeasured"] == 0


def test_une_zone_et_une_region_de_meme_nom_ne_se_confondent_pas() -> None:
    """Le type est ce qui les distingue, et rien d'autre ne le peut.

    Comparer les noms nus ferait passer un constat de région pour mesuré parce
    qu'une zone au nom voisin aurait répondu. Ici la région n'a pas été lue : le
    constat ne peut pas être conclu.
    """
    ancien = _constat(portee="fr-par", type_de_portee="region")

    changements = _comparer([], [ancien], portees=[{"type": "zone", "name": "fr-par"}])

    assert changements["counts"]["resolved"] == 0
    assert changements["unmeasured"][0]["reason"] == "its scope was not measured by this run"
