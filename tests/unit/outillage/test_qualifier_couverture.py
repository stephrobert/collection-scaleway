"""Une porte qui tait ses trous est le vert sur zéro fichier examiné.

`mise run qualifier` annonce rejouer la CI, et il a annoncé « 12 étapes » quand
la CI en portait quatorze : le parcours d'accueil et la réaction sur événement,
ajoutés pendant le jalon, n'y étaient pas. Le correctif seul ne suffisait pas,
parce que le prochain job ajouté aurait recommencé.

La couverture se dérive donc du workflow. Un job qui n'est ni rejoué ni nommé
comme non rejouable fait rougir ici, au moment où quelqu'un l'ajoute.
"""

from __future__ import annotations

import re
from pathlib import Path

import qualifier

RACINE = Path(__file__).resolve().parents[3]
WORKFLOW = RACINE / ".github" / "workflows" / "ci.yml"


def _jobs_de_la_ci() -> set[str]:
    """Les jobs que `ci.yml` déclare, lus dans le fichier.

    Une liste écrite ici serait une seconde source du workflow, et elle aurait
    exactement le défaut que ce test existe pour attraper.

    Le suffixe d'une matrice est retiré : `collection (ansible-core ...)` est un
    job, décliné en quatre exécutions. La porte le rejoue une fois et le dit
    dans sa réserve, ce qui est un choix assumé et non un oubli.

    Les autres workflows (CodeQL, TruffleHog, Scorecard) ne sont pas lus ici :
    la porte les nomme comme non rejouables, et ils vivent chacun dans leur
    fichier.
    """
    texte = WORKFLOW.read_text(encoding="utf-8")
    # `name:` au premier niveau d'un job, c'est à dire indenté de quatre
    # espaces sous `jobs:`. Les `name:` d'étapes le sont davantage.
    return {
        nom.split(" (")[0] for nom in re.findall(r"^    name: (.+)$", texte, flags=re.MULTILINE)
    }


def test_le_workflow_declare_des_jobs() -> None:
    """Sans ça, tout ce fichier serait vert sur rien."""
    assert _jobs_de_la_ci(), "aucun job reconnu : le motif ne mesure plus le workflow"


def test_chaque_job_de_la_ci_est_rejoue_ou_nomme() -> None:
    """C'est la promesse de la porte, et elle était tenue à la main.

    Un job ajouté sans y penser laissait la porte annoncer un compte inférieur
    à ce que la CI fait, sans que rien ne le dise. Le compte rendu se lisait
    comme une couverture complète.
    """
    rejoues = {etape.job for etape in qualifier.ETAPES}
    nommes = {nom for nom, _ in qualifier.NON_REJOUES}

    oublies = sorted(_jobs_de_la_ci() - rejoues - nommes)
    assert oublies == [], (
        f"job(s) de CI que la porte ne rejoue pas et ne nomme pas : {oublies}. "
        "Soit une étape les rejoue, soit `NON_REJOUES` dit pourquoi c'est "
        "impossible : taire un job fait annoncer une couverture qu'on n'a pas"
    )


def test_aucune_etape_ne_designe_un_job_disparu() -> None:
    """Une étape orpheline rejoue quelque chose que la CI ne fait plus.

    Elle coûte du temps à chaque passage et donne confiance sur un job qui
    n'existe plus, ce qui est pire que de ne rien rejouer.
    """
    # Ce que la porte rejoue et qui ne vient pas de `ci.yml` : chaque nom est
    # un job d'un autre workflow, ou un groupe de commodité que le compte rendu
    # affiche tel quel. Les nommer ici fait de leur ajout une décision.
    ailleurs = {"Workflow security", "Plumber", "ClusterFuzzLite", "scan-pr / osv-scan"}
    orphelines = sorted({etape.job for etape in qualifier.ETAPES} - _jobs_de_la_ci() - ailleurs)
    assert orphelines == [], f"étape(s) désignant un job absent du workflow : {orphelines}"
