"""Ce qui a bougé, agrégé, et le silence quand rien n'a bougé."""

from __future__ import annotations

import pytest

from ansible_collections.stephrobert.scaleway.plugins.filter.fleet_changes import (
    changes_summary,
    summary_verdict,
    worst_level,
)

MAINTENANT = "2026-09-14T10:00:00Z"


def _constat(severite: str = "warn", identifiant: str = "aaaa", **reste: object) -> dict:
    return {
        "id": f"public_ip:instance:{identifiant}",
        "name": f"instance/{identifiant}",
        "zone": "fr-par-1",
        "rule": "public_ip",
        "severity": severite,
        "detail": "a public address is attached",
        **reste,
    }


def _changements(**reste: object) -> dict:
    base: dict = {
        "baseline": False,
        "new": [],
        "persisting": [],
        "resolved": [],
        "unmeasured": [],
        "counts": {"new": 0, "persisting": 0, "resolved": 0, "unmeasured": 0, "current": 0},
    }
    base.update(reste)
    compte = base["counts"]
    for cle in ("new", "persisting", "resolved", "unmeasured"):
        compte[cle] = len(base[cle])
    return base


def _diff(**reste: object) -> dict:
    return {"new": [], "removed": [], "changed": [], "zones_not_compared": {}, **reste}


# ---- La règle exécutable du jalon ----------------------------------------


def test_un_parc_inchange_sort_quiet() -> None:
    """**La règle du jalon, et elle est exécutable.**

    La 0.8.0 ne doit pas augmenter le nombre de notifications, elle doit
    augmenter le rapport signal sur bruit. Sans ce contrôle, « ne pas spammer »
    est une phrase dans une issue.
    """
    bilan = changes_summary(
        _changements(persisting=[_constat()]),
        diff=_diff(),
        previous_findings=[_constat()],
    )

    assert summary_verdict(bilan) == "quiet"
    assert bilan["new_findings"] == 0
    assert bilan["resolved_findings"] == 0
    assert bilan["infrastructure_changes"] == 0


def test_un_constat_qui_persiste_ne_reclame_pas_une_action_chaque_matin() -> None:
    """Il a déjà été rapporté hier. Le remonter au même rang est le bruit à retirer."""
    bilan = changes_summary(
        _changements(persisting=[_constat("fail")]),
        diff=_diff(),
        previous_findings=[_constat("fail")],
    )

    assert bilan["persistent_failures"] == 1
    assert summary_verdict(bilan) == "quiet"


# ---- Ce qui réclame une action -------------------------------------------


def test_un_constat_bloquant_neuf_reclame_une_action() -> None:
    bilan = changes_summary(_changements(new=[_constat("fail")]), diff=_diff())

    assert summary_verdict(bilan) == "action_required"


def test_un_constat_bloquant_neuf_nest_pas_tu_par_un_autre_qui_se_resout() -> None:
    """**Le delta de sévérité ne décide de rien.**

    Un `fail` qui apparaît pendant qu'un autre se résout laisse le compte à
    l'identique : décider sur le delta ferait taire le constat neuf, masqué par
    la bonne nouvelle du voisin.
    """
    bilan = changes_summary(
        _changements(
            new=[_constat("fail", "neuf")],
            resolved=[_constat("fail", "ancien")],
        ),
        diff=_diff(),
        previous_findings=[_constat("fail", "ancien")],
    )

    assert bilan["severities"]["fail"]["delta"] == 0
    assert bilan["new_failures"] == 1
    assert summary_verdict(bilan) == "action_required"


def test_une_zone_muette_pese_autant_quun_constat_bloquant() -> None:
    """Une zone muette n'est pas une bonne nouvelle."""
    bilan = changes_summary(_changements(), diff=_diff(), unmeasured_zones=["nl-ams-2"])

    assert summary_verdict(bilan) == "action_required"


def test_un_constat_non_conclu_pese_autant() -> None:
    """Un constat dont la zone n'a pas répondu n'est pas un constat réglé (#234)."""
    bilan = changes_summary(_changements(unmeasured=[_constat()]), diff=_diff())

    assert bilan["not_concluded"] == 1
    assert bilan["resolved_findings"] == 0
    assert summary_verdict(bilan) == "action_required"


def test_une_exception_perimee_reclame_une_action() -> None:
    """Son échéance est l'information, et le jour où elle passe est le seul moment utile."""
    bilan = changes_summary(
        _changements(), diff=_diff(), expired_exceptions=[{"rule": "public_ip"}]
    )

    assert summary_verdict(bilan) == "action_required"


