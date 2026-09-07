"""Ce que le parser ne couvre pas, mesuré sur chaque contrat versionné.

**À passer sur le contrat d'un produit avant de l'importer.** Le parser ne
couvre pas tout OpenAPI, et c'est délibéré : généraliser sans cas déclenchant
produit du code que rien ne juge. La liste des travaux se déduit donc de ce que
ce script trouve, et chaque ajout a son cas.

Le second produit a prouvé que ça marche. Sur Instance, sept des huit
constructions n'apparaissaient jamais et la huitième, `page_size`, valait zéro.
Le Load Balancer l'emploie, et onze de ses listes rendaient leur première page
en silence faute d'être reconnues comme paginées.

**Ce qui est traduit n'est pas « non géré », et le rapport doit le dire.** Une
preuve pessimiste est fausse au même titre qu'une preuve optimiste : elle fait
payer un prix qui n'existe pas, et elle masque celui qui existe. `oneOf` se
compte donc en deux lignes, selon ce que le parser en fait (ADR-008) : la forme
`[T, null]` est traduite avec sa nullabilité, l'union de formes est signalée et
ne l'est pas. `x-one-of` est traduit en `mutually_exclusive`, et compté comme
tel.

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

from generator.source.base import VendoredSpecSource

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


def _formes_de_oneof(contrat: dict[str, Any]) -> tuple[int, int]:
    """Les `oneOf` du contrat, séparés selon ce que le parser en fait.

    **Le critère est celui du parser, et c'est ce qui rend le compte vrai.**
    Une seule branche non nulle est un type optionnel : le parser en tire le
    type utile et porte la nullabilité (ADR-008). Tout autre nombre de branches
    est une union de formes, que le parser signale par un avertissement et ne
    traduit pas. Compter les deux sous une même ligne « non géré » sous-décrivait
    le parser : la porte d'admission faisait payer un prix qui n'existait pas.

    Une branche qui n'est pas un dictionnaire n'est pas une branche utile, comme
    dans le parser : un compte qui s'en écarterait mesurerait autre chose que le
    parseur, et les deux divergeraient au premier contrat malformé.
    """
    optionnels = 0
    unions = 0
    pile: list[Any] = [contrat]
    while pile:
        noeud = pile.pop()
        if isinstance(noeud, dict):
            branches = noeud.get("oneOf")
            if isinstance(branches, list):
                utiles = [
                    branche
                    for branche in branches
                    if isinstance(branche, dict) and branche.get("type") != "null"
                ]
                if len(utiles) == 1:
                    optionnels += 1
                else:
                    unions += 1
            pile.extend(noeud.values())
        elif isinstance(noeud, list):
            pile.extend(noeud)
    return optionnels, unions


def relever(
    produit: str, version: str, racine: Path = SPEC_ROOT
) -> tuple[int, list[tuple[str, int, str]]]:
    """Les constructions OpenAPI d'un contrat, comptées et qualifiées.

    **Mesurer et imprimer sont deux choses.** La fonction imprimait, et la
    porte d'admission a besoin des nombres : les lui faire relire dans une
    sortie texte ferait un second lecteur du même calcul, et les deux
    divergeraient au premier changement de mise en forme.
    """
    chemin = racine / f"{produit}.{version}.yml"
    if not chemin.is_file():
        raise FileNotFoundError(f"{chemin.relative_to(ROOT)} absent")
    return compter(yaml.safe_load(chemin.read_text(encoding="utf-8")))


def compter(contrat: dict[str, Any]) -> tuple[int, list[tuple[str, int, str]]]:
    """Les constructions d'un document déjà lu, comptées et qualifiées.

    Séparé de la lecture du fichier pour qu'un test puisse construire le
    document qui déclenche une ligne, plutôt que d'attendre qu'un contrat
    versionné l'emploie.
    """
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

    oneof_optionnels, oneof_unions = _formes_de_oneof(contrat)
    lignes = [
        ("paramètres au niveau du chemin", parametres_de_chemin, "non géré"),
        ("$ref hors components.schemas", _compte_refs_hors_schemas(contrat), "non géré"),
        ("allOf", _compte_mot_clef(contrat, {"allOf"}), "non géré"),
        ("oneOf [T, null]", oneof_optionnels, "traduit, nullabilité portée"),
        ("oneOf union réelle", oneof_unions, "non géré, signalé par le parser"),
        ("anyOf", _compte_mot_clef(contrat, {"anyOf"}), "non géré"),
        ("x-one-of", _compte_mot_clef(contrat, {"x-one-of"}), "traduit en mutually_exclusive"),
        ("style de sérialisation", styles, "non géré"),
        ("réponses 201", reponses_201, "non lues"),
        ("réponses 204", reponses_204, "non lues"),
        ("opérations sans réponse 200", sans_reponse_200, "aucune réponse décrite"),
        ("pagination per_page", tailles["per_page"], "reconnue"),
        ("pagination page_size", tailles["page_size"], "reconnue"),
    ]
    return len(operations), lignes


def mesurer(produit: str, version: str) -> None:
    """La même mesure, imprimée."""
    try:
        combien_doperations, lignes = relever(produit, version)
    except FileNotFoundError as absent:
        print(f"  {absent}", file=sys.stderr)
        return

    print(f"\n=== {produit} {version} : {combien_doperations} opérations")
    for nom, combien, etat in lignes:
        marque = "  " if combien == 0 else "! "
        print(f"  {marque}{nom:34s} {combien:4d}   {etat}")


def main(argv: list[str]) -> int:
    if len(argv) == 3:
        mesurer(argv[1], argv[2])
        return 0

    # **Les contrats générés, lus par la même source que le rapport.** Ce
    # script relisait `products.txt` à la main, et lisait `ipam v1 suivi`
    # comme `<slug> <produit> <version>` : il cherchait `v1.suivi.yml`, le
    # disait absent sur la sortie d'erreur, et sortait en 0. Un contrat suivi
    # n'est pas mesuré, parce qu'aucun module ne le porte ; un contrat généré
    # qui manquerait doit se voir, pas se confondre avec ce bruit.
    for produit, version in VendoredSpecSource(root=SPEC_ROOT).available():
        mesurer(produit, version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
