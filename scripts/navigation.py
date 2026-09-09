"""Le site annonce ce qu'il sert, et sert l'usage en premier.

Le site publié agrégeait trois documentations dans un seul menu sans dire
laquelle sert à quoi, et ouvrait sur l'architecture du générateur : une page
sous « Use », dix-neuf sous « Decisions ». Quelqu'un qui venait d'installer la
collection tombait dans le pipeline OpenAPI (#164).

**Ce contrôle ne juge pas le goût.** Un ratio de pages avec un seuil serait un
nombre inventé, et le refuser au nom d'une porte ferait exactement ce que ce
dépôt reproche ailleurs. Il vérifie quatre faits binaires :

* la première section de la navigation est celle de l'usage ;
* elle sert la page assemblée depuis le README, celle que Galaxy publie ;
* la page d'accueil nomme les deux parcours ;
* Sphinx est configuré en anglais, comme tout ce que le dépôt publie.

    python scripts/navigation.py

Codes de sortie : `0` conforme, `1` erreur, `2` la navigation ne dit plus ça.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.md"
CONF = ROOT / "docs" / "conf.py"

#: La page d'usage, assemblée depuis le README de la collection par `docsite`.
USAGE = "guides/using-the-collection"

#: La référence groupée par produit, assemblée depuis le plan par `docsite`.
#:
#: `antsibull` rend les modules à plat, et la section « Reference » doit ouvrir
#: sur ce qui les ordonne, pas sur la liste alphabétique.
REFERENCE = "guides/module-reference"

#: Ce que la première section doit annoncer. Le mot compte : « Use » seul
#: décrivait déjà l'ancienne section, celle qui ne portait qu'une page.
PREMIERE_SECTION = "Use the collection"

_CAPTION = re.compile(r"^:caption:\s*(.+)$", re.MULTILINE)


class NavigationError(RuntimeError):
    """La navigation n'a pas pu être lue."""


def sections(texte: str) -> list[tuple[str, list[str]]]:
    """Les sections de la navigation, dans l'ordre, avec leurs pages."""
    trouvees: list[tuple[str, list[str]]] = []
    for bloc in texte.split("```{toctree}")[1:]:
        corps = bloc.split("```", 1)[0]
        titre = _CAPTION.search(corps)
        pages = [
            ligne.strip()
            for ligne in corps.splitlines()
            if ligne.strip() and not ligne.strip().startswith(":")
        ]
        trouvees.append((titre.group(1).strip() if titre else "", pages))
    return trouvees


def refus(index: str, conf: str) -> list[str]:
    """Ce qui ne va pas, nommé. Vide quand la navigation dit ce qu'elle doit."""
    manques: list[str] = []
    ordonnees = sections(index)
    if not ordonnees:
        raise NavigationError(
            f"{INDEX.relative_to(ROOT)} ne porte aucune `toctree` : un contrôle qui "
            "ne lit rien rend vert sur n'importe quoi."
        )

    titre, pages = ordonnees[0]
    if titre != PREMIERE_SECTION:
        manques.append(
            f"la première section s'appelle {titre!r} et non {PREMIERE_SECTION!r} : "
            "un lecteur qui vient d'installer la collection lit celle-là d'abord"
        )
    if USAGE not in pages:
        manques.append(
            f"la première section ne sert pas `{USAGE}`, la page assemblée depuis le "
            "README que Galaxy publie"
        )
    reference = next((pages for titre, pages in ordonnees if titre == "Reference"), [])
    if reference and reference[0] != REFERENCE:
        manques.append(
            f"la section « Reference » n'ouvre pas sur `{REFERENCE}` : un lecteur y "
            "tombe sur la liste alphabétique que rend antsibull, et non sur ce qui "
            "l'ordonne"
        )
    if "Use the collection" not in index or "Build the collection" not in index:
        manques.append(
            "la page d'accueil ne nomme pas ses deux parcours : sans eux, le site "
            "n'annonce pas à quoi il sert"
        )
    if 'language = "en"' not in conf:
        manques.append(
            "Sphinx n'est pas configuré en anglais, alors que ce site est publié : "
            "l'habillage sortirait en français autour d'un contenu anglais"
        )
    return manques


def main() -> int:
    try:
        manques = refus(INDEX.read_text(encoding="utf-8"), CONF.read_text(encoding="utf-8"))
    except (OSError, NavigationError) as erreur:
        print(str(erreur), file=sys.stderr)
        return 1

    if manques:
        print(
            f"{len(manques)} chose(s) que la navigation du site ne dit plus :\n"
            + "\n".join(f"  {ligne}" for ligne in manques),
            file=sys.stderr,
        )
        return 2

    print("le site annonce ses deux parcours, et sert l'usage en premier.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
