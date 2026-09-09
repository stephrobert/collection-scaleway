"""Une tâche qui lit les modules générés attend que la génération finisse.

`mise` lance les tâches d'une porte en parallèle. `admission` appelait
`docs_quality.mesurer()`, qui lit `plugins/modules/*.py`, sans déclarer
`generate` : `main` est sorti rouge sur deux défauts documentaires que le dépôt
ne porte pas, après une pull request verte.

C'était déjà l'omission de #138, où `readme` n'avait pas la dépendance que
`readme:check` avait. Ces tests portent sur le cas exact, tel qu'il était.
"""

from __future__ import annotations

import dependances_taches
import pytest

#: `mise.toml` réduit à ce qui compte, dans l'état qui a cassé `main`.
AVANT = """\
[tasks.generate]
run = "python -m generator generate"

[tasks."docs:quality"]
depends = ["generate"]
run = "python scripts/docs_quality.py --check"

[tasks.admission]
run = "python scripts/admission.py --tous"

[tasks.check]
depends = [
  "docs:quality",
  "admission",
]
"""

APRES = AVANT.replace(
    "[tasks.admission]\nrun =",
    '[tasks.admission]\ndepends = ["generate"]\nrun =',
)


def test_la_tache_qui_lisait_sans_attendre_est_refusee() -> None:
    """Le cas exact, rejoué sur l'état d'avant le correctif."""
    manques = dependances_taches.refus(AVANT)

    assert len(manques) == 1
    assert "admission" in manques[0]
    assert "generate" in manques[0]


def test_la_meme_tache_avec_sa_dependance_passe() -> None:
    """Le contre-exemple, sans lequel le contrôle refuserait toute tâche."""
    assert dependances_taches.refus(APRES) == []


def test_une_dependance_indirecte_suffit() -> None:
    """`check:generated` dépend de `generate` par `generate` lui-même ou par une
    autre tâche : exiger la dépendance directe ferait refuser des tâches déjà
    correctes, et le contrôle serait désactivé."""
    indirect = AVANT.replace(
        "[tasks.admission]\nrun =",
        '[tasks.admission]\ndepends = ["docs:quality"]\nrun =',
    )

    assert dependances_taches.refus(indirect) == []


def test_une_tache_qui_ne_lit_pas_les_modules_nest_pas_concernee() -> None:
    """Le second contre-exemple : la plupart des tâches ne lisent rien de généré."""
    texte = AVANT.replace(
        'run = "python scripts/admission.py --tous"',
        'run = "python scripts/histoire.py"',
    )

    manques = dependances_taches.refus(texte)

    assert all("admission" not in ligne for ligne in manques)


def test_un_check_sans_dependances_est_une_erreur_pas_un_succes() -> None:
    """Un contrôle qui ne lit rien rend vert sur n'importe quoi."""
    with pytest.raises(dependances_taches.DependancesError, match="aucune dépendance"):
        dependances_taches.refus('[tasks.generate]\nrun = "x"\n\n[tasks.check]\nrun = "y"\n')


def test_un_producteur_absent_est_une_erreur() -> None:
    """Le contrôle doit savoir ce qu'il surveille."""
    with pytest.raises(dependances_taches.DependancesError, match="n'est pas une tâche"):
        dependances_taches.refus('[tasks.check]\ndepends = ["autre"]\nrun = "y"\n')


def test_un_script_qui_lit_par_import_est_vu() -> None:
    """`admission` ne construit pas le chemin : il importe `docs_quality`.

    Ne regarder que le script lancé aurait laissé passer le défaut d'origine.
    """
    assert dependances_taches.lit_les_modules(dependances_taches.SCRIPTS / "admission.py"), (
        "admission lit les modules par `docs_quality`"
    )


def test_le_depot_est_conforme() -> None:
    """Ce que le contrôle dit du dépôt aujourd'hui."""
    assert dependances_taches.refus(dependances_taches.MISE.read_text(encoding="utf-8")) == []
