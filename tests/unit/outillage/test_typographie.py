"""Le tiret cadratin est refusé, et la règle est enfin mesurée.

Elle était écrite dans les instructions du dépôt, dans les deux langues, et rien
ne la vérifiait. Le dépôt en portait cent quatre-vingt-quatorze, presque tous
écrits en une semaine : un cadratin ne casse rien, ne rougit nulle part, et se
relit comme de la prose ordinaire.

Ces tests portent sur la garde. Le seul qui regarde le dépôt est nommé pour ça.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import typographie


def _fichier(dossier: Path, contenu: str, nom: str = "page.md") -> Path:
    chemin = dossier / nom
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_un_cadratin_est_signale_avec_sa_ligne(tmp_path: Path, monkeypatch) -> None:
    """Le message doit dire **où**, la correction dépendant de chaque incise."""
    contenu = (
        "Une phrase ordinaire.\nUne autre, avec une incise " + typographie.CADRATIN + " ici.\n"
    )
    _fichier(tmp_path, contenu)
    monkeypatch.setattr(typographie, "ROOT", tmp_path)

    ecarts = typographie.examiner("page.md")

    assert len(ecarts) == 1
    assert ecarts[0].ligne == 2


def test_une_prose_sans_cadratin_passe(tmp_path: Path, monkeypatch) -> None:
    """Le trait d'union, le tiret demi-cadratin et le point médian restent.

    Une règle qui refuserait tous les tirets serait une gêne : le dépôt écrit
    `dix-sept`, `2026-09-07` et sépare ses champs par un point médian.
    """
    _fichier(tmp_path, "dix-sept modules, 2026-09-07, a · b · c, et un tiret - simple.\n")
    monkeypatch.setattr(typographie, "ROOT", tmp_path)

    assert typographie.examiner("page.md") == []


def test_un_fichier_binaire_ne_fait_pas_planter(tmp_path: Path, monkeypatch) -> None:
    """Un contrôle qui plante sur un fichier inattendu finit désactivé."""
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")
    monkeypatch.setattr(typographie, "ROOT", tmp_path)

    assert typographie.examiner("image.png") == []


def test_un_fichier_absent_ne_fait_pas_planter(tmp_path: Path, monkeypatch) -> None:
    """`git ls-files` liste ce que l'index porte, pas ce que le disque porte."""
    monkeypatch.setattr(typographie, "ROOT", tmp_path)

    assert typographie.examiner("supprime-mais-encore-indexe.md") == []


def test_le_controle_refuse_de_nexaminer_aucun_fichier(monkeypatch) -> None:
    """Zéro fichier examiné est un vert qui ne dit rien (ADR-004)."""
    monkeypatch.setattr(typographie, "fichiers", list)

    assert typographie.main() == 1


def _faux_git(monkeypatch, sortie: str, code: int = 0) -> None:
    """Remplace l'appel à git par un `CompletedProcess` réel.

    Un double qui ne porte que les attributs lus le jour où on l'écrit casse au
    premier changement de la fonction qu'il imite. Celui-ci en portait un seul,
    et le repli hors dépôt lit `returncode` avant `stdout`.
    """
    monkeypatch.setattr(
        typographie.subprocess,
        "run",
        lambda commande, **_: subprocess.CompletedProcess(commande, code, sortie, ""),
    )


def test_les_artefacts_dun_outil_ne_sont_pas_de_la_prose(monkeypatch) -> None:
    """Le verrou, les contrats et les golden viennent d'ailleurs.

    Un cadratin dans une description venue du portail Scaleway n'est pas une
    phrase de ce dépôt, et le refuser demanderait de corriger l'amont.
    """
    _faux_git(monkeypatch, "README.md\nspecs/scaleway/instance.v1.yml\n")

    assert typographie.fichiers() == ["README.md"]


def test_hors_depot_le_controle_lit_le_disque(tmp_path: Path, monkeypatch) -> None:
    """Le harnais de falsification travaille dans une copie sans `.git`.

    Un contrôle qui y plante ne peut pas être prouvé, et il n'aurait alors que
    l'apparence d'une garde. Une archive téléchargée pose le même problème.
    """
    _fichier(tmp_path, "Une page ordinaire.\n", nom="lisible.md")
    monkeypatch.setattr(typographie, "ROOT", tmp_path)
    _faux_git(monkeypatch, "", code=128)

    assert typographie.fichiers() == ["lisible.md"]


def test_le_repli_saute_ce_que_git_aurait_saute(tmp_path: Path, monkeypatch) -> None:
    """Sinon il lirait `build/`, `.venv/` et les artefacts.

    Ce qui n'est pas versionné n'est pas publié, et n'a pas à passer une porte
    de rédaction : le repli doit refuser le même périmètre que git, pas un
    périmètre plus large parce qu'il est plus simple à écrire.
    """
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "rapport.md").write_text("produit", encoding="utf-8")
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "amont.yml").write_text("venu d'ailleurs", encoding="utf-8")
    _fichier(tmp_path, "Une page ordinaire.\n", nom="lisible.md")
    monkeypatch.setattr(typographie, "ROOT", tmp_path)
    _faux_git(monkeypatch, "", code=128)

    assert typographie.fichiers() == ["lisible.md"]


def test_le_depot_ne_porte_aucun_cadratin() -> None:
    """Ce que le contrôle dit du dépôt aujourd'hui."""
    ecarts = [
        str(ecart) for chemin in typographie.fichiers() for ecart in typographie.examiner(chemin)
    ]

    assert ecarts == [], "\n".join(ecarts)


@pytest.mark.parametrize(
    ("document", "terme"),
    [("CLAUDE.md", "cadratin"), ("CONTRIBUTING.md", "em dash")],
)
def test_la_regle_reste_ecrite_la_ou_on_la_lit(document: str, terme: str) -> None:
    """Une garde sans sa raison écrite se lit comme une lubie.

    Le terme diffère avec la langue du document, et c'est la frontière du dépôt :
    `CONTRIBUTING.md` est publié donc anglais, `CLAUDE.md` ne l'est pas donc
    français. Ce dernier n'est pas versionné : son absence de ce clone ne fait
    pas échouer le test, mais s'il est là il doit porter la règle.
    """
    chemin = typographie.ROOT / document
    if not chemin.is_file():
        pytest.skip(f"{document} absent de ce clone")

    assert terme in chemin.read_text(encoding="utf-8").lower()
