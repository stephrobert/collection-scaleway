"""Un manque de feint est ce que feint a décliné, pas une différence d'ensembles.

La version précédente soustrayait les modules joués et affirmait sous sa liste
que **chacun avait été appelé des deux côtés**. Mesuré le 2026-09-11 : deux sur
cinq l'avaient été. Les autres étaient des tâches que le playbook saute faute de
ressource à viser, et un module qu'aucune tâche ne nommait de ce côté.

L'écart importe parce que cette liste est présentée comme le matériau d'une
issue de feint : trois cinquièmes seraient partis chez le mauvais projet.
"""

from __future__ import annotations

from typing import Any

import example_coverage
import pytest


def _run(cible: str, joues: list[str], **reste: Any) -> dict[str, Any]:
    return {
        "cible": cible,
        "run_id": "abc",
        "horodatage": "2026-09-11T00:00:00+00:00",
        "modules_joues": sorted(joues),
        "modules_declines": [],
        "modules_sautes": [],
        "modules_en_echec": [],
        "routes_non_emulees": [],
        **reste,
    }


def _mesure(reel: dict[str, Any], feint: dict[str, Any]) -> dict[str, Any]:
    return {"runs": {"reel": reel, "emulateur": feint}}


def test_un_module_decline_par_feint_est_un_manque() -> None:
    ecart = example_coverage.comparer(
        _mesure(
            _run("reel", ["instance_volume_type_info"]),
            _run("emulateur", [], modules_declines=["instance_volume_type_info"]),
        )
    )
    assert ecart["manques_de_feint"] == ["instance_volume_type_info"]


def test_un_module_saute_cote_feint_nest_pas_un_manque_de_feint() -> None:
    """La stack ne bâtit pas de certificats contre l'émulateur : personne n'a appelé."""
    ecart = example_coverage.comparer(
        _mesure(
            _run("reel", ["lb_certificate"]),
            _run("emulateur", [], modules_sautes=["lb_certificate"]),
        )
    )
    assert ecart["manques_de_feint"] == []
    assert ecart["sautes_cote_feint"] == ["lb_certificate"]


def test_un_module_quaucune_tache_ne_nomme_est_publie_a_part() -> None:
    """C'est un défaut du playbook ou de ses conditions, pas de l'émulateur."""
    ecart = example_coverage.comparer(
        _mesure(_run("reel", ["instance_server_action"]), _run("emulateur", []))
    )
    assert ecart["manques_de_feint"] == []
    assert ecart["jamais_nommes_cote_feint"] == ["instance_server_action"]


def test_un_echec_nest_pas_un_refus_de_route() -> None:
    ecart = example_coverage.comparer(
        _mesure(
            _run("reel", ["lb_frontend"]),
            _run("emulateur", [], modules_en_echec=["lb_frontend"]),
        )
    )
    assert ecart["manques_de_feint"] == []
    assert ecart["en_echec_cote_feint"] == ["lb_frontend"]


def test_le_cas_mesure_du_2026_09_11_se_range_par_ce_qui_est_arrive() -> None:
    """Les modules que le run réel a joués, rangés par leur sort côté émulateur.

    C'est la mesure qui a fondé #189, rejouée ici sans compte ni émulateur.
    """
    ecart = example_coverage.comparer(
        _mesure(
            _run(
                "reel",
                [
                    "instance_image",
                    "instance_server_action",
                    "instance_server_type_availability_info",
                    "instance_volume_type_info",
                    "lb_certificate",
                ],
            ),
            _run(
                "emulateur",
                [],
                modules_declines=[
                    "instance_server_type_availability_info",
                    "instance_volume_type_info",
                ],
                modules_sautes=["instance_image", "lb_certificate"],
            ),
        )
    )
    assert ecart["manques_de_feint"] == [
        "instance_server_type_availability_info",
        "instance_volume_type_info",
    ]
    assert ecart["sautes_cote_feint"] == ["instance_image", "lb_certificate"]
    assert ecart["jamais_nommes_cote_feint"] == ["instance_server_action"]


def test_un_artefact_anterieur_au_decoupage_le_dit_plutot_que_de_rendre_une_liste_vide() -> None:
    """Rien n'a été mesuré n'est pas rien n'a manqué.

    Un artefact d'avant #189 ne porte ni `modules_declines`, ni `modules_sautes`,
    ni `modules_en_echec`. Les lire comme vides publierait « feint ne décline
    rien », qui est une affirmation.
    """
    ancien = _run("emulateur", [])
    for champ in ("modules_declines", "modules_sautes", "modules_en_echec"):
        del ancien[champ]

    ecart = example_coverage.comparer(_mesure(_run("reel", ["instance_image"]), ancien))

    assert ecart["detaille"] is False
    rendu = example_coverage.rendre_comparaison(ecart)
    assert "antérieur au découpage" in rendu
    assert "matériau d'une issue feint" not in rendu


def test_le_rendu_ne_promet_un_materiau_que_pour_ce_qui_a_ete_decline() -> None:
    ecart = example_coverage.comparer(
        _mesure(
            _run("reel", ["instance_volume_type_info", "lb_certificate"]),
            _run(
                "emulateur",
                [],
                modules_declines=["instance_volume_type_info"],
                modules_sautes=["lb_certificate"],
            ),
        )
    )
    rendu = example_coverage.rendre_comparaison(ecart)

    # La promesse ne couvre que la première liste, et le dit.
    avant = rendu.index("matériau d'une issue feint")
    apres = rendu.index("sautés côté feint")
    assert avant < apres
    assert "rien d'autre ici ne l'est" in rendu
    assert "Ce n'est pas un manque de l'émulateur" in rendu


def test_la_projection_laisse_passer_ce_que_la_comparaison_lit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La projection décide de ce que le rapport pourra dire.

    `mesurer` réduit chaque run à quelques clés. Elle ne retenait pas
    `routes_non_emulees`, donc la section « routes que feint déclare ne pas
    servir » cherchait dans le vide : elle ne s'est jamais affichée, alors que
    l'artefact portait la réponse depuis le début.

    **Les artefacts sont injectés, pas lus sur le disque.** La première version
    de ce test lisait `build/example/`, que `/falsify` ne copie pas dans son
    arbre de travail : la boucle ne s'exécutait sur rien et le test restait vert
    pendant que la garde était neutralisée. Un test qui mesure l'état du dépôt
    plutôt que la fonction ne mesure rien du tout.
    """
    artefact = _run(
        "emulateur",
        ["instance_server_info"],
        modules_declines=["instance_volume_type_info"],
        modules_sautes=["lb_certificate"],
        modules_en_echec=["lb_frontend"],
        routes_non_emulees=["ListVolumesTypes"],
    )
    monkeypatch.setattr(example_coverage, "artefacts", lambda: {"emulateur": artefact})

    projete = example_coverage.mesurer()["runs"]["emulateur"]

    for champ in (
        "modules_declines",
        "modules_sautes",
        "modules_en_echec",
        "routes_non_emulees",
    ):
        assert champ in projete, (
            f"{champ} est dans l'artefact et la projection le perd, "
            "donc la comparaison ne peut pas le lire"
        )
    assert projete["routes_non_emulees"] == ["ListVolumesTypes"]
