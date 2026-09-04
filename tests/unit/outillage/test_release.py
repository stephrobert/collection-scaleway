"""Ce que la garde de publication refuse, et pourquoi chaque refus coûte un numéro.

Une version publiée sur Galaxy est **immuable** : republier la même rend
``conflict.collection_exists``. Il n'y a pas de correction, seulement une
version de plus. Chacun des refus ci-dessous coûterait donc un numéro à qui
publie, et il n'existait aucune garde avant que #67 le demande.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import release


@pytest.mark.parametrize(("tag", "attendu"), [("v0.1.0", "0.1.0"), ("0.1.0", "0.1.0")])
def test_les_deux_conventions_de_tag_designent_la_meme_version(tag: str, attendu: str) -> None:
    """Refuser `v0.1.0` ferait perdre une version à qui se trompe de forme."""
    assert release.normaliser(tag) == attendu


def _sans_bruit(monkeypatch: pytest.MonkeyPatch, collection: Any) -> None:
    """Neutralise git et le changelog : chaque test ne juge que son refus."""
    monkeypatch.setattr(release, "load_collection", lambda: collection)
    monkeypatch.setattr(release, "_git", lambda *_: "")
    monkeypatch.setattr(release, "fragments_en_attente", lambda _: [])


class _Collection:
    def __init__(self, version: str, chemin: Path) -> None:
        self.version = version
        self.path = chemin
        self.fqcn = "stephrobert.scaleway"


def test_un_tag_qui_ne_dit_pas_la_version_de_galaxy_est_refuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L'archive est nommée d'après `galaxy.yml`, pas d'après le tag.

    Les deux peuvent diverger sans que rien ne le dise, et on publie alors une
    version que l'historique ne porte pas.
    """
    _sans_bruit(monkeypatch, _Collection("0.1.0", tmp_path))
    refus = release.controler("0.2.0")
    assert len(refus) == 1
    assert "0.2.0" in refus[0] and "0.1.0" in refus[0]


def test_sans_tag_on_ne_publie_pas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Une version publiée doit être retrouvable dans l'historique."""
    _sans_bruit(monkeypatch, _Collection("0.1.0", tmp_path))
    refus = release.controler(None)
    assert len(refus) == 1
    assert "aucun tag" in refus[0]


def test_un_arbre_sale_est_refuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Une archive construite sur des modifications non versionnées ne se reproduit pas."""
    _sans_bruit(monkeypatch, _Collection("0.1.0", tmp_path))
    monkeypatch.setattr(release, "_git", lambda *_: " M generator/ansible/models.py")
    refus = release.controler("0.1.0")
    assert len(refus) == 1
    assert "non versionnée" in refus[0]


def test_des_fragments_en_attente_sont_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ils décrivent ce que la version apporte, et resteraient dehors.

    Mesuré sur ce dépôt : douze fragments accumulés sous une `0.1.0` composée
    quand la collection portait **un** module, dont le correctif de pagination
    qui rendait une première page en silence.
    """
    _sans_bruit(monkeypatch, _Collection("0.1.0", tmp_path))
    monkeypatch.setattr(release, "fragments_en_attente", lambda _: ["pagination.yml"])
    refus = release.controler("0.1.0")
    assert len(refus) == 1
    assert "pagination.yml" in refus[0]


def test_une_version_qui_nest_pas_semver_est_refusee(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ansible impose le versionnement sémantique aux collections."""
    _sans_bruit(monkeypatch, _Collection("0.1", tmp_path))
    refus = release.controler("0.1")
    assert any("sémantique" in raison for raison in refus)


def test_tout_en_ordre_ne_refuse_rien(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Le cas voisin, et il porte plus que les autres.

    Une garde qui refuse tout ferait passer les cinq tests précédents, et
    empêcherait toute publication sur un dépôt sain.
    """
    _sans_bruit(monkeypatch, _Collection("0.1.0", tmp_path))
    assert release.controler("0.1.0") == []


def test_les_fragments_se_lisent_sur_le_disque(tmp_path: Path) -> None:
    """La liste vient du répertoire, pas d'une déclaration à tenir à jour."""
    dossier = tmp_path / "changelogs" / "fragments"
    dossier.mkdir(parents=True)
    (dossier / "b.yml").write_text("", encoding="utf-8")
    (dossier / "a.yml").write_text("", encoding="utf-8")
    (dossier / ".gitkeep").write_text("", encoding="utf-8")
    assert release.fragments_en_attente(tmp_path) == ["a.yml", "b.yml"]
