"""La référence groupée par produit, et les pages de tâches assemblées.

`antsibull` rend les modules à plat, par ordre alphabétique. C'est déjà pénible
à cinquante, et le nombre ne cesse pas de croître puisque personne ne suit
l'API à la main (#164).

Cette page ne remplace pas les pages générées, elle les ordonne. Elle est
**générée depuis le plan**, donc depuis la décision du générateur lui-même :
la ressource et la classe sont celles qui ont nommé le module.
"""

from __future__ import annotations

from pathlib import Path

import docsite
import pytest


@pytest.fixture
def site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un `build/site-src/` à nous, jamais celui du dépôt."""
    monkeypatch.setattr(docsite, "SITE_SRC", tmp_path)
    return tmp_path


def test_la_reference_groupe_par_produit_puis_par_ressource(site: Path) -> None:
    docsite.write_reference_page()
    texte = (site / "guides" / "module-reference.md").read_text(encoding="utf-8")

    assert "## Instance API" in texte
    assert "### security group" in texte
    assert texte.index("## Instance API") < texte.index("### security group")


def test_chaque_entree_renvoie_a_la_page_generee(site: Path) -> None:
    """La page ordonne, elle ne remplace pas : la référence reste celle
    d'antsibull, et un lien qui n'y mènerait pas ferait une seconde source."""
    docsite.write_reference_page()
    texte = (site / "guides" / "module-reference.md").read_text(encoding="utf-8")

    assert "{ansplugin}`instance_server <stephrobert.scaleway.instance_server#module>`" in texte


def test_les_trois_classes_sortent_dans_lordre_de_la_lecture(site: Path) -> None:
    """On cherche d'abord ce qu'on peut lire, puis changer, puis déclencher.

    L'ordre alphabétique mettait `instance_server_action` avant
    `instance_server_info`, ce qui n'est celui d'aucune question.
    """
    docsite.write_reference_page()
    texte = (site / "guides" / "module-reference.md").read_text(encoding="utf-8")
    bloc = texte.split("### server\n", 1)[1].split("###", 1)[0]

    assert bloc.index("instance_server_info") < bloc.index("instance_server ")
    assert bloc.index("instance_server ") < bloc.index("instance_server_action")


def test_tout_module_livre_figure_dans_la_reference(site: Path) -> None:
    """Une référence qui en oublierait un serait pire que l'ordre alphabétique.

    C'est aussi ce qui la fait rougir le jour où un module apparaît sans que le
    plan le nomme, ce qui serait un défaut du générateur, pas de cette page.
    """
    docsite.write_reference_page()
    texte = (site / "guides" / "module-reference.md").read_text(encoding="utf-8")

    manquants = [nom for nom in docsite.expected_modules() if f"`{nom} <" not in texte]

    assert docsite.expected_modules(), "aucun module livré : le test ne mesure plus rien"
    assert manquants == []


def test_les_playbooks_livres_ont_leur_page(site: Path) -> None:
    """Ce sont les pages de tâches du site, et elles tournent.

    `mise run integration` les joue à chaque exécution : écrire des pages de
    tâches à la main à côté ferait une seconde source, que rien n'exécuterait.
    """
    docsite.write_playbooks_page()
    texte = (site / "guides" / "shipped-playbooks.md").read_text(encoding="utf-8")

    assert texte.startswith("# Task playbooks")
    assert "arreter_un_serveur.yml" in texte


def test_un_readme_absent_est_une_erreur_pas_une_page_vide(site: Path) -> None:
    """Le site n'invente pas ce qu'il sert."""
    with pytest.raises(docsite.SiteError, match="n'invente pas"):
        docsite._page_depuis_readme(Path("nulle-part.md"), "x", "X", "y")
