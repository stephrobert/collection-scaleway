"""L'histoire va dans les ADR, le code dit l'invariant.

Les commentaires de ce dépôt expliquent beaucoup, et c'est ce qui fait leur
valeur : « on avait découvert que… », « au début il y avait bien moins de
modules… ». Le raisonnement se transmet, et **le nombre finit faux**. Des
docstrings portaient un compte de tests que la mesure démentait, une autre un
compte de modules inférieur à ce que la collection publie, et deux copies d'un
même tableau ne disaient déjà plus la même chose. Aucune n'était fausse le jour
où elle a été écrite : ADR-007 les relève, avec leurs nombres et leur date.

La règle tient en une phrase :

> Un nombre qui compte des choses du dépôt n'a pas sa place dans une phrase.
> S'il est vrai, quelque chose doit le faire rougir quand il change : une
> assertion, un golden, un bloc dérivé. S'il est historique, il va dans un ADR,
> qui porte sa date.

Ce contrôle est la forme exécutable de cette phrase. Il lit les commentaires et
les docstrings du code Python, et refuse un nombre accolé à un nom de chose que
ce dépôt produit. Il ne juge pas si le nombre est vrai : le juger demanderait de
le recalculer, donc une seconde source qui divergerait de la première. Il juge
**où il est écrit**.

Ce qu'il ne regarde pas, et pourquoi :

* `docs/adr/`, qui est historique par construction et porte une date ;
* les documents publiés, tenus par `scripts/chiffres.py`, qui applique la même
  règle avec l'autre issue : un bloc dérivé plutôt qu'un ADR ;
* les chaînes de caractères qui ne sont pas des docstrings : un compteur qu'un
  programme calcule n'est pas une phrase qui vieillit.

    python scripts/histoire.py
"""

from __future__ import annotations

import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Les arbres de code lus. `docs/` n'en fait pas partie : les documents publiés
#: relèvent de `scripts/chiffres.py`, et `docs/adr/` est justement l'endroit où
#: un nombre historique a le droit de vivre.
ARBRES = (
    ROOT / "generator",
    ROOT / "scripts",
    ROOT / "tests",
    ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "plugins",
)

#: Les nombres qui comptent. `un`, `une` et `deux` en sont absents : ce sont des
#: articles bien plus souvent que des comptes, et une règle qui refuserait « un
#: module porte une opération » serait une gêne qu'on désactiverait au lieu de
#: la respecter.
#:
#: Deux précautions que la première version n'avait pas, et qui produisaient
#: chacune un faux positif : la garde `(?<![-\w])` empêche de lire « sept » dans
#: « trente-sept », et les composés viennent **avant** leurs parties, l'alternance
#: de Python retenant la première branche qui accroche et non la plus longue.
NOMBRE = (
    r"(?<![-\w])(?:(?<![\d.,])\d+(?![\d.,]\d)|dix-sept|dix-huit|dix-neuf|trois|quatre|"
    r"cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|seize|vingt|trente|"
    r"quarante|cinquante|soixante|cent|cents)"
)

#: Ce que ce dépôt produit et compte. Le pluriel seulement : au singulier, le
#: nombre qui précède est un article.
CHOSES = (
    r"(?:modules|op[ée]rations|d[ée]fauts|m[ée]thodes|tests|mutations|champs|options|"
    r"param[èe]tres|produits|ressources|plugins|contrats|r[èe]gles|fichiers|lignes|"
    r"pages|versions|enums|playbooks|exemples|gardes|retours|cl[ée]s|entr[ée]es|"
    r"appels|routes|jobs|t[âa]ches|overrides|fragments|sch[ée]mas|couvertures)"
)

#: Le nom peut être séparé du nombre par un retour à la ligne, un commentaire
#: étant réécrit à la largeur de la colonne. Chercher sur la ligne seule aurait
#: laissé passer « 41\n        opérations », qui est exactement le cas mesuré.
MOTIF = re.compile(rf"\b(?P<phrase>{NOMBRE}\s+{CHOSES})\b", re.IGNORECASE)


@dataclass(frozen=True)
class Ecart:
    """Un nombre trouvé là où il vieillira sans que rien ne le dise."""

    fichier: Path
    ligne: int
    texte: str

    def __str__(self) -> str:
        chemin = self.fichier.relative_to(ROOT) if self.fichier.is_absolute() else self.fichier
        return f"{chemin}:{self.ligne} « {self.texte} »"


def prose(source: str) -> list[tuple[int, str]]:
    """Rend les commentaires et les docstrings, avec leur ligne de départ.

    Une docstring se reconnaît à ce qu'elle ouvre son instruction : c'est ce qui
    la sépare d'une chaîne de données, qu'un programme calcule et qui ne
    vieillit pas toute seule.
    """
    trouves: list[tuple[int, str]] = []
    try:
        jetons = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return trouves
    for jeton in jetons:
        commentaire = jeton.type == tokenize.COMMENT
        docstring = jeton.type == tokenize.STRING and jeton.line.lstrip().startswith(('"""', "'''"))
        if commentaire or docstring:
            trouves.append((jeton.start[0], jeton.string))
    return trouves


def examiner(chemin: Path) -> list[Ecart]:
    """Les nombres historiques d'un fichier, dans l'ordre où ils s'y lisent."""
    ecarts: list[Ecart] = []
    for depart, texte in prose(chemin.read_text(encoding="utf-8")):
        for trouve in MOTIF.finditer(texte):
            avant = texte[: trouve.start()]
            ecarts.append(
                Ecart(
                    fichier=chemin,
                    ligne=depart + avant.count("\n"),
                    texte=" ".join(trouve.group("phrase").split()),
                )
            )
    return ecarts


def fichiers() -> list[Path]:
    """Le code lu, trié pour que deux exécutions rendent le même rapport."""
    return sorted(
        chemin
        for arbre in ARBRES
        for chemin in arbre.rglob("*.py")
        if "__pycache__" not in chemin.parts
    )


def main() -> int:
    lus = fichiers()
    if not lus:
        print(
            "aucun fichier examiné : un contrôle qui ne lit rien rend vert sur n'importe quoi.",
            file=sys.stderr,
        )
        return 1

    ecarts = [ecart for chemin in lus for ecart in examiner(chemin)]
    if ecarts:
        for ecart in ecarts:
            print(f"  {ecart}", file=sys.stderr)
        print(
            f"\n{len(ecarts)} nombre(s) comptant des choses du dépôt, écrits dans une "
            "phrase.\nUn nombre vrai se prouve par une assertion, un golden ou un bloc "
            "dérivé ;\nun nombre historique va dans `docs/adr/`, qui porte sa date. Une "
            "phrase\nn'est ni l'un ni l'autre : elle vieillit sans que rien ne le dise.",
            file=sys.stderr,
        )
        return 1

    print(f"{len(lus)} fichier(s) examiné(s) : aucun nombre historique dans une phrase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
