"""Un lien publié à côté d'une version doit mener à cette version.

Sur Galaxy, la page de `stephrobert.scaleway` annonce sa version et propose un
lien « Documentation ». Celui-ci menait à `tree/main/docs` : le lecteur d'une
version publiée il y a six mois atterrissait sur les fichiers d'aujourd'hui, et
rien sur la page ne le lui disait.

Le tag existe forcément quand quelqu'un lit cette page : `release.py` refuse de
publier quand le tag et `galaxy.yml` divergent, et refuse un tag hors de `main`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import readme_counters

REPO = Path(__file__).resolve().parents[3]
PUBLIES = (
    REPO / "README.md",
    REPO / "ansible_collections" / "stephrobert" / "scaleway" / "README.md",
    REPO / "ansible_collections" / "stephrobert" / "scaleway" / "galaxy.yml",
)


def test_aucun_lien_de_ce_depot_ne_pointe_sur_une_branche() -> None:
    """`main` bouge, une version publiée non : les deux ne peuvent pas coïncider."""
    version = readme_counters.load_collection().version
    fautifs = []
    for fichier in PUBLIES:
        for lien in readme_counters.LIEN_DU_DEPOT.finditer(fichier.read_text(encoding="utf-8")):
            if lien.group(2) != version:
                fautifs.append(f"{fichier.name} : {lien.group(0)}")
    assert fautifs == [], f"liens non versionnés : {fautifs}"


def test_un_lien_du_depot_prend_la_version_publiee() -> None:
    """La substitution elle-même, isolée des fichiers qu'elle a déjà réécrits.

    Le test précédent lit l'état du dépôt : il resterait vert si la fonction
    cessait de versionner, puisque les fichiers portent déjà la bonne valeur.
    Il faut donc exercer la fonction pour que la garde morde.
    """
    reecrit = readme_counters._versionner_les_liens(
        "https://github.com/stephrobert/collection-scaleway/tree/main/docs\n", "9.9.9"
    )
    assert "/tree/9.9.9/docs" in reecrit


def test_un_lien_vers_un_autre_projet_nest_pas_reecrit() -> None:
    """Le README cite la checklist d'`ansible-inclusion`, dont `main` est la bonne référence.

    Une substitution qui prendrait toutes les URL GitHub ferait pointer ce lien
    sur un tag de **ce** dépôt, dans un dépôt qui ne le porte pas.
    """
    texte = (
        "voir https://github.com/ansible-collections/ansible-inclusion/blob/main/x.md\n"
        "et https://github.com/stephrobert/collection-scaleway/blob/main/docs/y.md\n"
    )
    reecrit = readme_counters._versionner_les_liens(texte, "9.9.9")
    assert "ansible-inclusion/blob/main/" in reecrit
    assert "collection-scaleway/blob/9.9.9/" in reecrit


def test_le_bloc_derive_publie_la_qualite_documentaire(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Un chiffre qui ne sort nulle part est un chiffre que personne ne surveille.

    Les 15 options sans description et les 18 exemples en `<zone>` étaient
    invisibles depuis le README, qui comptait pourtant les modules, les tests et
    les mutations.

    Les comptes rendus sont fabriqués : ils vivent dans `build/`, que la copie
    hors dépôt de `/falsify` n'emporte pas. Un test qui échouerait faute
    d'artefact ressemblerait à une garde prouvée sans rien prouver.
    """
    monkeypatch.setattr(readme_counters, "RAPPORTS", tmp_path)
    (tmp_path / "instance.v1.json").write_text(
        json.dumps(
            {
                "totals": {
                    "operations": 74,
                    "day2_candidates": 42,
                    "by_kind": dict.fromkeys(
                        ("info", "action", "manage", "workflow", "lifecycle", "ignore", "unknown"),
                        0,
                    ),
                    "by_mode": {"auto": 40, "manual": 1, "override": 1},
                },
                "day2_automation_coverage": 0.976,
            }
        ),
        encoding="utf-8",
    )
    for produit, ecrits in (("instance", 29), ("lb", 21)):
        (tmp_path / f"{produit}.v1.generation.md").write_text(
            f"# Génération\n\nModules écrits : **{ecrits}**, écartés : **1**\n",
            encoding="utf-8",
        )

    bloc = readme_counters.bloc()
    assert "published pages" in bloc
    assert "options and" in bloc
    assert "examples copyable as is" in bloc
    assert re.search(r"\d+/\d+ returned keys list their fields", bloc)