def test_une_zone_incomparable_pese_autant() -> None:
    """Deux instantanés qui ne couvrent pas la même zone ne disent rien de cette zone."""
    bilan = changes_summary(
        _changements(), diff=_diff(zones_not_compared={"pl-waw-1": "did not answer"})
    )

    assert summary_verdict(bilan) == "action_required"


# ---- Ce qui est informatif ------------------------------------------------


def test_un_changement_dinfrastructure_seul_rend_changed() -> None:
    bilan = changes_summary(_changements(), diff=_diff(new=[{"id": "x", "kind": "instance"}]))

    assert bilan["infrastructure_changes"] == 1
    assert summary_verdict(bilan) == "changed"


def test_un_constat_resolu_seul_rend_changed() -> None:
    bilan = changes_summary(_changements(resolved=[_constat()]), diff=_diff())

    assert summary_verdict(bilan) == "changed"


# ---- Ce qui n'est pas mesuré n'est pas zéro ------------------------------


def test_sans_instantane_rendu_linfrastructure_nest_pas_comptee_a_zero() -> None:
    """« On n'a pas comparé » n'est pas « rien n'a bougé »."""
    bilan = changes_summary(_changements(), diff=None)

    assert bilan["infrastructure_changes"] is None
    assert bilan["zones_not_compared"] is None
    assert summary_verdict(bilan) == "quiet"


def test_sans_constats_gardes_un_delta_de_severite_nest_pas_zero() -> None:
    """Écrire `(+0)` affirmerait qu'elle n'a pas bougé, ce que rien ne soutient."""
    bilan = changes_summary(_changements(persisting=[_constat("fail")]), diff=_diff())

    assert bilan["severities"]["fail"]["now"] == 1
    assert bilan["severities"]["fail"]["delta"] is None


def test_un_delta_se_calcule_quand_le_run_precedent_est_rendu() -> None:
    bilan = changes_summary(
        _changements(new=[_constat("warn", "b")], persisting=[_constat("warn", "a")]),
        diff=_diff(),
        previous_findings=[_constat("warn", "a")],
    )

    assert bilan["severities"]["warn"] == {"now": 2, "delta": 1}


def test_un_constat_excuse_ne_pese_dans_aucune_severite() -> None:
    """Quelqu'un l'a explicitement accepté ; le compter nierait son exception."""
    bilan = changes_summary(
        _changements(persisting=[_constat("fail", status="suppressed")]),
        diff=_diff(),
        previous_findings=[],
    )

    assert bilan["severities"] == {}
    assert bilan["persistent_failures"] == 0


# ---- Aucun score composite ------------------------------------------------


def test_le_bilan_ne_porte_aucun_score_composite() -> None:
    """Un nombre composite ne se remonte pas jusqu'à ce qui l'a fait bouger.

    Le contrôle porte sur la forme rendue : chaque clé compte une chose nommée,
    et aucune n'agrège les autres.
    """
    bilan = changes_summary(_changements(), diff=_diff())

    assert not any("score" in cle for cle in bilan)
    assert "total" not in bilan


# ---- Le pire de plusieurs niveaux ----------------------------------------


def test_le_pire_niveau_lemporte() -> None:
    """Prendre le plus bas laisserait une moitié calme masquer l'autre."""
    assert worst_level(["quiet", "action_required", "changed"]) == "action_required"
    assert worst_level(["quiet", "changed"]) == "changed"
    assert worst_level(["baseline", "quiet"]) == "quiet"


def test_un_niveau_inconnu_est_refuse() -> None:
    """Un niveau qu'on ne sait pas ordonner se rangerait au hasard."""
    with pytest.raises(Exception, match="niveau"):
        worst_level(["quiet", "presque"])


# ---- Les refus d'entrée ---------------------------------------------------


def test_un_bilan_ne_se_calcule_pas_sur_autre_chose() -> None:
    with pytest.raises(Exception, match="audit_changes"):
        changes_summary("rien")


def test_un_verdict_ne_se_calcule_pas_sur_autre_chose() -> None:
    """Un appelant qui pourrait forcer le niveau produirait un rapport qui se ment."""
    with pytest.raises(Exception, match="bilan"):
        summary_verdict("quiet")


def test_un_diff_qui_nen_est_pas_un_est_refuse() -> None:
    with pytest.raises(Exception, match="fleet_diff"):
        changes_summary(_changements(), diff=[])
