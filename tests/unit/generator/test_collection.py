"""La collection se découvre, et son identité doit être cohérente.

Ansible charge une collection par **son chemin** et la décrit par **son
manifeste**. On ne peut supprimer ni l'un ni l'autre : l'outil impose les deux.
Ce qui se peut, c'est exiger qu'ils concordent.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from generator.ansible.collection import CollectionError, find_collection, load_collection


def _ecrire(racine: Path, namespace: str, nom: str, declare: dict[str, object]) -> Path:
    chemin = racine / "ansible_collections" / namespace / nom
    chemin.mkdir(parents=True, exist_ok=True)
    (chemin / "galaxy.yml").write_text(yaml.safe_dump(declare), encoding="utf-8")
    return chemin


def test_la_collection_du_depot_se_decouvre() -> None:
    collection = load_collection()
    assert collection.fqcn == "stephrobert.scaleway"
    assert collection.path.name == collection.name
    assert collection.path.parent.name == collection.namespace


def test_le_chemin_dimport_du_runtime_suit_le_namespace() -> None:
    collection = load_collection()
    assert collection.module_utils_import.startswith("ansible_collections.stephrobert.scaleway.")
    assert collection.collections_root.name != "ansible_collections"


def test_un_chemin_qui_ment_sur_le_namespace_est_refuse(tmp_path: Path) -> None:
    """La collection se chargerait sous le nom du chemin, pas sous le sien."""
    chemin = _ecrire(
        tmp_path,
        "autre",
        "scaleway",
        {"namespace": "local", "name": "scaleway", "version": "1.0.0"},
    )

    with pytest.raises(CollectionError) as erreur:
        load_collection(chemin)
    assert "chemin" in str(erreur.value)


def test_un_manifeste_coherent_est_accepte(tmp_path: Path) -> None:
    """Sans cette moitié, le test précédent passerait sur un refus permanent."""
    chemin = _ecrire(
        tmp_path,
        "local",
        "scaleway",
        {"namespace": "local", "name": "scaleway", "version": "1.0.0"},
    )
    assert load_collection(chemin).version == "1.0.0"


def test_deux_collections_dans_un_depot_sont_refusees(tmp_path: Path) -> None:
    """Choisir implicitement serait choisir sans que personne le relise."""
    _ecrire(
        tmp_path,
        "local",
        "scaleway",
        {"namespace": "local", "name": "scaleway", "version": "1.0.0"},
    )
    _ecrire(tmp_path, "local", "autre", {"namespace": "local", "name": "autre", "version": "1.0.0"})

    with pytest.raises(CollectionError) as erreur:
        find_collection(tmp_path / "ansible_collections")
    assert "plusieurs" in str(erreur.value)


def test_une_collection_absente_est_dite_absente(tmp_path: Path) -> None:
    (tmp_path / "ansible_collections").mkdir()
    with pytest.raises(CollectionError):
        find_collection(tmp_path / "ansible_collections")
