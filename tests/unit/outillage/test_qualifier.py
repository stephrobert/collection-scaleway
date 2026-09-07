"""La porte de qualification doit lancer ce qu'elle annonce.

Elle nommait « site de documentation et playbooks cités » et lançait
`mise run docs:site docs:examples check:worktree`. Mise n'en lance qu'une ainsi :
il passe les suivantes en **arguments** à la première, qui les ignore. La sortie
le disait, si on la lisait :

    [docs:site] $ python scripts/docsite.py docs:examples check:worktree

L'étape rendait donc vert en ayant mesuré une part de ce qu'elle nommait, et le
défaut est resté invisible parce qu'un vert partiel ressemble trait pour trait à
un vert complet. C'est exactement ce que cette porte existe pour empêcher, dans
la porte elle-même.
"""

from __future__ import annotations

import qualifier


def test_aucune_commande_mise_ne_nomme_deux_taches() -> None:
    """`mise run a b` passe `b` en argument à `a`, il ne lance pas `b`.

    Une tâche du dépôt se reconnaît à son nom : ils portent des deux-points ou
    figurent parmi les tâches simples que la porte emploie. Un second nom après
    le premier est donc le défaut, pas une option.
    """
    fautives = []
    for etape in qualifier.ETAPES:
        commande = list(etape.commande)
        if commande[:2] != ["mise", "run"]:
            continue
        taches = [mot for mot in commande[2:] if not mot.startswith("-")]
        if len(taches) > 1:
            fautives.append(f"{etape.job} : {' '.join(commande)}")

    assert fautives == [], "\n".join(fautives)


def test_chaque_etape_nomme_le_job_quelle_rejoue() -> None:
    """Le compte rendu se lit comme une carte de la CI.

    Sans le nom du job, un lecteur ne peut pas voir ce qui n'y est pas, et
    c'est la moitié utile de cette porte.
    """
    assert all(etape.job for etape in qualifier.ETAPES)
    assert all(etape.nom for etape in qualifier.ETAPES)


def test_ce_qui_nest_pas_rejouable_est_nomme() -> None:
    """Une porte qui tairait ses trous serait le vert sur zéro fichier examiné.

    Chaque entrée porte sa raison : « non rejouable » sans raison se lit comme
    un oubli, et personne ne saurait s'il faut la combler.
    """
    assert qualifier.NON_REJOUES
    assert all(nom and raison for nom, raison in qualifier.NON_REJOUES)
