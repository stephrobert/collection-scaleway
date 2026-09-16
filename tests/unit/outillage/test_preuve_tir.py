"""« Testé sur Scaleway » doit rougir quand ce n'est pas vrai de ce commit.

Le dépôt séparait déjà unité, émulateur et cloud réel, et ne prétendait pas que
l'émulateur remplace le compte. Le trou était ailleurs : **rien n'attestait par
machine que le commit publié avait passé le scénario réel**. Une version pouvait
partir sur la foi d'un tir fait trois semaines plus tôt, sur un autre arbre
(#96).

Quatre façons de publier sur une preuve qui n'en est pas, et chacune a son
refus :

```text
elle manque          personne n'a jamais tiré sur ce commit
elle désigne un autre commit   un tir voisin passe pour celui-ci
elle dit FAIL        le tir a eu lieu et n'a pas passé
elle a laissé du résidu        le compte est facturé pour ce qui reste
```
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import preuve_tir
import pytest

SHA = "0123456789abcdef0123456789abcdef01234567"


def _artefact(chemin: Path, **reste: object) -> Path:
    """Un artefact de run tel que `scripts/example.py` l'écrit."""
    charge = {
        "cible": "reel",
        "horodatage": "2026-09-16T10:00:00+00:00",
        "residu": "aucun",
        "modules_joues": ["instance_server_info", "instance_snapshot"],
        "modules_en_echec": [],
        "run_id": "abc123def",
        **reste,
    }
    chemin.write_text(json.dumps(charge), encoding="utf-8")
    return chemin


def _preuve(dossier: Path, **reste: object) -> Path:
    charge = {
        "commit": SHA,
        "date": "2026-09-16",
        "verdict": "PASS",
        "residu": "aucun",
        "modules_joues": 2,
        **reste,
    }
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"tir-{charge['date']}-{str(charge['commit'])[:9]}.json"
    chemin.write_text(json.dumps(charge), encoding="utf-8")
    return chemin


# ---- Ce que le scellement fait, et refuse de faire ------------------------


def test_un_artefact_demulateur_ne_vaut_pas_preuve(tmp_path: Path) -> None:
    """L'émulateur prouve la forme d'un run, jamais le compte (ADR-006).

    Les deux artefacts ont exactement la même structure et le même nom de
    champs : seule la cible les distingue, et c'est pour ça que ce refus existe
    plutôt que de compter sur la vigilance.
    """
    artefact = _artefact(tmp_path / "dernier-emulateur.json", cible="emulateur")

    with pytest.raises(preuve_tir.PreuveTirError, match="cible 'emulateur'"):
        preuve_tir.sceller(artefact, commit=SHA)


def test_le_verdict_se_derive_du_run_et_ne_se_declare_pas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Une preuve qui se dirait bonne toute seule ne prouverait rien.

    `verdict` n'est pas un paramètre : il sort de ce que le run a laissé, et un
    module en échec le fait basculer sans que personne ait à y penser.
    """
    monkeypatch.setattr(preuve_tir, "PREUVES", tmp_path / "preuves")
    # L'arbre du dépôt est sale pendant qu'on développe, et son refus s'ajouterait
    # à chaque test qui n'en juge pas. Il est jugé dans le sien.
    monkeypatch.setattr(preuve_tir, "_git", lambda *_: "")
    artefact = _artefact(tmp_path / "run.json", modules_en_echec=["lb_frontend"])

    chemin = preuve_tir.sceller(artefact, commit=SHA)

    assert json.loads(chemin.read_text(encoding="utf-8"))["verdict"] == "FAIL"


def test_un_residu_fait_basculer_le_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le compte est facturé : ce qui reste compte autant qu'un module rouge."""
    monkeypatch.setattr(preuve_tir, "PREUVES", tmp_path / "preuves")
    monkeypatch.setattr(preuve_tir, "_git", lambda *_: "")
    artefact = _artefact(tmp_path / "run.json", residu="3 ressource(s)")

    chemin = preuve_tir.sceller(artefact, commit=SHA)

    assert json.loads(chemin.read_text(encoding="utf-8"))["verdict"] == "FAIL"


