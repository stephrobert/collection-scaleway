"""Ce produit arrive-t-il derrière la collection officielle, ou en face ?"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import admission  # noqa: E402
import officielle  # noqa: E402


def test_un_produit_quils_provisionnent_est_nomme_avec_leurs_modules() -> None:
    """« Ils le créent, nous l'exploitons » se lit dans le rapport, pas de mémoire."""
    etape = admission.etape_complementarite("k8s")

    assert etape.tenue
    assert "scaleway_k8s_cluster" in etape.detail


def test_un_produit_quils_ne_provisionnent_pas_est_un_prix_pas_un_refus() -> None:
    """Refuser interdirait tout ce que leur collection ignore.

    C'est à dire le plus gros de leur propre dépôt, dont l'essentiel des modules
    n'est pas livré (ADR-022), et les deux produits déjà livrés ici tombent de
    ce côté.
    """
    etape = admission.etape_complementarite("instance")

    assert not etape.tenue
    assert not etape.bloquante
    assert "prix et non un refus" in etape.detail


def test_sans_mesure_letape_dit_quelle_na_rien_mesure() -> None:
    """Rien n'a été mesuré n'est pas rien n'a été trouvé."""
    ancienne = officielle.MESURE
    officielle.MESURE = ROOT / "specs" / "officielle" / "personne.json"
    try:
        etape = admission.etape_complementarite("k8s")
    finally:
        officielle.MESURE = ancienne

    assert not etape.tenue
    assert "sync:officielle" in etape.detail


def test_letape_ne_va_jamais_sur_le_reseau() -> None:
    """La mesure est versionnée, et c'est ce qui rend `admission` reproductible.

    Le contrôle porte sur ce qui est **importé**, pas sur le nom appelé. Une
    première version regardait les appels, et `/falsify` l'a dit : neutraliser
    la garde par `from officielle import mesurer as lire` laissait le nom
    d'appel intact et le test vert. Un contrôle qu'aucune mutation ne peut faire
    rougir est une affirmation que rien ne vérifie.
    """
    import ast

    source = ast.parse((ROOT / "scripts" / "admission.py").read_text(encoding="utf-8"))
    fonction = next(
        noeud
        for noeud in ast.walk(source)
        if isinstance(noeud, ast.FunctionDef) and noeud.name == "etape_complementarite"
    )
    importes = {
        alias.name
        for noeud in ast.walk(fonction)
        if isinstance(noeud, ast.ImportFrom) and noeud.module == "officielle"
        for alias in noeud.names
    }

    assert importes == {"MESURE", "lire"}
