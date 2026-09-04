"""Ce qui doit être vrai avant de publier, et qu'une version publiée fige.

Une version publiée sur Galaxy est **immuable** : republier la même rend
``conflict.collection_exists``. Il n'y a pas de correction, seulement une
version de plus. Tout ce que ce script refuse coûterait donc un numéro.

    python scripts/release.py --check          juge HEAD et son tag
    python scripts/release.py --check --tag 0.1.0

Quatre refus, et chacun a coûté quelque chose à quelqu'un ailleurs :

1. **le tag et `galaxy.yml` doivent concorder.** L'archive est nommée d'après
   `galaxy.yml`, pas d'après le tag : les deux peuvent diverger sans que rien
   ne le dise, et on publie alors une version que l'historique ne porte pas ;
2. **le tag doit désigner HEAD.** Publier depuis un arbre en avance du tag
   livre du code que personne ne retrouvera à ce numéro ;
3. **l'arbre doit être propre.** Une archive construite sur des modifications
   non versionnées ne se reproduit pas ;
4. **le changelog ne doit rien laisser en attente.** Les fragments décrivent ce
   que la version apporte ; ceux qui restent décrivent une version qui ne sort
   pas. Mesuré sur ce dépôt : douze fragments accumulés sous une `0.1.0`
   composée quand la collection portait un module.

Ce script ne publie pas et ne parle à personne. Il dit si on peut.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]

#: Le versionnement sémantique, qu'Ansible impose aux collections.
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


class ReleaseError(RuntimeError):
    """La publication ne peut pas partir, et il vaut mieux le dire avant."""


def _git(*args: str) -> str:
    resultat = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return resultat.stdout.strip()


def normaliser(tag: str) -> str:
    """`v0.1.0` et `0.1.0` désignent la même version.

    Les deux conventions existent, et refuser l'une des deux ferait perdre une
    version à qui se trompe de forme, pour une raison qui n'a rien à voir avec
    le contenu.
    """
    return tag[1:] if tag.startswith("v") else tag


def tag_de_head() -> str | None:
    """Le tag qui désigne exactement HEAD, s'il y en a un."""
    return _git("describe", "--exact-match", "--tags", "HEAD") or None


def fragments_en_attente(collection_path: Path) -> list[str]:
    """Les fragments de changelog qu'aucune version n'a encore absorbés."""
    dossier = collection_path / "changelogs" / "fragments"
    if not dossier.is_dir():
        return []
    return sorted(f.name for f in dossier.glob("*.yml") if not f.name.startswith("."))


def controler(tag: str | None) -> list[str]:
    """Rend la liste des refus. Vide veut dire qu'on peut publier."""
    collection = load_collection()
    refus: list[str] = []

    if not SEMVER.match(collection.version):
        refus.append(
            f"`galaxy.yml` déclare la version {collection.version!r}, qui n'est pas du "
            "versionnement sémantique. Ansible l'impose aux collections."
        )

    if tag is None:
        refus.append(
            "aucun tag ne désigne HEAD. Une version publiée doit être retrouvable dans "
            "l'historique : `git tag -s <version>` avant de publier."
        )
    elif normaliser(tag) != collection.version:
        refus.append(
            f"le tag dit {normaliser(tag)!r} et `galaxy.yml` dit {collection.version!r}. "
            "L'archive est nommée d'après `galaxy.yml` : on publierait une version que "
            "l'historique ne porte pas."
        )

    sale = _git("status", "--porcelain")
    if sale:
        lignes = sale.splitlines()
        refus.append(
            f"l'arbre porte {len(lignes)} modification(s) non versionnée(s) : une archive "
            "construite dessus ne se reproduit pas.\n    "
            + "\n    ".join(lignes[:5])
            + ("\n    ..." if len(lignes) > 5 else "")
        )

    fragments = fragments_en_attente(collection.path)
    if fragments:
        refus.append(
            f"{len(fragments)} fragment(s) de changelog en attente : ils décrivent ce que "
            "cette version apporte, et resteraient dehors.\n    "
            + "\n    ".join(fragments[:5])
            + ("\n    ..." if len(fragments) > 5 else "")
            + "\n    Composer la version avec `antsibull-changelog release`."
        )

    return refus


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--check", action="store_true", required=True)
    parseur.add_argument(
        "--tag",
        default=None,
        help="le tag à juger ; par défaut celui qui désigne exactement HEAD",
    )
    arguments = parseur.parse_args(argv[1:])

    tag = arguments.tag if arguments.tag is not None else tag_de_head()
    refus = controler(tag)

    if refus:
        print(
            f"{len(refus)} refus avant publication. Une version publiée sur Galaxy est "
            "immuable :\n",
            file=sys.stderr,
        )
        for raison in refus:
            print(f"  - {raison}", file=sys.stderr)
        return 1

    collection = load_collection()
    print(
        f"{collection.fqcn} {collection.version} : le tag concorde, l'arbre est propre, "
        "le changelog est composé."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
