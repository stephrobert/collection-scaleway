"""Ce que le verrou de plateforme refuse, et ce qu'il se contente de dire.

Un run réel a laissé des ressources facturées vivantes. Le `finally` avait été
atteint et avait lancé la destruction : c'est la destruction elle-même qui n'a
pas pu s'exécuter, parce que la branche git avait changé pendant que le
déploiement tournait et que `examples/stack/.terraform.lock.hcl` est versionné.
ADR-015 porte l'incident et son compte.

Ces tests fabriquent un verrou et ne touchent à aucun cloud : c'est ce que
l'issue demandait, et c'est ce qui les rend lançables à chaque commit.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import verrou_plateforme


@pytest.fixture
def verrou(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un verrou à nous, jamais celui du dépôt."""
    chemin = tmp_path / "plateforme.json"
    monkeypatch.setattr(verrou_plateforme, "VERROU", chemin)
    monkeypatch.setattr(verrou_plateforme, "ROOT", tmp_path)
    return chemin


def test_sans_plateforme_debout_le_verrou_se_pose(verrou: Path) -> None:
    pose = verrou_plateforme.poser("abc123", "reel")
    assert pose.run_id == "abc123"
    assert verrou.is_file()


def test_un_second_run_est_refuse(verrou: Path) -> None:
    """Deux exercices concurrents se détruiraient par leurs `finally` respectifs.

    Le premier détruirait ce que le second vient de créer, et le second ce que
    le premier tenait encore.
    """
    verrou_plateforme.poser("abc123", "reel")
    with pytest.raises(verrou_plateforme.VerrouError, match="déjà debout"):
        verrou_plateforme.poser("def456", "reel")


def test_le_refus_nomme_ce_qui_est_debout(verrou: Path) -> None:
    """Un refus qui ne dit pas quoi détruire oblige à chercher dans un journal."""
    verrou_plateforme.poser("abc123", "reel")
    with pytest.raises(verrou_plateforme.VerrouError) as erreur:
        verrou_plateforme.poser("def456", "emulateur")
    message = str(erreur.value)
    assert "abc123" in message
    assert "reel" in message


def test_un_arbre_inchange_ne_derive_pas(verrou: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(verrou_plateforme, "empreinte", lambda: "identique")
    verrou_plateforme.poser("abc123", "reel")
    assert verrou_plateforme.derive() == ""


def test_un_arbre_qui_a_change_est_annonce(verrou: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Le cas exact de l'incident : la définition a bougé sous le déploiement."""
    monkeypatch.setattr(verrou_plateforme, "empreinte", lambda: "avant")
    verrou_plateforme.poser("abc123", "reel")

    monkeypatch.setattr(verrou_plateforme, "empreinte", lambda: "après")
    message = verrou_plateforme.derive()
    assert "L'ARBRE A CHANGÉ" in message
    assert "git checkout" in message, "le message doit dire quoi retrouver"


def test_la_derive_ne_leve_jamais(verrou: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Découvrir la dérive ne doit pas empêcher la destruction.

    Lever ici laisserait des ressources facturées debout pour faire respecter
    une règle d'hygiène, ce qui est exactement le mauvais arbitrage.
    """
    monkeypatch.setattr(verrou_plateforme, "empreinte", lambda: "avant")
    verrou_plateforme.poser("abc123", "reel")
    monkeypatch.setattr(verrou_plateforme, "empreinte", lambda: "après")
    assert isinstance(verrou_plateforme.derive(), str)


def test_sans_verrou_il_ny_a_pas_de_derive(verrou: Path) -> None:
    """Le contre-exemple : rien debout, rien à annoncer."""
    assert verrou_plateforme.derive() == ""


def test_un_verrou_illisible_est_signale(verrou: Path) -> None:
    """Le supprimer en silence perdrait l'information qui reste.

    Un verrou illisible dit qu'une plateforme **peut** être debout, et c'est
    l'hypothèse prudente : le compte se vérifie avant de le retirer.
    """
    verrou.write_text("{ ceci n'est pas du JSON", encoding="utf-8")
    with pytest.raises(verrou_plateforme.VerrouError, match="illisible"):
        verrou_plateforme.lire()


def test_le_verrou_se_retire(verrou: Path) -> None:
    verrou_plateforme.poser("abc123", "reel")
    verrou_plateforme.retirer()
    assert verrou_plateforme.lire() is None
    assert not verrou.exists()


def test_lempreinte_couvre_ce_qui_nest_pas_commite() -> None:
    """Le commit seul ne dit rien d'un `git stash` ni d'un éditeur ouvert.

    C'est justement ce que l'incident a laissé derrière : le verrou Terraform
    modifié dans la copie de travail, pas dans un commit.
    """
    assert "examples/stack" in verrou_plateforme.SUIVIS
    assert "|" in verrou_plateforme.empreinte(), "l'empreinte joint l'enregistré et l'en-cours"


def test_le_verrou_se_retire_quand_la_destruction_a_reussi() -> None:
    """Même si le run a échoué : c'est la destruction qui décide, pas le run.

    Le cas mesuré : un playbook rouge sur une plateforme entièrement détruite
    laissait un verrou debout, et le run suivant était refusé au nom d'une
    plateforme qui n'existait plus.
    """
    assert verrou_plateforme.a_retirer(detruit=True, garder=False) is True


def test_le_verrou_reste_quand_la_destruction_a_echoue() -> None:
    """Le contre-exemple, et c'est lui la raison d'être du verrou.

    Le lever alors que la destruction a échoué dirait qu'il n'y a plus rien
    debout : c'est exactement le mensonge que l'incident a produit.
    """
    assert verrou_plateforme.a_retirer(detruit=False, garder=False) is False


def test_une_plateforme_gardee_garde_son_verrou() -> None:
    """`--garder` laisse la plateforme debout, donc le verrou doit le dire."""
    assert verrou_plateforme.a_retirer(detruit=True, garder=True) is False
