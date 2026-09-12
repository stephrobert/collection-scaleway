"""Ce que le contrôle du journal des apparitions refuse, et ce qu'il publie.

Un contrôle qui ne refuse jamais est une décoration, et un contrôle qui refuse
tout est un contrôle qu'on désactive. Les deux bords sont donc mesurés ici.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from types import MappingProxyType

import introductions
import pytest
import version as version_module

from generator.ansible.collection import load_collection
from generator.ansible.introductions import load_introductions


def test_le_journal_du_depot_passe_son_propre_controle() -> None:
    """Le seul test du fichier qui dit où en est le dépôt, et c'est voulu."""
    conforme, lignes = introductions.controler(load_introductions())
    assert conforme, "\n".join(lignes)


def test_une_version_en_preparation_deja_publiee_est_refusee() -> None:
    """Une release partie sans que le journal soit figé.

    Le prochain figeage écrirait alors une seconde fois la même date, ce que le
    chargeur refuse : mieux vaut le dire au moment où c'est réparable.
    """
    journal = dataclasses.replace(load_introductions(), en_preparation=load_collection().version)
    conforme, lignes = introductions.controler(journal)
    assert not conforme
    assert any("n'est pas postérieure" in ligne for ligne in lignes)


def test_un_module_non_encore_date_est_publie_sans_etre_refuse() -> None:
    """Ajouter un produit ne doit pas rougir entre son écriture et sa release.

    C'est l'état normal d'un ajout, pas un défaut : le contrôle le nomme, et
    laisse passer.
    """
    journal = load_introductions()
    ampute = dataclasses.replace(
        journal,
        modules=MappingProxyType(
            {nom: version for nom, version in journal.modules.items() if nom != "lb_ip_info"}
        ),
    )
    conforme, lignes = introductions.controler(ampute)
    assert conforme
    assert any("module lb_ip_info" in ligne for ligne in lignes)


def test_une_version_en_preparation_qui_contredit_les_fragments_est_refusee(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Et seulement quand un nom en dépend.

    Sans rien en attente, la valeur ne publie aucune date, et refuser
    obligerait à corriger le journal chaque fois qu'un fragment change de
    portée sans qu'aucun module soit concerné.

    **Ce que les fragments impliquent est posé, pas lu dans le dépôt.** La
    composition d'une release les efface : ce test ne passait donc qu'entre
    deux versions, et rougissait le jour de la publication, qui est le pire
    jour possible pour un test qui ne mesure plus ce qu'il croit. C'est la
    troisième fois dans ce fichier qu'un cas dépendait d'un état transitoire.
    """
    monkeypatch.setattr(
        introductions,
        "implique",
        lambda _chemin, _version: ("0.9.9", "les fragments impliquent une version mineure"),
    )
    journal = load_introductions()
    ampute = dataclasses.replace(
        journal,
        en_preparation="9.9.9",
        modules=MappingProxyType(
            {nom: version for nom, version in journal.modules.items() if nom != "lb_ip_info"}
        ),
    )
    conforme, lignes = introductions.controler(ampute)
    assert not conforme
    assert any("contredit ce que les fragments impliquent" in ligne for ligne in lignes)

    # **Le contre-exemple : la même version fausse, mais plus rien qui en
    # dépende.** Il se construit, il ne se suppose pas. Le test passait
    # autrefois parce que le journal réel n'avait aucun nom en attente ce
    # jour-là ; il en a dès qu'un module gagne une option ou un retour, et le
    # contre-exemple mesurait alors la même chose que le cas nominal.
    modules, membres = introductions.noms_produits(journal)
    sans_attente = dataclasses.replace(
        journal,
        en_preparation="9.9.9",
        options=MappingProxyType(
            {
                **journal.options,
                **{(m, n): "0.1.0" for genre, m, n in membres if genre == "option"},
            }
        ),
        retours=MappingProxyType(
            {
                **journal.retours,
                **{(m, n): "0.1.0" for genre, m, n in membres if genre == "retour"},
            }
        ),
    )
    assert introductions.non_dates(sans_attente, modules, membres) == []
    conforme, _ = introductions.controler(sans_attente)
    assert conforme


def test_un_cycle_sans_rien_a_dater_avance_quand_meme_la_preparation(tmp_path: Path) -> None:
    """Un cycle peut ne rien ajouter que le journal date, et être une release.

    Mesuré en coupant la 0.6.0 : elle apportait des playbooks, un plugin de
    lookup et de la documentation, et pas un module, pas une option, pas une
    valeur de retour. Le figeage sortait par un raccourci avant d'avancer
    `en_preparation`, et le contrôle suivant refusait la release qui venait de
    se faire, en accusant un figeage qui avait pourtant eu lieu.

    Ce qui se saute quand il n'y a rien à dater, c'est le **bloc** : un bloc
    vide publierait un badge de version sur rien.
    """
    # Le journal du dépôt, copié : il date déjà tout ce qui est écrit, donc
    # figer une version de plus n'a rien à y inscrire. C'est exactement la
    # situation de la 0.6.0, reproduite plutôt que simulée.
    fichier = tmp_path / "introductions.yml"
    fichier.write_text(introductions.DEFAULT_JOURNAL.read_text(encoding="utf-8"), encoding="utf-8")
    journal = load_introductions(fichier)
    cible = journal.en_preparation

    lignes = introductions.enregistrer(journal, cible, fichier)

    assert any("rien à figer" in ligne for ligne in lignes), lignes
    attendue = version_module.suivante(cible, "correctif")
    assert load_introductions(fichier).en_preparation == attendue, (
        "la version en préparation n'a pas avancé : le contrôle refusera la "
        "release qui vient de se faire"
    )
    assert f'"{cible}":' not in fichier.read_text(encoding="utf-8"), (
        "un bloc vide a été écrit : il publierait un badge de version sur rien"
    )
