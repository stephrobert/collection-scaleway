"""Décide le prochain numéro de version depuis les fragments, et le pose.

**Le numéro se déduit, il ne se saisit pas.** Une version tapée à la main est
un nombre recopié de plus, et ce dépôt en a corrigé quatre en deux jours. Ce
qu'une version promet est déjà écrit dans les fragments de changelog : une
rupture, un ajout, ou une correction. Il n'y a donc rien à décider, seulement à
lire.

    python scripts/version.py --show      ce que les fragments impliquent
    python scripts/version.py --bump      écrit galaxy.yml et compose le changelog

La règle, qui est celle du versionnement sémantique qu'Ansible impose :

| ce que les fragments portent | ce qui bouge |
|---|---|
| `breaking_changes`, `removed_features` | **majeure** |
| `major_changes`, `minor_changes`, `deprecated_features` | **mineure** |
| `bugfixes`, `security_fixes` seuls | **correctif** |

**Avant `1.0.0`, une rupture ne fait pas passer à `1.0.0`.** Le passage à la
version majeure est une décision humaine, celle de dire que les interfaces sont
stables. Une rupture en pré-1.0 incrémente donc la mineure, ce que le
versionnement sémantique autorise explicitement et que le README de la
collection annonce déjà : « avant `1.0.0`, considérez les interfaces comme
évolutives ».
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

#: Ce qu'une section de fragment implique. L'ordre compte : le premier trouvé
#: gagne, du plus fort au plus faible.
IMPLICATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("majeure", ("breaking_changes", "removed_features")),
    ("mineure", ("major_changes", "minor_changes", "deprecated_features")),
    ("correctif", ("bugfixes", "security_fixes", "trivial")),
)


class VersionError(RuntimeError):
    """On ne peut pas décider, et il vaut mieux le dire que choisir au hasard."""


def sections_en_attente(collection_path: Path) -> dict[str, list[str]]:
    """Les sections que portent les fragments, et le fichier de chacune."""
    dossier = collection_path / "changelogs" / "fragments"
    if not dossier.is_dir():
        return {}
    trouve: dict[str, list[str]] = {}
    for fichier in sorted(dossier.glob("*.yml")):
        if fichier.name.startswith("."):
            continue
        contenu = yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}
        if not isinstance(contenu, dict):
            raise VersionError(f"{fichier.name} n'est pas un document YAML de fragment")
        for section in contenu:
            trouve.setdefault(str(section), []).append(fichier.name)
    return trouve


def portee(sections: dict[str, list[str]]) -> str | None:
    """Ce que ces fragments impliquent : majeure, mineure, correctif, ou rien."""
    for echelon, declencheurs in IMPLICATIONS:
        if any(section in sections for section in declencheurs):
            return echelon
    return None


def suivante(version: str, echelon: str) -> str:
    """Le numéro suivant, selon l'échelon.

    **Une rupture en pré-1.0 n'impose pas `1.0.0`.** Décider que les interfaces
    sont stables est un acte humain, pas la conséquence mécanique d'un fragment.
    La rupture incrémente donc la mineure tant que la majeure vaut zéro.
    """
    correspondance = SEMVER.match(version)
    if not correspondance:
        raise VersionError(f"{version!r} n'est pas du versionnement sémantique, qu'Ansible impose")
    majeure, mineure, correctif = (int(x) for x in correspondance.groups())

    if echelon == "majeure":
        if majeure == 0:
            return f"0.{mineure + 1}.0"
        return f"{majeure + 1}.0.0"
    if echelon == "mineure":
        return f"{majeure}.{mineure + 1}.0"
    return f"{majeure}.{mineure}.{correctif + 1}"


def ecrire_version(collection_path: Path, version: str) -> None:
    """Réécrit la seule ligne `version:` de `galaxy.yml`.

    Une réécriture par YAML perdrait les commentaires, qui portent les raisons
    de chaque champ : sur ce fichier, ils valent plus que la commodité.
    """
    chemin = collection_path / "galaxy.yml"
    texte = chemin.read_text(encoding="utf-8")
    nouveau, remplacements = re.subn(
        r"^version:\s*\S+$", f"version: {version}", texte, count=1, flags=re.M
    )
    if remplacements != 1:
        raise VersionError(f"{chemin} ne porte pas exactement une ligne `version:`")
    chemin.write_text(nouveau, encoding="utf-8")


def composer(version: str) -> None:
    """Fait absorber les fragments par `antsibull-changelog`."""
    resultat = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "changelog.py"), "release", "--version", version],
        cwd=ROOT,
        check=False,
    )
    if resultat.returncode != 0:
        raise VersionError("`antsibull-changelog release` a échoué")


def figer_les_apparitions(version: str) -> None:
    """Date sous `version` tout ce que le journal des apparitions ne connaît pas.

    **C'est ici que ça se fige, et pas ailleurs.** Un module écrit pendant le
    cycle porte la version en préparation ; s'il n'est pas inscrit au moment de
    publier, le cycle suivant lui donnera une date qui n'est plus la sienne
    (ADR-013). Le figeage appartient donc à la commande qui pose le numéro.
    """
    resultat = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "introductions.py"), "--enregistrer", version],
        cwd=ROOT,
        check=False,
    )
    if resultat.returncode != 0:
        raise VersionError("le journal des apparitions n'a pas pu être figé")


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    groupe = parseur.add_mutually_exclusive_group(required=True)
    groupe.add_argument("--show", action="store_true", help="dire ce que les fragments impliquent")
    groupe.add_argument("--bump", action="store_true", help="écrire la version et composer")
    arguments = parseur.parse_args(argv[1:])

    try:
        collection = load_collection()
        sections = sections_en_attente(collection.path)
        echelon = portee(sections)
    except VersionError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return 1

    if echelon is None:
        print(
            f"{collection.version} : aucun fragment en attente, donc rien à publier.\n"
            "Une version sans changement décrit n'apporte rien à personne."
        )
        return 1

    cible = suivante(collection.version, echelon)
    print(f"  {collection.version} -> {cible}   ({echelon})")
    for _echelon, declencheurs in IMPLICATIONS:
        presentes = [s for s in declencheurs if s in sections]
        for section in presentes:
            print(f"    {section:20s} {', '.join(sections[section])}")

    if arguments.show:
        return 0

    try:
        ecrire_version(collection.path, cible)
        composer(cible)
        figer_les_apparitions(cible)
    except VersionError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return 1

    print(
        f"\n{cible} est écrite dans galaxy.yml et le changelog est composé.\n"
        "Reste à relire le diff, committer, puis taguer :\n"
        f"  git tag -s {cible} -m 'stephrobert.scaleway {cible}'\n"
        f"  git push origin {cible}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
