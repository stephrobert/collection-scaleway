"""Aucun compteur vivant dans un document écrit à la main.

Le README dérivait ses nombres et la CI refusait un README périmé. **La règle ne
valait que pour lui.** Un audit de la 0.3.0 a trouvé plusieurs compteurs faux
dans `docs/`, chacun figé au jour où sa phrase a été écrite. ADR-007 les relève
avec leurs nombres et leur date, qui est ce qui les rend lisibles.

Le projet dit « ne pas mentir, mesurer ». Une règle qui ne vaut que pour un
fichier ne vaut pas.
"""

from __future__ import annotations

from pathlib import Path

import chiffres


def _document(dossier: Path, contenu: str) -> Path:
    chemin = dossier / "page.md"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_un_compteur_hors_bloc_est_refuse(tmp_path: Path) -> None:
    """C'est le défaut mesuré : une phrase qui commence par « Measured on »."""
    chemin = _document(
        tmp_path,
        "# Page\n\nMeasured on Instance v1: **41 Day-2 candidates, 40 AUTO**.\n",
    )
    ecarts = chiffres.examiner(chemin)
    trouves = {ecart.texte for ecart in ecarts}
    assert "41 Day-2" in trouves
    assert "40 AUTO" in trouves


def test_le_meme_compteur_dans_un_bloc_derive_passe(tmp_path: Path) -> None:
    """Le contrôle ne juge pas le nombre : il juge d'où il vient.

    Recalculer chaque chiffre pour l'auditer ferait un second calcul à tenir à
    jour, donc une seconde source qui divergerait de la première.
    """
    chemin = _document(
        tmp_path,
        "# Page\n\n"
        "<!-- compteurs:classification:début, produits par scripts/readme_counters.py -->\n"
        "Measured on Instance v1: **41 Day-2 candidates, 40 AUTO**.\n"
        "<!-- compteurs:classification:fin -->\n",
    )
    assert chiffres.examiner(chemin) == []


def test_un_nom_de_bloc_a_tiret_est_reconnu(tmp_path: Path) -> None:
    """`runtime-etat` et `ecart-cibles` en portent un.

    La première version de la classe de caractères n'acceptait que `[a-z]` :
    les blocs existaient, le contrôle les signalait quand même, et un lecteur
    aurait cherché un défaut là où il n'y en avait pas.
    """
    chemin = _document(
        tmp_path,
        "<!-- compteurs:runtime-etat:début, produits par scripts/readme_counters.py -->\n"
        "State: measured by 49 unit tests.\n"
        "<!-- compteurs:runtime-etat:fin -->\n",
    )
    assert chiffres.examiner(chemin) == []


def test_un_nombre_qui_nest_pas_une_mesure_passe(tmp_path: Path) -> None:
    """« Python 3.12 », « RFC 2606 », un nombre qui ne mesure rien.

    Un contrôle qui refuserait tout chiffre serait une gêne, pas une garde :
    on le désactiverait, et il ne mesurerait plus rien.
    """
    chemin = _document(
        tmp_path,
        "# Page\n\nPython 3.12 is required. RFC 2606 reserves `example.com`.\n"
        "The three rules below decide everything, and 42 is not a measurement.\n",
    )
    assert chiffres.examiner(chemin) == []


def test_seuls_les_adr_echappent_au_suivi() -> None:
    """Un ADR porte l'histoire avec sa date : y dériver un bloc la réécrirait.

    L'exemption est nommée, et elle est étroite. Élargie à `docs/`, elle
    sortirait de la mesure les pages où un compteur périmé se lit exactement
    comme une mesure, ce que ce contrôle existe pour empêcher.
    """
    suivis = {chemin.relative_to(chiffres.ROOT).as_posix() for chemin in chiffres.SURVEILLES}

    assert "docs/scorecard.md" in suivis, "une page publiée doit rester suivie"
    assert not any(nom.startswith("docs/adr/") for nom in suivis), sorted(suivis)


def test_le_depot_ne_publie_aucun_compteur_hors_bloc() -> None:
    """Ce que le contrôle mesure aujourd'hui sur les fichiers publiés.

    Le seul test du fichier qui regarde le dépôt, et c'est voulu : les autres
    prouvent que la garde sait refuser, celui-ci dit où en est le dépôt.
    """
    ecarts = [
        f"{ecart.fichier.name}:{ecart.ligne} « {ecart.texte} »"
        for chemin in chiffres.SURVEILLES
        for ecart in chiffres.examiner(chemin)
    ]
    assert ecarts == [], "\n".join(ecarts)
