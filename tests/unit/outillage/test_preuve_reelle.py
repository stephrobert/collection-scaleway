"""Un tableau de preuve qui se trompe se lit exactement comme un tableau juste.

Le guide Kubernetes allait publier une matrice écrite à la main, et l'audit du
15 septembre 2026 a nommé la classe de défaut qu'elle aurait rejointe : une
affirmation qui survit à ce qui la mesurait.

Elle est donc dérivée de la transcription du tir réel. Ce fichier tient les
trois façons dont ce rapprochement peut mentir sans planter :

```text
il attribue mal      une route que deux modules portent crédite le premier
il ne mesure rien    un préfixe mal dérivé écarte tout, et tout sort « non atteint »
il attribue en vain  une ligne sans agent est comptée comme si on savait qui l'a émise
```
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from preuve_reelle import (
    PreuveError,
    Tir,
    _motif,
    _service,
    lire,
    rapprocher,
    tir_le_plus_recent,
)


def _ligne(seq: int, methode: str, chemin: str, agent: str) -> str:
    return json.dumps(
        {
            "seq": seq,
            "t": "2026-09-14T10:55:24Z",
            "method": methode,
            "path": chemin,
            "status": 200,
            "req": {"headers": {"User-Agent": agent}},
        }
    )


# ---- Ce que la transcription réelle porte --------------------------------


def test_le_tir_kapsule_credite_chaque_module_quune_route_propre_prouve() -> None:
    """La mesure, sur le fichier versionné, et pas sur un exemple fabriqué.

    Elle fixe ce que le guide publie : un module dont une route n'appartient
    qu'à lui est prouvé, et le tableau le dit sans que personne l'ait tapé.
    """
    resultat = rapprocher("k8s", "v1", lire(tir_le_plus_recent("k8s")))

    assert "k8s_cluster_info" in resultat.atteints
    assert "k8s_node_reboot_action" in resultat.atteints
    assert resultat.orphelines == ()


def test_une_lecture_que_deux_modules_portent_ne_credite_personne() -> None:
    """**Le cas qui a démenti le tableau écrit à la main.**

    `GET /pools/{id}` est portée par la lecture unitaire et par le MANAGE qui
    lit avant d'écrire (ADR-003). La requête a circulé, et rien ne dit lequel
    des deux l'a émise : créditer le premier par ordre alphabétique aurait
    rendu un « oui » tiré au sort.

    Le MANAGE reste prouvé : son PATCH n'appartient qu'à lui.
    """
    resultat = rapprocher("k8s", "v1", lire(tir_le_plus_recent("k8s")))

    assert "k8s_pool_info" in resultat.indistincts
    assert "k8s_pool" in resultat.atteints


def test_un_module_quaucune_route_natteint_est_nomme() -> None:
    """Ce que le tir ne prouve pas doit se lire aussi fort que ce qu'il prouve.

    Un tableau qui ne listerait que les succès serait une plaquette.
    """
    resultat = rapprocher("k8s", "v1", lire(tir_le_plus_recent("k8s")))

    assert "k8s_node_replace_action" in resultat.muets


# ---- Les trois façons de mentir sans planter ------------------------------


def test_un_rapprochement_qui_ne_rapproche_rien_le_dit(tmp_path: Path) -> None:
    """**Le défaut que ce script a eu, et qui n'a rien affiché.**

    Le préfixe dérivé valait `/k8s/v1/regions/{region}/`, gabarit qui ne
    préfixe aucun chemin réel. Toutes les routes du tir étaient écartées avant
    tout rapprochement, et chaque module sortait « non atteint » : un tableau
    parfaitement lisible, et entièrement faux.

    Le critère est l'incohérence et non le zéro. Un tir qui n'émet rien sur ce
    produit est un fait ; un tir qui en émet et dont rien ne se rapproche est
    une panne d'outil.

    **Le filtre est neutralisé, pas la garde.** Deux versions de cette garde
    ont compté les routes « du produit » en réutilisant le filtre suspect :
    chacune était donc inerte exactement dans le cas qu'elle devait attraper,
    et ce test l'a dit les deux fois. Son critère ne consulte plus rien : des
    requêtes ont circulé, et il n'en est sorti ni preuve, ni doute, ni
    orpheline.
    """
    tir = Tir(
        fichier=tmp_path / "kapsule-2026-09-14.jsonl",
        date="2026-09-14",
        routes={("GET", "/k8s/v1/regions/fr-par/clusters"): 1},  # type: ignore[arg-type]
    )

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("preuve_reelle._service", lambda _: "/k8s/v1/regions/{region}/")
        with pytest.raises(PreuveError, match="ne reconnaît plus"):
            rapprocher("k8s", "v1", tir)


def test_une_requete_sans_agent_est_refusee(tmp_path: Path) -> None:
    """Une ligne qu'on ne sait pas attribuer ne se compte d'aucun côté.

    La transcription porte trois agents : la collection, le provider Terraform
    qui a bâti la plateforme, et celui des empreintes de résidu. Compter une
    ligne muette reviendrait à créditer la collection de ce que Terraform a
    fait, ce qui est l'inverse de ce que ce tableau montre.
    """
    chemin = tmp_path / "kapsule-2026-09-14.jsonl"
    chemin.write_text(
        json.dumps(
            {
                "seq": 1,
                "t": "2026-09-14T10:00:00Z",
                "method": "GET",
                "path": "/k8s/v1/regions/fr-par/clusters",
                "req": {"headers": {}},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(PreuveError, match="ne porte pas d'agent"):
        lire(chemin)


def test_seul_lagent_de_la_collection_est_compte(tmp_path: Path) -> None:
    """Terraform a bâti la plateforme, et il n'entre pas dans cette preuve."""
    chemin = tmp_path / "kapsule-2026-09-14.jsonl"
    chemin.write_text(
        "\n".join(
            (
                _ligne(1, "GET", "/k8s/v1/regions/fr-par/clusters", "scaleway-sdk-python/2.11.0"),
                _ligne(
                    2,
                    "POST",
                    "/k8s/v1/regions/fr-par/clusters",
                    "scaleway-sdk-go/v1.0.0 terraform-provider/2.81.0",
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    tir = lire(chemin)

    assert tir.routes == {("GET", "/k8s/v1/regions/fr-par/clusters"): 1}


# ---- Les bornes du rapprochement -----------------------------------------


def test_un_gabarit_ne_deborde_pas_sur_le_segment_suivant() -> None:
    """Sans borne, `/clusters/{id}` avalerait `/clusters/{id}/nodes`.

    Deux modules se disputeraient alors la même route, et la lecture unitaire
    serait créditée de ce que la liste des nœuds a fait.
    """
    motif = _motif("/k8s/v1/regions/{region}/clusters/{cluster_id}")

    assert motif.match("/k8s/v1/regions/fr-par/clusters/abc")
    assert not motif.match("/k8s/v1/regions/fr-par/clusters/abc/nodes")


def test_le_service_est_le_premier_segment_et_pas_le_prefixe_commun() -> None:
    """Le préfixe commun de ces deux gabarits garde `{region}`.

    Il ne préfixe alors aucun chemin réel, et c'est la forme exacte du défaut
    ci-dessus, prise à sa source plutôt qu'à son symptôme.
    """
    portees = {
        "a": (("GET", "/k8s/v1/regions/{region}/clusters"),),
        "b": (("GET", "/k8s/v1/regions/{region}/pools/{pool_id}"),),
    }

    assert _service(portees) == "/k8s/"  # type: ignore[arg-type]


def test_une_route_dune_version_dapi_que_le_plan_ne_porte_pas_est_orpheline(
    tmp_path: Path,
) -> None:
    """Le jour où `/k8s/v2/` existera, la collection ne l'appellera pas en silence.

    Un filtre calé sur `/k8s/v1/` l'aurait écartée comme si elle concernait un
    autre produit. Le premier segment la garde dans le champ, où elle ressort
    comme ce qu'elle est : une route émise qu'aucun module ne déclare.
    """
    chemin = tmp_path / "kapsule-2026-09-14.jsonl"
    chemin.write_text(
        _ligne(1, "GET", "/k8s/v2/regions/fr-par/clusters", "scaleway-sdk-python/2.11.0") + "\n",
        encoding="utf-8",
    )

    resultat = rapprocher("k8s", "v1", lire(chemin))

    assert resultat.orphelines == (("GET", "/k8s/v2/regions/fr-par/clusters"),)


def test_une_transcription_renommee_sans_etre_rejouee_est_refusee(tmp_path: Path) -> None:
    """Une preuve datée d'aujourd'hui sur des mesures d'hier n'est pas une preuve.

    Renommer un fichier coûte une seconde, et le tableau publierait la nouvelle
    date sans qu'une seule requête ait été rejouée.
    """
    chemin = tmp_path / "kapsule-2026-12-25.jsonl"
    chemin.write_text(
        _ligne(1, "GET", "/k8s/v1/regions/fr-par/clusters", "scaleway-sdk-python/2.11.0") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(PreuveError, match="s'annonce du 2026-12-25"):
        lire(chemin)
