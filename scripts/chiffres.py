"""Aucun compteur vivant dans un document écrit à la main.

Le README dérive ses nombres et la CI refuse un README périmé. **Cette règle ne
valait que pour lui**, et un audit de la 0.3.0 a trouvé quatre documents qui
publiaient des chiffres faux :

Le relevé de ces écarts, avec ses nombres et sa date, vit dans ADR-007 : ici
il vieillirait, et deux docstrings en portaient déjà deux versions différentes.

Le projet dit « ne pas mentir, mesurer ». Une règle qui ne vaut que pour un
fichier ne vaut pas.

**Ce que ce contrôle cherche, et ce qu'il ne cherche pas.** Il ne juge pas si un
nombre est juste : il ne le saurait pas sans le recalculer, et ce serait alors
un second calcul à maintenir. Il cherche les **tournures** par lesquelles ce
dépôt publie une mesure : « N tests unitaires », « N modules », « N opérations
Day-2 », « couverture N % ». Toute occurrence hors d'un bloc dérivé est refusée,
avec le nom du bloc où la mettre.

Un nombre qui n'est pas une mesure passe donc sans encombre : « Python 3.12 »,
« RFC 2606 ». C'est voulu, et c'est la différence entre un contrôle et une
gêne.

## Ce qu'il ne voit pas, et qui reste à la relecture humaine

Écrit ici parce qu'un contrôle qui tairait ses trous se lit exactement comme un
contrôle complet, et que l'audit du 8 septembre a trouvé trois divergences dont
**deux** sont hors de portée de tout motif (ADR-007).

**Une affirmation vérifiable qui n'est pas un nombre.** « `mise run check` est
ce qu'une pull request doit passer » était vrai, puis la CI a gagné des jobs que
`check` ne rejoue pas. Aucun motif ne dit qu'une phrase décrivant une commande
a cessé de la décrire. Ce qui protège ici est ailleurs : la description de la
tâche dans `mise.toml`, que quelqu'un lit en la lançant.

**Une affirmation sur le monde extérieur.** Le commentaire de `galaxy.yml`
disait que le site de documentation n'était pas publié, des mois après sa mise
en ligne. Le vérifier demanderait le réseau, que ce contrôle s'interdit : il
doit tourner hors ligne, comme le reste de `mise run check`. Une phrase qui
affirme qu'une chose **n'existe pas** est la plus dangereuse de toutes, parce
qu'elle devient fausse sans que le dépôt bouge.

**Un compte vrai aujourd'hui, écrit à la main.** Les documents publiés en
portent encore : les produits que l'inventaire découvre, les opérations d'un
contrat, les PUT écartés par override, les mutations qui prouvent un verrou.
Tous ont été mesurés justes le 8 septembre, et aucun n'est dérivé : ils
vieilliront en silence. La liste vit dans #140, avec la valeur mesurée de
chacun, plutôt qu'ici où elle serait un compteur de plus.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Ce qui est exclu du suivi, et la raison de chaque exclusion.
#:
#: `CLAUDE.md` n'est pas versionné dans ce dépôt. Les changelogs décrivent ce
#: qu'une version passée portait, et leurs nombres doivent **rester** ceux
#: d'alors.
#:
#: `docs/adr/` pour la même raison, et c'est sa raison d'être : un ADR est
#: historique par construction, il porte sa date, et il est l'endroit où un
#: nombre du passé a le droit de vivre. Y dériver un bloc réécrirait l'histoire
#: à chaque exécution, ce qui est exactement ce qu'un ADR interdit. Voir
#: ADR-007, et `mise run histoire`, qui applique la même frontière au code.
HORS_SUIVI: tuple[Path, ...] = (ROOT / "docs" / "adr",)


def _suivi(chemin: Path) -> bool:
    return not any(exclu in chemin.parents for exclu in HORS_SUIVI)


#: Les fichiers suivis où un compteur périmé se lit comme une mesure.
SURVEILLES: tuple[Path, ...] = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "RELEASING.md",
    ROOT / "SECURITY.md",
    ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "README.md",
    # **Publiée, et pourtant absente d'ici jusqu'à #183.** Le site l'assemble
    # sous « Task playbooks », et elle a porté deux comptes que le temps avait
    # démentis : le nombre de playbooks livrés, et celui des modules que
    # l'exemple appelle. Les deux se lisaient comme des mesures. Une page qu'on
    # publie se surveille.
    ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "playbooks" / "README.md",
    *sorted(chemin for chemin in (ROOT / "docs").rglob("*.md") if _suivi(chemin)),
)

#: Les nombres que ce dépôt écrit en toutes lettres dans ses documents.
#:
#: Ils sont là parce qu'un compteur écrit ainsi échappait au contrôle : le
#: README annonçait un compte de jobs en lettres dans un tableau écrit à la
#: main, sous un bloc dérivé du même fichier qui en donnait un autre. Un motif
#: qui ne cherche que des chiffres ne mesure que la moitié de ce que ce dépôt
#: écrit. ADR-007 porte l'occurrence et sa date.
#:
#: La liste s'arrête aux formes simples : un nombre composé, « twenty-seven
#: jobs », échappe aux deux branches, et la garde de `_NOMBRE` l'exige puisqu'elle
#: refuse un nombre collé à un tiret. Le cas ne s'est jamais présenté, les
#: comptes de ce dépôt tenant sous vingt ; il se présentera peut-être, et il
#: faudra alors l'ajouter plutôt que le découvrir.
_EN_LETTRES = (
    r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|hundred"
)

#: Un nombre, en chiffres ou en lettres, et pas au milieu d'un terme composé.
#:
#: `(?<![-\w])` empêche de lire un compte à l'intérieur d'un terme composé,
#: `Day-2` et `twenty-seven` en étant les deux formes. La garde n'est pas
#: théorique : `histoire.py` l'a payée sur le premier motif de la même famille,
#: et le contrôle signalait des passages sans rapport, ce qui est la façon la
#: plus sûre de le faire désactiver.
_NOMBRE = rf"(?<![-\w])(?:\d+|{_EN_LETTRES})"

#: Les tournures par lesquelles ce dépôt publie une mesure, et le bloc dérivé
#: qui doit la porter. Chacune vient d'une divergence réellement trouvée.
TOURNURES: tuple[tuple[re.Pattern[str], str], ...] = (
    # Le vocabulaire de la CI, en chiffres comme en lettres. C'est la classe
    # qui a produit « four jobs » : un fait vérifiable, publié, que personne ne
    # compare à sa source parce qu'il ne ressemble pas à un chiffre.
    (
        re.compile(
            rf"{_NOMBRE}\s+(?:workflow\s+)?"
            r"(jobs|scanners|required checks|gates|workflows|runners)\b",
            re.I,
        ),
        "compteurs",
    ),
    (re.compile(r"\b\d+\s+unit tests\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s+mutations\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s+modules? (written|played|called|generated)\b", re.I), "compteurs"),
    (re.compile(r"\bout of \d+\s+(modules|operations)\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s+Day-2\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s+(AUTO|MANUAL|IGNORE|LIFECYCLE|UNKNOWN)\b"), "compteurs"),
    (re.compile(r"\bcoverage\s+\d+[.,]\d+\s*%"), "compteurs"),
    (re.compile(r"\b\d+\s+published pages\b", re.I), "compteurs"),
    (re.compile(r"\b\d+\s*/\s*\d+\s+(options|returned keys|examples)\b", re.I), "compteurs"),
)

#: Un bloc dérivé, quel que soit son nom.
#:
#: Le tiret est dans la classe parce qu'un nom de bloc en porte :
#: `runtime-etat`, `ecart-cibles`. Sans lui, ces trois blocs existaient et le
#: contrôle les signalait quand même, ce qui aurait fait chercher un défaut là
#: où il n'y en avait pas.
DEBUT = re.compile(r"<!-- compteurs:(?:[a-z-]+:)?début")
FIN = re.compile(r"<!-- compteurs:(?:[a-z-]+:)?fin")


@dataclass(frozen=True)
class Ecart:
    """Un compteur publié hors d'un bloc dérivé."""

    fichier: Path
    ligne: int
    texte: str
    bloc: str