# ---- Les quatre façons de publier sur une preuve qui n'en est pas ---------


def test_sans_preuve_la_publication_est_refusee(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**Le défaut que #96 nommait.** Rien ne disait « ce commit n'a pas tiré ».

    C'est le cas le plus courant, et le plus silencieux : la porte de release
    passait, et « testé sur Scaleway » restait une phrase.
    """
    monkeypatch.setattr(preuve_tir, "PREUVES", tmp_path / "vide")

    assert preuve_tir.refus(SHA), "un commit sans preuve doit être refusé"


def test_une_preuve_dun_autre_commit_ne_vaut_pas_pour_celui_ci(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C'est exactement le scénario que la lie au SHA sert à empêcher.

    Un tir de la veille, sur l'arbre d'avant, est une preuve parfaitement
    valide : elle ne parle simplement pas de ce qu'on publie.
    """
    dossier = tmp_path / "preuves"
    monkeypatch.setattr(preuve_tir, "PREUVES", dossier)
    _preuve(dossier, commit="ffffffffffffffffffffffffffffffffffffffff")

    assert preuve_tir.refus(SHA)


def test_une_preuve_en_echec_est_refusee(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Publier dessus dirait le contraire de ce qui a été mesuré."""
    dossier = tmp_path / "preuves"
    monkeypatch.setattr(preuve_tir, "PREUVES", dossier)
    _preuve(dossier, verdict="FAIL")

    assert preuve_tir.refus(SHA)


def test_une_preuve_qui_a_laisse_du_residu_est_refusee(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le compte est facturé, et ça ne se publie pas."""
    dossier = tmp_path / "preuves"
    monkeypatch.setattr(preuve_tir, "PREUVES", dossier)
    _preuve(dossier, residu="2 ressource(s)")

    assert preuve_tir.refus(SHA)


def test_une_preuve_perimee_est_refusee(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Elle désigne bien ce commit, et l'API a pu bouger sous lui depuis.

    Ce n'est pas une durée de validité du produit : c'est une borne sur la
    distance entre ce qui a été joué et ce qui part.
    """
    dossier = tmp_path / "preuves"
    monkeypatch.setattr(preuve_tir, "PREUVES", dossier)
    _preuve(dossier, date="2026-01-01")

    assert preuve_tir.refus(SHA, aujourdhui="2026-09-16")


def test_une_preuve_fraiche_du_bon_commit_laisse_publier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La garde doit aussi savoir dire oui.

    Sans ce cas, elle pourrait refuser tout le temps et personne ne le saurait
    avant la prochaine publication.
    """
    dossier = tmp_path / "preuves"
    monkeypatch.setattr(preuve_tir, "PREUVES", dossier)
    _preuve(dossier)

    assert preuve_tir.refus(SHA, aujourdhui="2026-09-16") == []


def test_un_arbre_sale_ne_se_scelle_pas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """La preuve nomme un SHA, et le tir aurait tourné sur autre chose.

    Mesuré le 16 septembre 2026 : une preuve a été scellée sur un arbre
    portant des fichiers modifiés, et elle affirmait le commit d'avant. Personne
    n'aurait pu rejouer ce qu'elle prétendait prouver.

    `release.py` refusait déjà de publier depuis un arbre sale, pour la même
    raison exactement. Le scellement ne le faisait pas, et c'est lui qui décide
    de ce que la preuve nomme.
    """
    monkeypatch.setattr(preuve_tir, "PREUVES", tmp_path / "preuves")
    monkeypatch.setattr(preuve_tir, "_git", lambda *_: " M scripts/example.py")
    artefact = _artefact(tmp_path / "run.json")

    with pytest.raises(preuve_tir.PreuveTirError, match="non versionnée"):
        preuve_tir.sceller(artefact)


def test_une_preuve_ne_peut_pas_vivre_dans_le_commit_quelle_atteste(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sinon la garde demanderait l'impossible, et finirait désactivée.

    Le tir se joue sur un arbre propre, la preuve nomme ce commit-là, et la
    commiter en crée forcément un autre. Exiger qu'elle désigne HEAD ne peut
    jamais être satisfait.

    Le décalage admis est étroit : un ancêtre dont le contenu ne diffère que
    sous `preuves/`. Tout le reste de l'arbre est celui qui a tourné.
    """
    dossier = tmp_path / "preuves"
    monkeypatch.setattr(preuve_tir, "PREUVES", dossier)
    _preuve(dossier, commit="1111111111111111111111111111111111111111")
    monkeypatch.setattr(preuve_tir, "_meme_archive_publiee", lambda ancetre, commit: True)

    assert preuve_tir.refus(SHA, aujourdhui="2026-09-16") == []


def test_un_ancetre_qui_change_autre_chose_que_la_preuve_est_refuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le décalage ne doit pas devenir une porte dérobée.

    Un commit d'écart qui touche le code est un arbre différent de celui qui a
    tourné, et la preuve ne parle plus de ce qu'on publie.

    **Le jugement se fait dans un dépôt jetable**, parce que la question est
    « que contient ce diff » et qu'y répondre demande de vrais commits. Patcher
    la fonction aurait rendu le test vert quoi qu'elle fasse, ce qui est
    exactement ce que la mutation a montré.
    """
    depot = tmp_path / "depot"
    depot.mkdir()
    lancer = lambda *a: subprocess.run(  # noqa: E731
        ["git", *a], cwd=depot, capture_output=True, check=True
    )
    lancer("init", "-q")
    lancer("config", "user.email", "t@t")
    lancer("config", "user.name", "t")
    (depot / "ansible_collections").mkdir()
    (depot / "ansible_collections" / "module.py").write_text("x = 1\n", encoding="utf-8")
    lancer("add", "-A")
    lancer("commit", "-qm", "socle")
    socle = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=depot, capture_output=True, text=True, check=True
    ).stdout.strip()

    monkeypatch.setattr(preuve_tir, "ROOT", depot)

    # Un commit qui n'ajoute qu'une preuve : l'archive publiée ne bouge pas.
    (depot / "preuves").mkdir()
    (depot / "preuves" / "tir.json").write_text("{}", encoding="utf-8")
    lancer("add", "-A")
    lancer("commit", "-qm", "la preuve")
    avec_preuve = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=depot, capture_output=True, text=True, check=True
    ).stdout.strip()

    assert preuve_tir._meme_archive_publiee(socle, avec_preuve)

    # Un commit qui touche un module : ce qu'on publierait n'est plus ce qui a tourné.
    (depot / "ansible_collections" / "module.py").write_text("x = 2\n", encoding="utf-8")
    lancer("add", "-A")
    lancer("commit", "-qm", "du code")
    avec_code = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=depot, capture_output=True, text=True, check=True
    ).stdout.strip()

    assert not preuve_tir._meme_archive_publiee(socle, avec_code), (
        "un commit qui change l'archive publiée a été accepté : un utilisateur "
        "installerait autre chose que ce qui a tourné."
    )


def test_le_perimetre_de_la_preuve_est_celui_de_larchive() -> None:
    """La preuve couvre ce qui est publié, pas le dépôt entier.

    **Le premier critère exigeait un arbre entier identique, et il était
    invivable** : corriger l'outillage de release après le tir invalidait le
    tir, donc chaque correction en réclamait un nouveau, facturé. Ce module dit
    lui-même qu'une garde impossible à satisfaire se fait désactiver dans le
    mois ; c'en était une.

    Le périmètre doit rester celui de l'archive : l'élargir laisserait un module
    changer entre le tir et la publication, ce qui est précisément ce que la
    preuve interdit.
    """
    assert preuve_tir.PUBLIE == "ansible_collections/", (
        "le périmètre de la preuve n'est plus celui de l'archive publiée. "
        "`ansible-galaxy collection build` ne construit que ce répertoire : "
        "restreindre plus laisserait un module bouger sans invalider le tir, "
        "élargir rendrait la garde impossible à satisfaire."
    )
