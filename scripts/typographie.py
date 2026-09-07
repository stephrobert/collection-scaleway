"""Le tiret cadratin, que ce dépôt refuse dans les deux langues.

La règle était écrite, et rien ne la mesurait. Le dépôt en portait cent
quatre-vingt-quatorze, presque tous écrits en une semaine, et personne ne les
avait vus : un cadratin ne casse rien, ne rougit nulle part, et se relit comme
de la prose ordinaire. C'est exactement la définition d'une règle qui n'est
qu'un commentaire.

**Pourquoi cette règle plutôt qu'une autre.** Le cadratin en incise est la
signature d'une prose écrite par un modèle, et ce dépôt est écrit avec des
modèles. La ponctuation qu'il remplace dit toujours quelque chose de plus
précis : un deux-points annonce, une virgule coordonne, une parenthèse met à
part. Le cadratin fait les trois indistinctement, et il les fait partout.

Ce contrôle ne propose pas de correction. Le remplacement dépend de ce que
l'incise fait, et une substitution unique mettrait la même ponctuation partout,
ce qui produirait des phrases fausses. Il dit où, le reste est un travail de
rédaction.

    python scripts/typographie.py
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Le caractère refusé, écrit par son point de code et non littéralement.
#:
#: Ce n'est pas de la coquetterie : écrit tel quel, il se signalerait lui-même
#: au premier passage, et la seule issue serait d'exempter ce fichier, donc
#: d'ouvrir un trou dans le contrôle pour le confort de son auteur. Le défaut
#: est passé inaperçu jusqu'à ce que le fichier soit versionné, `git ls-files`
#: ne listant pas encore ce qu'on vient d'écrire.
CADRATIN = "\u2014"

#: Les fichiers qu'on ne lit pas. Le verrou des dépendances et les golden sont
#: produits par un outil : leur contenu n'est pas de la prose, et le tiret y
#: appartiendrait à une donnée amont plutôt qu'à une phrase de ce dépôt.
IGNORES = (
    "requirements-dev.lock",
    "tests/fixtures/",
    "specs/",
)

#: Les répertoires que le repli saute, et que git ignore de toute façon.
NON_VERSIONNES = frozenset({"__pycache__", "build", "dist", "node_modules"})

#: Les répertoires en point que ce dépôt suit vraiment.
#:
#: **Une liste noire de caches serait toujours en retard** sur le prochain outil
#: qui pose le sien : le repli lisait `.hypothesis/constants/`, où Hypothesis
#: range un dépôt des chaînes littérales du code, et y trouvait le caractère
#: refusé. Un répertoire en point est donc sauté par défaut, et ceux-ci sont
#: nommés. L'oubli d'un nom fait sauter un répertoire suivi dans un bac à sable,
#: ce qui se voit ; l'oubli d'un cache faisait signaler une faute inexistante.
POINTS_SUIVIS = frozenset({".github", ".claude", ".clusterfuzzlite"})

#: Ce qu'on lit quand on parcourt le disque. Le repli ne doit pas ouvrir les
#: binaires du dépôt : `examiner` les tolère, mais les lire tous coûterait
#: inutilement.
SUFFIXES = frozenset(
    {".py", ".md", ".yml", ".yaml", ".toml", ".sh", ".cfg", ".txt", ".j2", ".rst", ""}
)


@dataclass(frozen=True)
class Ecart:
    """Un cadratin, là où il faut choisir une ponctuation à sa place."""

    fichier: str
    ligne: int
    texte: str

    def __str__(self) -> str:
        return f"{self.fichier}:{self.ligne} {self.texte.strip()[:96]}"


def _suivis_par_git() -> list[str] | None:
    """Ce que git connaît, ou `None` s'il n'y a pas de dépôt ici."""
    resultat = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if resultat.returncode != 0:
        return None
    return [chemin for chemin in resultat.stdout.split("\n") if chemin]


def _parcourus() -> list[str]:
    """Le repli : le disque, moins ce que git ignorerait de toute façon."""
    trouves: list[str] = []
    for chemin in ROOT.rglob("*"):
        if not chemin.is_file() or chemin.suffix not in SUFFIXES:
            continue
        relatif = chemin.relative_to(ROOT)
        dossiers = relatif.parts[:-1]
        if NON_VERSIONNES.intersection(dossiers):
            continue
        if any(part.startswith(".") and part not in POINTS_SUIVIS for part in dossiers):
            continue
        trouves.append(relatif.as_posix())
    return sorted(trouves)


def fichiers() -> list[str]:
    """Les fichiers à lire, hors de ce qu'un outil produit.

    **`git ls-files` d'abord, et un repli quand il n'y a pas de dépôt.** La
    liste de git est la bonne source : elle dit exactement ce qui est publié, et
    elle écarte `build/`, `.venv/` et les artefacts sans avoir à les nommer.

    Elle manque pourtant là où ce contrôle doit précisément tenir : le harnais
    de falsification travaille dans une **copie hors dépôt**, sans `.git`, et un
    contrôle qui y plante ne peut pas être prouvé. Une archive téléchargée pose
    le même problème. Le repli parcourt donc le disque, en sautant ce que git
    aurait sauté.
    """
    connus = _suivis_par_git()
    lus = connus if connus is not None else _parcourus()
    return [chemin for chemin in lus if not any(chemin.startswith(ignore) for ignore in IGNORES)]


def examiner(chemin: str) -> list[Ecart]:
    """Les cadratins d'un fichier, avec leur ligne.

    Un fichier binaire ou dans un autre encodage ne fait pas échouer le
    contrôle : il ne porte pas de prose, et un contrôle qui plante sur un
    fichier inattendu finit désactivé.
    """
    try:
        texte = (ROOT / chemin).read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        return []
    return [
        Ecart(fichier=chemin, ligne=numero, texte=ligne)
        for numero, ligne in enumerate(texte.splitlines(), 1)
        if CADRATIN in ligne
    ]


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
            f"\n{len(ecarts)} tiret(s) cadratin(s). Choisir la ponctuation que "
            "l'incise\nappelle vraiment : un deux-points annonce, une virgule "
            "coordonne, une\nparenthèse met à part. Pas de substitution unique, "
            "elle produirait des\nphrases fausses.",
            file=sys.stderr,
        )
        return 1

    print(f"{len(lus)} fichier(s) examiné(s) : aucun tiret cadratin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
