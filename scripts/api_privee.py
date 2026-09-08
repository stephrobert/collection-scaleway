"""Aucun attribut privé d'une bibliothèque tierce dans ce qui est livré.

Le runtime a été réécrit pour ne plus appeler `scaleway_core.api.API._request`,
**parce que c'était privé** : un souligné n'est pas un contrat, et une version
mineure du SDK peut le déplacer sans rien promettre à personne. Le même runtime
écrivait ensuite `requests.Response._content` pour y glisser `total_count`
(#132). Un dépôt qui documente pourquoi il ne dépend pas d'une API privée doit
l'être jusque dans sa propre couche HTTP.

Ce contrôle lit `plugins/` par AST et refuse un accès à un attribut souligné
**sur une valeur qui n'est pas `self`**. C'est la frontière qui compte :

```python
self._client            # à soi, et c'est le style de tout le fichier
response._content       # à requests, et c'est le défaut
client._profile         # au SDK, même famille
```

**Ce qu'il ne sait pas faire.** Il ne remonte pas le type d'une expression : un
attribut souligné sur une variable locale est refusé sans qu'il sache à quoi
elle appartient. C'est délibéré, et c'est le sens du refus : dans du code livré,
un souligné sur autre chose que `self` demande à être justifié, et une
justification s'écrit. Rien ne l'écrit automatiquement, donc rien ne l'excuse
en silence.

Les tests ne sont pas examinés : ils fabriquent des doubles, et poser un
attribut souligné sur un objet factice n'engage aucune dépendance.

    python scripts/api_privee.py

Codes de sortie : `0` conforme, `1` erreur, `2` accès refusé.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Ce qui est livré, et donc tenu par cette règle.
LIVRE = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "plugins"


def _est_dunder(nom: str) -> bool:
    """Un protocole public de Python, pas un attribut privé.

    `__init__`, `__name__` et leurs semblables sont documentés par le langage
    lui-même. Les refuser ferait un contrôle qu'on désactive.
    """
    return nom.startswith("__") and nom.endswith("__")


@dataclass(frozen=True)
class Acces:
    """Un attribut souligné lu ou écrit sur autre chose que `self`."""

    fichier: Path
    ligne: int
    expression: str


def _porteur(noeud: ast.expr) -> str:
    """Le nom de ce sur quoi on lit, tel qu'il est écrit dans le code."""
    if isinstance(noeud, ast.Name):
        return noeud.id
    if isinstance(noeud, ast.Attribute):
        return f"{_porteur(noeud.value)}.{noeud.attr}"
    if isinstance(noeud, ast.Call):
        return f"{_porteur(noeud.func)}()"
    return type(noeud).__name__


def examiner(chemin: Path) -> list[Acces]:
    """Les accès privés hors `self` de ce fichier."""
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    trouves: list[Acces] = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Attribute) or not noeud.attr.startswith("_"):
            continue
        if _est_dunder(noeud.attr):
            continue
        if isinstance(noeud.value, ast.Name) and noeud.value.id in ("self", "cls"):
            continue
        trouves.append(
            Acces(chemin, noeud.lineno, f"{_porteur(noeud.value)}.{noeud.attr}"),
        )
    return trouves


def main(argv: list[str]) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)

    fichiers = sorted(LIVRE.rglob("*.py"))
    if not fichiers:
        print(
            f"aucun fichier examiné sous {LIVRE.relative_to(ROOT)} : "
            "un contrôle qui ne regarde rien passe toujours.",
            file=sys.stderr,
        )
        return 1

    acces = [entree for chemin in fichiers for entree in examiner(chemin)]
    if not acces:
        print(f"{len(fichiers)} fichier(s) livré(s) : aucun accès à une API privée.")
        return 0

    print(f"{len(acces)} accès à un attribut privé dans du code livré :\n", file=sys.stderr)
    for entree in acces:
        chemin = entree.fichier.relative_to(ROOT)
        print(f"  {chemin}:{entree.ligne}  {entree.expression}", file=sys.stderr)
    print(
        "\nUn souligné n'est pas un contrat : la bibliothèque peut le déplacer "
        "sans rien promettre.\nCe dépôt a déjà quitté `API._request` pour cette "
        "raison, puis écrit `Response._content`.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