def _hors_des_blocs(texte: str) -> list[tuple[int, str]]:
    """Les lignes du fichier qui ne sont dans aucun bloc dérivé."""
    dedans = False
    dehors: list[tuple[int, str]] = []
    for rang, ligne in enumerate(texte.splitlines(), start=1):
        if DEBUT.search(ligne):
            dedans = True
            continue
        if FIN.search(ligne):
            dedans = False
            continue
        if not dedans:
            dehors.append((rang, ligne))
    return dehors


def examiner(chemin: Path) -> list[Ecart]:
    """Les compteurs publiés hors bloc dans ce fichier."""
    if not chemin.is_file():
        return []
    ecarts: list[Ecart] = []
    for rang, ligne in _hors_des_blocs(chemin.read_text(encoding="utf-8")):
        for motif, bloc in TOURNURES:
            trouve = motif.search(ligne)
            if trouve:
                ecarts.append(Ecart(chemin, rang, trouve.group(0), bloc))
    return ecarts


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--check", action="store_true", help="échouer sur un compteur hors bloc")
    parseur.parse_args(argv[1:])

    ecarts = [ecart for chemin in SURVEILLES for ecart in examiner(chemin)]
    if not ecarts:
        print(f"{len(SURVEILLES)} fichier(s) examiné(s) : aucun compteur hors d'un bloc dérivé.")
        return 0

    print(f"{len(ecarts)} compteur(s) publié(s) hors d'un bloc dérivé :\n", file=sys.stderr)
    for ecart in ecarts:
        chemin = ecart.fichier.relative_to(ROOT)
        print(f"  {chemin}:{ecart.ligne}  « {ecart.texte} »", file=sys.stderr)
    print(
        "\nUn nombre écrit à la main vieillit en silence et se lit exactement\n"
        "comme une mesure. Encadrer le passage par un bloc dérivé :\n"
        "    <!-- compteurs:<nom>:début, produits par scripts/readme_counters.py -->\n"
        "    ...\n"
        "    <!-- compteurs:<nom>:fin -->\n"
        "puis produire ce bloc dans `scripts/readme_counters.py`.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
