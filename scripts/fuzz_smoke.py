"""Rejoue le harnais de fuzzing sur des cas dérivés du contrat réel.

**Un harnais qui ne tourne que dans le conteneur d'OSS-Fuzz est un harnais que
personne ne relit.** ClusterFuzzLite l'exécute pendant dix minutes sur chaque
pull request, ce qui prouve qu'il trouve ; ceci prouve qu'il **marche**, en
quelques secondes, hors ligne, dans `mise run check`.

Les cas ne sont pas du bruit : ils viennent des contrats versionnés, mutés d'une
façon que l'amont peut vraiment produire. Un champ retiré, un type remplacé, une
référence qui ne pointe nulle part, une profondeur qui double. C'est là que le
parser suppose une forme.
"""

from __future__ import annotations

import copy
import random
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "fuzz"))

from fuzz_parser import examiner  # noqa: E402

SPECS = ROOT / "specs" / "scaleway"

#: Ce qu'on fait subir au document, et ce que chaque mutation imite.
MUTATIONS = (
    ("champ retiré", "une clé que l'amont cesse d'émettre"),
    ("type remplacé", "un champ qui change de forme entre deux versions"),
    ("référence morte", "un `$ref` vers un schéma supprimé"),
    ("valeur nulle", "un champ optionnel rendu à `null`"),
)


class FuzzError(RuntimeError):
    """Le harnais a trouvé autre chose qu'un refus déclaré."""


def _chemins(noeud: Any, prefixe: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    """Tous les chemins d'un document, pour pouvoir en muter un au hasard."""
    trouve = [prefixe] if prefixe else []
    if isinstance(noeud, dict):
        for cle, valeur in noeud.items():
            trouve.extend(_chemins(valeur, (*prefixe, cle)))
    elif isinstance(noeud, list):
        for rang, valeur in enumerate(noeud):
            trouve.extend(_chemins(valeur, (*prefixe, rang)))
    return trouve


def _muter(document: Any, chemin: tuple[Any, ...], genre: str) -> None:
    parent: Any = document
    for etape in chemin[:-1]:
        parent = parent[etape]
    cle = chemin[-1]
    if genre == "champ retiré":
        if isinstance(parent, dict):
            parent.pop(cle, None)
        elif isinstance(parent, list) and isinstance(cle, int) and cle < len(parent):
            parent.pop(cle)
    elif genre == "type remplacé":
        parent[cle] = [{"un": "objet"}] if isinstance(parent[cle], (str, int)) else "une chaîne"
    elif genre == "référence morte":
        parent[cle] = {"$ref": "#/components/schemas/ceci.nexiste.pas"}
    elif genre == "valeur nulle":
        parent[cle] = None


def main(argv: list[str]) -> int:
    passages = int(argv[1]) if len(argv) > 1 else 300
    contrats = sorted(SPECS.glob("*.yml"))
    if not contrats:
        print(f"erreur : aucun contrat dans {SPECS}", file=sys.stderr)
        return 1

    # Graine fixe : un fuzzer qui ne rejoue pas la même séquence ne se
    # débogue pas, et ce harnais sert à trouver puis à prouver le correctif.
    hasard = random.Random(20260906)
    documents = [yaml.safe_load(chemin.read_text(encoding="utf-8")) for chemin in contrats]
    joues = 0
    for _ in range(passages):
        original = hasard.choice(documents)
        genre, _pourquoi = hasard.choice(MUTATIONS)
        mute = copy.deepcopy(original)
        chemins = _chemins(mute)
        if not chemins:
            continue
        _muter(mute, hasard.choice(chemins), genre)
        try:
            examiner(mute)
        # Attraper large est ici le sujet : tout ce qui n'est pas un refus
        # déclaré par le harnais est ce que le fuzzer cherche.
        except Exception as erreur:
            raise FuzzError(
                f"{type(erreur).__name__} sur une mutation « {genre} » : {erreur}\n"
                "Le parser a supposé une forme que le contrat peut ne pas avoir."
            ) from erreur
        joues += 1

    print(f"{joues} document(s) mutés passés au parser, sur {len(contrats)} contrat(s)")
    print("aucun refus non déclaré : le parser refuse, il ne casse pas.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except FuzzError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
