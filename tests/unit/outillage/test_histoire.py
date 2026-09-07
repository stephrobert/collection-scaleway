"""Un nombre qui compte des choses du dépôt n'a pas sa place dans une phrase.

Le README dérivait ses nombres, puis `docs/` s'est vu appliquer la même règle.
**Le code n'y était pas soumis**, et il portait les mêmes compteurs faux : des
docstrings annonçant un compte de tests que la mesure démentait, un compte de
modules inférieur à ce que la collection publie, et deux copies d'un même
tableau qui ne disaient déjà plus la même chose.

Ces tests portent sur la garde, pas sur le dépôt : ils prouvent qu'elle refuse
ce qu'elle doit refuser, et surtout qu'elle **laisse passer** ce qu'un contrôle
trop large refuserait. Une gêne se désactive, et ne mesure alors plus rien.
"""

from __future__ import annotations

from pathlib import Path

import histoire


def _module(dossier: Path, contenu: str) -> Path:
    chemin = dossier / "sujet.py"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_un_compteur_dans_une_docstring_est_refuse(tmp_path: Path) -> None:
    """Le défaut mesuré : un compte de tests figé au jour de la phrase.

    Le compteur fautif vit dans le sujet ci-dessous et non dans cette phrase,
    qui serait sinon le défaut qu'elle décrit.
    """
    chemin = _module(tmp_path, '"""Ce que mesurent les 575 tests du dépôt."""\n')

    ecarts = histoire.examiner(chemin)

    assert [ecart.texte for ecart in ecarts] == ["575 tests"]


def test_un_compteur_dans_un_commentaire_est_refuse(tmp_path: Path) -> None:
    """Un commentaire vieillit exactement comme une docstring."""
    chemin = _module(tmp_path, "# La collection publie cinquante modules.\nx = 1\n")

    assert [ecart.texte for ecart in histoire.examiner(chemin)] == ["cinquante modules"]


def test_le_nombre_est_trouve_meme_coupe_par_un_retour_a_la_ligne(tmp_path: Path) -> None:
    """Un commentaire se réécrit à la largeur de la colonne.

    Chercher sur la ligne seule laissait passer « 41\\n opérations », qui est
    exactement la forme qu'avait le passage mesuré dans `generator/plan.py`.
    """
    chemin = _module(tmp_path, '"""Sur Instance, 41\n    opérations sont classées."""\n')

    assert [ecart.texte for ecart in histoire.examiner(chemin)] == ["41 opérations"]


def test_un_article_nest_pas_un_compte(tmp_path: Path) -> None:
    """« un module », « une option », « deux contrats ».

    C'est la moitié du vocabulaire du dépôt, et une règle qui refuserait « un
    module porte une opération » serait une gêne qu'on désactiverait au lieu de
    la respecter.
    """
    chemin = _module(
        tmp_path,
        '"""Un module porte une opération, et deux contrats la déclarent."""\n',
    )

    assert histoire.examiner(chemin) == []


def test_un_nombre_dans_un_mot_compose_nest_pas_un_compte(tmp_path: Path) -> None:
    """Un composé à trait d'union ne porte pas le compte qu'on croit y lire.

    La première version de la classe de caractères lisait le second membre du
    composé et signalait deux passages parfaitement corrects. Un contrôle qui
    crie au loup est un contrôle qu'on éteint.
    """
    chemin = _module(tmp_path, "# L'exercice crée trente-sept ressources puis les détruit.\n")

    assert histoire.examiner(chemin) == []


def test_un_nombre_qui_ne_compte_rien_du_depot_passe(tmp_path: Path) -> None:
    """« Python 3.12 », « 60 s », « RFC 2606 »."""
    chemin = _module(
        tmp_path,
        '"""Python 3.12 est exigé, le délai est de 60 s, RFC 2606 réserve example.com."""\n',
    )

    assert histoire.examiner(chemin) == []


def test_une_chaine_de_donnees_nest_pas_une_phrase(tmp_path: Path) -> None:
    """Un compteur qu'un programme calcule ne vieillit pas tout seul.

    Sans cette distinction, le contrôle refuserait les messages que les
    programmes du dépôt composent avec leurs propres mesures, c'est-à-dire
    exactement ce qu'on veut encourager.
    """
    chemin = _module(tmp_path, 'message = f"{n} modules interrogés"\nautre = "50 pages"\n')

    assert histoire.examiner(chemin) == []


def test_un_fichier_illisible_ne_fait_pas_planter(tmp_path: Path) -> None:
    """Un contrôle qui plante sur un fichier en cours d'édition sera désactivé."""
    chemin = _module(tmp_path, "def casse(:\n")

    assert histoire.examiner(chemin) == []


def test_le_depot_ne_porte_aucun_nombre_historique() -> None:
    """Ce que le contrôle dit du dépôt aujourd'hui.

    Le seul test du fichier qui le regarde, et c'est voulu : les autres prouvent
    que la garde sait refuser et sait laisser passer, celui-ci dit où en est le
    dépôt.
    """
    ecarts = [str(ecart) for chemin in histoire.fichiers() for ecart in histoire.examiner(chemin)]

    assert ecarts == [], "\n".join(ecarts)


def test_le_controle_refuse_de_nexaminer_aucun_fichier(monkeypatch) -> None:
    """Zéro fichier examiné est un vert qui ne dit rien (ADR-004).

    C'est le défaut qui avait rendu un `ansible-test sanity` vert sur zéro
    fichier, et il ne coûte rien de le refuser ici aussi.
    """
    monkeypatch.setattr(histoire, "ARBRES", ())

    assert histoire.main() == 1
