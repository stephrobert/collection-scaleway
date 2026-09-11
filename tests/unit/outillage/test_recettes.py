"""Une recette sans playbook livré n'est pas une recette, c'est une intention.

Le chapitre de recettes vit dans le README des playbooks, et le site l'assemble
de là. C'est délibéré, et la raison est écrite dans `docsite.py` : « Écrire des
pages de tâches à la main à côté ferait une seconde source, que rien
n'exécuterait et qui pourrirait. »

Ces tests tiennent la bijection dans les deux sens. Un playbook livré sans
recette est un playbook que personne ne sait pourquoi lancer ; une recette sans
playbook est une promesse.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
PLAYBOOKS = RACINE / "ansible_collections" / "stephrobert" / "scaleway" / "playbooks"
LISEZ_MOI = PLAYBOOKS / "README.md"


def _recettes() -> str:
    """La section des recettes, et elle seule."""
    texte = LISEZ_MOI.read_text(encoding="utf-8")
    debut = texte.index("## Recipes")
    fin = texte.index("## Running them")
    return texte[debut:fin]


def _playbooks_cites(section: str) -> set[str]:
    return set(re.findall(r"stephrobert\.scaleway\.([a-z0-9_]+)", section))


def _playbooks_livres() -> set[str]:
    return {chemin.stem for chemin in PLAYBOOKS.glob("*.yml")}


def test_chaque_playbook_livre_a_sa_recette() -> None:
    """Un playbook que personne ne sait pourquoi lancer n'a pas d'usage."""
    livres = _playbooks_livres()
    assert livres, "le répertoire des playbooks ne se lit plus"

    sans_recette = sorted(livres - _playbooks_cites(_recettes()))
    assert sans_recette == [], (
        f"playbook(s) livré(s) sans recette : {sans_recette}. Une recette part "
        "d'un besoin et dit quelle commande y répond"
    )


def test_aucune_recette_ne_cite_un_playbook_absent() -> None:
    """Une recette sans playbook est une promesse, pas une documentation."""
    cites = _playbooks_cites(_recettes())
    assert cites, "la section des recettes ne cite plus aucun playbook"

    fantomes = sorted(cites - _playbooks_livres())
    assert fantomes == [], f"recette(s) citant un playbook absent : {fantomes}"


def test_chaque_recette_dit_ce_quelle_ne_fait_pas() -> None:
    """C'est la moitié qui manque partout ailleurs, et celle qui évite un piège.

    Ce que le lecteur doit savoir n'est pas seulement ce que la commande fait :
    c'est ce qu'elle refuse, parce que c'est là qu'un outil trompe.
    """
    section = _recettes()
    besoins = re.findall(r"^### (.+)$", section, flags=re.MULTILINE)
    assert besoins, "les recettes ne sont plus découpées par besoin"

    blocs = re.split(r"^### .+$", section, flags=re.MULTILINE)[1:]
    # Singulier ou pluriel : une recette qui couvre plusieurs playbooks dit « they ».
    refus = re.compile(r"\*\*What (?:it does|they do) not do\*\*")
    for besoin, bloc in zip(besoins, blocs, strict=True):
        assert refus.search(bloc), f"la recette « {besoin} » ne dit pas ce qu'elle refuse"


def test_chaque_recette_part_dun_besoin_et_pas_dun_module() -> None:
    """Un titre qui nomme un module range la documentation par l'outil.

    Le lecteur arrive avec un problème, pas avec un nom de playbook.
    """
    besoins = re.findall(r"^### (.+)$", _recettes(), flags=re.MULTILINE)

    for besoin in besoins:
        assert besoin.startswith('"'), (
            f"« {besoin} » ne part pas d'un besoin : une recette se titre par "
            "la phrase que quelqu'un se dit avant de chercher"
        )


def test_la_page_des_recettes_est_surveillee() -> None:
    """Elle est publiée : le site l'assemble sous « Task playbooks ».

    Elle a porté deux comptes que le temps avait démentis, celui des playbooks
    livrés et celui des modules que l'exemple appelle, parce qu'aucun contrôle
    ne la regardait.
    """
    import chiffres

    assert LISEZ_MOI in chiffres.SURVEILLES, (
        "la page qui porte les recettes doit être surveillée comme les autres pages publiées"
    )
