"""Ce que le contrôle du journal des apparitions refuse, et ce qu'il publie.

Un contrôle qui ne refuse jamais est une décoration, et un contrôle qui refuse
tout est un contrôle qu'on désactive. Les deux bords sont donc mesurés ici.
"""

from __future__ import annotations

import dataclasses
from types import MappingProxyType

import introductions

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


def test_une_version_en_preparation_qui_contredit_les_fragments_est_refusee() -> None:
    """Et seulement quand un nom en dépend.

    Sans rien en attente, la valeur ne publie aucune date, et refuser
    obligerait à corriger le journal chaque fois qu'un fragment change de
    portée sans qu'aucun module soit concerné.
    """
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

    # Le contre-exemple : la même version fausse, mais plus rien qui en dépende.
    intacte = dataclasses.replace(journal, en_preparation="9.9.9")
    conforme, _ = introductions.controler(intacte)
    assert conforme
