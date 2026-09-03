"""Ce que le parser ne couvre pas, mesuré sur chaque contrat versionné.

**À passer sur le contrat d'un produit avant de l'importer.** Le parser ne
couvre pas tout OpenAPI, et c'est délibéré : généraliser sans cas déclenchant
produit du code que rien ne juge. La liste des travaux se déduit donc de ce que
ce script trouve, et chaque ajout a son cas.

Le second produit a prouvé que ça marche. Sur Instance, sept des huit
constructions n'apparaissaient jamais et la huitième, `page_size`, valait zéro.
Le Load Balancer l'emploie, et onze de ses listes rendaient leur première page
en silence faute d'être reconnues comme paginées.

    python scripts/parser_coverage.py            # tous les contrats versionnés
    python scripts/parser_coverage.py lb v1      # un seul

Le code de sortie est 0 : ce script **mesure**, il ne juge pas. Une construction
présente n'est pas un défaut, c'est un travail à décider.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "specs" / "scaleway"

VERBES = {"get", "post", "put", "patch", "delete"}


def _operations(contrat: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    trouvees = []
    for chemin, entree in (contrat.get("paths") or {}).items():
        for verbe, operation in entree.items():
            if verbe in VERBES:
                trouvees.append((chemin, verbe, operation))
    return trouvees


def _compte_refs_hors_schemas(contrat: dict[str, Any]) -> int:
    """`$ref` pointant ailleurs que `components/schemas`, que le parser ne suit pas."""
    compte = 0
    pile: list[Any] = [contrat]
    while pile:
        noeud = pile.pop()
        if isinstance(noeud, dict):
            cible = noeud.get("$ref")
            if isinstance(cible, str) and not cible.startswith("#/components/schemas/"):
                compte += 1
            pile.extend(noeud.values())
        elif isinstance(noeud, list):
            pile.extend(noeud)
    return compte


def _compte_mot_clef(contrat: dict[str, Any], mots: set[str]) -> int:
    compte = 0
    pile: list[Any] = [contrat]
    while pile:
        noeud = pile.pop()
        if isinstance(noeud, dict):
            compte += sum(1 for mot in mots if mot in noeud)
            pile.extend(noeud.values())
        elif isinstance(noeud, list):
            pile.extend(noeud)
    return compte


def mesurer(produit: str, version: str) -> None:
    chemin = SPEC_ROOT / f"{produit}.{version}.yml"
    if not chemin.is_file():
        print(f"  {chemin.relative_to(ROOT)} absent", file=sys.stderr)
        return
    contrat = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    operations = _operations(contrat)

    parametres_de_chemin = sum(
        1 for _c, entree in (contrat.get("paths") or {}).items() if "parameters" in entree
    )
    reponses_201 = sum(1 for _c, _v, op in operations if "201" in (op.get("responses") or {}))
    reponses_204 = sum(1 for _c, _v, op in operations if "204" in (op.get("responses") or {}))
    sans_reponse_200 = sum(
        1 for _c, _v, op in operations if "200" not in (op.get("responses") or {})
    )
    styles = sum(
        1
        for _c, _v, op in operations
        for p in (op.get("parameters") or [])
        if isinstance(p, dict) and "style" in p
    )
    tailles = {"per_page": 0, "page_size": 0, "page": 0}
    for _c, _v, op in operations:
        for p in op.get("parameters") or []:
            if isinstance(p, dict) and p.get("name") in tailles:
                tailles[p["name"]] += 1

    print(f"\n=== {produit} {version} : {len(operations)} opérations")
    lignes = [
        ("paramètres au niveau du chemin", parametres_de_chemin, "non géré"),
        ("$ref hors components.schemas", _compte_refs_hors_schemas(contrat), "non géré"),
        (
            "allOf / oneOf / anyOf",
            _compte_mot_clef(contrat, {"allOf", "oneOf", "anyOf"}),
            "non géré",
        ),
        ("style de sérialisation", styles, "non géré"),
        ("réponses 201", reponses_201, "non lues"),
        ("réponses 204", reponses_204, "non lues"),
        ("opérations sans réponse 200", sans_reponse_200, "aucune réponse décrite"),
        ("pagination per_page", tailles["per_page"], "reconnue"),
        ("pagination page_size", tailles["page_size"], "reconnue"),
    ]
    for nom, combien, etat in lignes:
        marque = "  " if combien == 0 else "! "
        print(f"  {marque}{nom:34s} {combien:4d}   {etat}")


def main(argv: list[str]) -> int:
    if len(argv) == 3:
        mesurer(argv[1], argv[2])
        return 0

    index = SPEC_ROOT / "products.txt"
    for ligne in index.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        champs = ligne.split()
        produit = champs[1] if len(champs) == 3 else champs[0]
        mesurer(produit, champs[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
