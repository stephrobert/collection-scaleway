"""Un compteur de téléchargements n'est pas un compte d'utilisateurs.

C'est la seule mesure d'adoption qu'un projet Galaxy reçoit gratuitement, et
elle ne mesure pas ce qu'on croit : une CI qui réinstalle à chaque exécution y
pèse autant qu'une équipe qui s'en sert tous les jours. Piloter un jalon
là-dessus revient à optimiser un chiffre illisible (#185).

Ces tests tiennent ce qui remplace ce chiffre : une liste de ce que quelqu'un a
**dit**, chaque ligne avec sa provenance, et un bloc dérivé qui publie aussi ce
que le dépôt ne sait pas.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parents[3]
ADOPTANTS = RACINE / "ADOPTERS.md"
LISEZ_MOI = RACINE / "README.md"
CONTRIBUER = RACINE / "CONTRIBUTING.md"
CONFIG = RACINE / ".github" / "ISSUE_TEMPLATE" / "config.yml"

SHOW_AND_TELL = "discussions/categories/show-and-tell"


def _section(marqueur: str) -> list[str]:
    texte = ADOPTANTS.read_text(encoding="utf-8")
    debut = texte.index(f"<!-- {marqueur}:début -->")
    corps = texte[debut : texte.index(f"<!-- {marqueur}:fin -->")]
    return [ligne.strip() for ligne in corps.splitlines() if ligne.strip().startswith("- ")]


# --- ce qu'une ligne doit porter -----------------------------------------


def _fichier(entrees: str) -> str:
    return f"<!-- adoptants:début -->\n{entrees}\n<!-- adoptants:fin -->\n"


def test_une_ligne_dadoption_sans_source_est_refusee() -> None:
    """Un usage que personne ne peut pointer est une affirmation, pas une mesure.

    Le test porte sur du texte synthétique, pas sur le fichier du dépôt : la
    liste y est vide, et un contrôle qui parcourrait une liste vide serait vert
    par construction. Il laisserait passer la première ligne écrite, c'est à
    dire exactement le cas qu'il existe pour attraper.
    """
    import readme_counters

    with pytest.raises(readme_counters.CompteursError) as erreur:
        readme_counters._lignes_declarees(
            "adoptants", _fichier("- Une équipe qui s'en sert tous les jours")
        )

    assert "sans source" in str(erreur.value)
    assert "affirmation, pas" in str(erreur.value)


def test_une_ligne_sourcee_passe() -> None:
    """Une porte qui refuse tout ne mesure plus rien : elle mesure sa panne."""
    import readme_counters

    entree = "- A team, said in https://github.com/stephrobert/collection-scaleway/discussions/1"
    assert readme_counters._lignes_declarees("adoptants", _fichier(entree)) == [entree]


def test_le_fichier_du_depot_passe_la_garde() -> None:
    """Et ce que le dépôt porte aujourd'hui est accepté, sinon rien ne publie."""
    assert _section("adoptants") == [] or all(
        re.search(r"https?://\S+", entree) for entree in _section("adoptants")
    )


def test_le_fichier_dit_ce_quil_ne_sait_pas() -> None:
    """La moitié qui manque à tous les compteurs d'adoption.

    Publier ce qu'on sait sans publier ce qu'on ignore laisse croire que la
    liste est le parc. Elle est ce que des gens ont bien voulu dire.
    """
    texte = ADOPTANTS.read_text(encoding="utf-8")

    assert "What this file does not know" in texte, (
        "le fichier ne dit plus ses limites : une liste d'usages sans ses "
        "limites se lit comme un inventaire"
    )
    assert "Downloads are not users" in texte, (
        "la confusion que ce fichier existe pour éviter n'y est plus nommée"
    )


# --- ce que le bloc publié doit dire --------------------------------------


def test_le_bloc_publie_ne_compte_pas_les_telechargements() -> None:
    """Le publier à côté d'un compte de personnes ferait passer l'un pour l'autre."""
    import readme_counters

    bloc = readme_counters.bloc_adoption()

    assert "download counter" in bloc, (
        "le bloc ne dit plus pourquoi le compteur de Galaxy n'y est pas, et "
        "quelqu'un finira par l'ajouter"
    )
    assert not re.search(r"\b\d+\s+downloads?\b", bloc), "un compte de téléchargements est publié"


def test_zero_entree_ne_secrit_pas_zero_utilisateur() -> None:
    """« Personne ne l'a dit » n'est pas « personne ne s'en sert ».

    C'est la distinction que `coverage:example` fait déjà entre « aucun run
    enregistré » et « 0 % ». Un `0 users` publié serait faux, et il serait cité.
    """
    import readme_counters

    if _section("adoptants"):
        return  # la liste n'est plus vide : ce test ne mesure plus rien ici

    bloc = readme_counters.bloc_adoption()
    assert "none yet, which is not the same as none existing" in bloc, (
        "une liste vide se publie comme une absence de mesure, jamais comme un zéro"
    )


def test_le_bloc_est_derive_dans_le_readme() -> None:
    """Écrit à la main, il vieillirait comme les autres comptes déjà démentis."""
    texte = LISEZ_MOI.read_text(encoding="utf-8")

    assert "<!-- compteurs:adoption:début" in texte, (
        "la section d'adoption du README ne dérive plus de `ADOPTERS.md`"
    )


# --- le chemin pour se manifester, et celui pour contribuer ---------------


def test_dire_quon_sen_sert_nexige_pas_douvrir_un_defaut() -> None:
    """Le tracker d'issues n'est pas l'endroit où dire qu'on se sert d'un outil.

    Sans cette entrée, la seule façon de se manifester était d'ouvrir une issue
    de défaut, et personne n'ouvre un défaut pour dire que ça marche.
    """
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    liens = [entree["url"] for entree in config["contact_links"]]

    assert any(SHOW_AND_TELL in lien for lien in liens), (
        "aucun lien ne mène à l'endroit où dire « je m'en sers »"
    )


def test_un_enchainement_remonte_a_un_chemin_vers_les_recettes() -> None:
    """Une chaîne qui ne vit que dans une discussion aide une personne.

    Le chapitre de recettes est ce qui la rend utile aux autres, et rejouée est
    ce qui la garde juste. Le chemin est écrit, avec ses étapes, ou il n'existe
    pas.
    """
    contribuer = CONTRIBUER.read_text(encoding="utf-8")

    assert "## From your chain to the recipe chapter" in contribuer, (
        "le chemin d'un enchaînement vers les recettes n'est plus documenté"
    )
    for exigence in ("mise run integration", "what it does not do", "scripts/example.py"):
        assert exigence in contribuer.split("## From your chain")[1].split("\n## ")[0], (
            f"le chemin ne mentionne plus « {exigence} », qui est ce qui "
            "distingue un playbook livré d'un extrait collé"
        )


def test_le_fichier_renvoie_au_chemin_quil_annonce() -> None:
    """Deux documents qui divergent valent moins qu'un seul."""
    assert "CONTRIBUTING.md#from-your-chain-to-the-recipe-chapter" in ADOPTANTS.read_text(
        encoding="utf-8"
    ), "le lien vers le chemin de contribution a disparu du fichier qui l'annonce"
