"""Mesure ce que la documentation publiée vaut, et refuse ce qui n'est pas publiable.

**Le générateur industrialise le code ; rien n'industrialisait la documentation
qu'il produit.** `ansible-test sanity` dit qu'un bloc est bien formé, pas qu'il
apprend quelque chose à quelqu'un. Une relecture des cinquante modules a trouvé
des pages où l'utilisateur lit « Not documented by the Scaleway API contract »,
des exemples remplis de `<zone>`, et un module d'action dont le retour annonce
trois actions que ce même module refuse.

Le critère, et il est plus exigeant que la syntaxe :

    Chaque module publié doit pouvoir être compris et utilisé depuis sa seule
    page Galaxy, sans lire le contrat OpenAPI ni le code source.

    python scripts/docs_quality.py            la mesure, par défaut
    python scripts/docs_quality.py --check    échoue sur un défaut bloquant
    python scripts/docs_quality.py --json     pour un script

**Ce que ce contrôle n'est pas.** Il ne juge pas le style. Il cherche des
défauts nommés, chacun trouvé sur un module réel, et chacun réparable dans le
générateur plutôt que dans le fichier produit. Un défaut qui ne se répare qu'à
la main n'a rien à faire ici : il retomberait au produit suivant.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]

#: Le texte que le générateur pose quand le contrat ne décrit rien. Utile dans
#: un rapport interne, illisible sur une page Galaxy.
REPLI = "Not documented by the Scaleway API contract."

#: Un exemple dont les valeurs sont des chevrons ne se copie pas : il montre la
#: forme et cache ce qu'on doit y mettre.
PLACEHOLDER = re.compile(r"<[a-z_]+>")

# **Les trois derniers défauts sont devenus bloquants le jour où ils sont passés
# à zéro.** Tant qu'un défaut existe, le déclarer bloquant ferme la publication
# sans rien réparer ; une fois corrigé, le laisser passant garantit qu'il
# reviendra sans qu'on s'en aperçoive. Le coût d'un faux positif est un refus
# lisible qui nomme le module et la phrase ; le coût d'un faux négatif est une
# page publiée pour toujours.

#: Un nom d'exemple qui reprend l'identifiant du contrat. `GetDashboard` est un
#: nom interne : personne ne le tape, et personne ne devrait avoir à le lire.
NOM_DOPERATION = re.compile(r"\bRun [A-Z][A-Za-z]+\b")

#: Le vocabulaire du contrat, et ce qu'un lecteur attend à la place.
JARGON: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bScaleway Lb\b"), "Scaleway Load Balancer"),
    (re.compile(r"Load Balancer load balancer", re.I), "Load Balancer"),
    (re.compile(r"\bLb (acl|ip|route|backend|frontend|certificate|subscriber)\b"), "Load Balancer"),
)

#: Ce que la couche HTTP dit et que l'abstraction Ansible rend faux. Le contrat
#: du Load Balancer écrit « You must set all parameters » ; le module lit la
#: ressource et complète, donc l'utilisateur n'a justement pas à le faire.
FUITES_HTTP: tuple[str, ...] = (
    "You must set all parameters",
    "the request type is PUT and not PATCH",
)


class QualiteError(RuntimeError):
    """Une source manque, et un chiffre faux serait pire qu'une erreur."""


@dataclass
class Defaut:
    """Un défaut nommé, sur un module nommé, avec ce qu'il faut corriger."""

    module: str
    genre: str
    detail: str
    bloquant: bool


@dataclass
class Mesure:
    """Ce que la documentation publiée vaut, en nombres."""

    modules: int = 0
    options: int = 0
    options_decrites: int = 0
    retours: int = 0
    retours_decrits: int = 0
    #: Clés de retour `dict` ou `list`, les seules qui puissent porter des
    #: champs, et celles qui les portent vraiment.
    retours_composites: int = 0
    retours_detailles: int = 0
    #: Les clés composites qui n'ont pas de champs, nommées une par une. Le
    #: contrat ne déclare pas de schéma pour elles : c'est une limite en amont,
    #: pas un défaut du générateur, et un ratio dont on ignore ce que le reste
    #: contient ne dit rien à personne.
    sans_detail: list[str] = field(default_factory=list)
    exemples: int = 0
    exemples_copiables: int = 0
    defauts: list[Defaut] = field(default_factory=list)

    def ratio(self, numerateur: int, denominateur: int) -> str:
        """Un ratio sans dénominateur est indéfini, pas nul."""
        if denominateur == 0:
            return "n/a"
        return f"{numerateur / denominateur * 100:.1f}%"


def _bloc(source: str, nom: str) -> Any:
    motif = re.compile(rf'^{nom} = r?"""(.*?)"""', re.S | re.M)
    trouve = motif.search(source)
    if not trouve:
        return None
    try:
        return yaml.safe_load(trouve.group(1))
    except yaml.YAMLError:
        return None


def _texte(source: str, nom: str) -> str:
    motif = re.compile(rf'^{nom} = r?"""(.*?)"""', re.S | re.M)
    trouve = motif.search(source)
    return trouve.group(1) if trouve else ""


def _descriptions(noeud: Any) -> list[list[str]]:
    """Toutes les `description` d'un arbre de documentation, y compris imbriquées."""
    trouve: list[list[str]] = []
    if isinstance(noeud, dict):
        for cle, valeur in noeud.items():
            if cle == "description":
                if isinstance(valeur, str):
                    trouve.append([valeur])
                elif isinstance(valeur, list):
                    trouve.append([str(x) for x in valeur])
                else:
                    trouve.append([])
            else:
                trouve.extend(_descriptions(valeur))
    elif isinstance(noeud, list):
        for element in noeud:
            trouve.extend(_descriptions(element))
    return trouve


def examiner(chemin: Path, choix_exposes: dict[str, set[str]]) -> tuple[Mesure, list[Defaut]]:
    """Mesure un module, et nomme ses défauts."""
    nom = chemin.stem
    source = chemin.read_text(encoding="utf-8")
    mesure = Mesure(modules=1)
    defauts: list[Defaut] = []

    doc = _bloc(source, "DOCUMENTATION") or {}
    retour = _bloc(source, "RETURN") or {}
    exemples = _bloc(source, "EXAMPLES") or []
    texte_publie = "\n".join(_texte(source, n) for n in ("DOCUMENTATION", "EXAMPLES", "RETURN"))

    # --- ce que le module dit de lui-même ---------------------------------
    if not doc.get("description"):
        defauts.append(
            Defaut(nom, "description-absente", "le module ne dit pas ce qu'il fait", True)
        )

    # --- les options publiques --------------------------------------------
    for option, corps in (doc.get("options") or {}).items():
        mesure.options += 1
        description = (corps or {}).get("description") or []
        if description and REPLI not in " ".join(str(x) for x in description):
            mesure.options_decrites += 1
        else:
            defauts.append(Defaut(nom, "option-sans-description", f"option `{option}`", True))

    # --- les clés de retour ------------------------------------------------
    for cle, corps in (retour or {}).items():
        mesure.retours += 1
        description = (corps or {}).get("description") or []
        if description and REPLI not in " ".join(str(x) for x in description):
            mesure.retours_decrits += 1
        else:
            defauts.append(Defaut(nom, "retour-sans-description", f"clé `{cle}`", True))

        # **Nommer la clé ne dit pas ce qu'on y trouve.** Un `contains` liste
        # les champs de la ressource, et sans lui il faut appeler le module pour
        # apprendre ce qu'il rend. Le dénominateur ne compte que les clés `dict`
        # et `list` : une clé `str` n'a rien à contenir, et l'y ranger ferait un
        # ratio qui reproche au module d'être correct.
        if (corps or {}).get("type") in ("dict", "list"):
            mesure.retours_composites += 1
            if (corps or {}).get("contains"):
                mesure.retours_detailles += 1
            else:
                mesure.sans_detail.append(f"{nom}.{cle}")

    # --- les exemples -------------------------------------------------------
    for tache in exemples if isinstance(exemples, list) else []:
        if not isinstance(tache, dict):
            continue
        mesure.exemples += 1
        rendu = yaml.safe_dump(tache, allow_unicode=True)
        if PLACEHOLDER.search(rendu):
            defauts.append(
                Defaut(nom, "exemple-non-copiable", f"« {tache.get('name', '?')} »", True)
            )
        else:
            mesure.exemples_copiables += 1
        if NOM_DOPERATION.search(str(tache.get("name", ""))):
            defauts.append(
                Defaut(nom, "exemple-nomme-par-le-contrat", str(tache.get("name")), True)
            )

    # --- une valeur d'enum que le module refuse, citée ailleurs -------------
    exposes = choix_exposes.get(nom)
    if exposes is not None:
        for valeur in sorted(_valeurs_du_contrat(texte_publie) - exposes):
            defauts.append(
                Defaut(
                    nom,
                    "action-exclue-documentee",
                    f"`{valeur}` est décrite alors que le module la refuse",
                    True,
                )
            )

    # --- le vocabulaire du contrat -----------------------------------------
    for motif, attendu in JARGON:
        if motif.search(texte_publie):
            defauts.append(Defaut(nom, "vocabulaire-du-contrat", f"attendu : {attendu}", True))

    # --- ce que la couche HTTP dit et que le module rend faux ---------------
    for phrase in FUITES_HTTP:
        if phrase.lower() in texte_publie.lower():
            defauts.append(Defaut(nom, "fuite-de-la-couche-http", f"« {phrase} »", True))

    return mesure, defauts


def _valeurs_du_contrat(texte: str) -> set[str]:
    """Les valeurs d'enum que le texte publié cite sous la forme `` `valeur` ``.

    Le contrat décrit ses actions en puces `` * `poweron`: ... ``. Une valeur
    citée là et absente des `choices` est une action que le module refuse et que
    la documentation promet quand même.
    """
    return set(re.findall(r"\* `([a-z0-9_]+)`\s*:", texte))


def choix_par_module(modules_dir: Path) -> dict[str, set[str]]:
    """Ce que chaque module accepte vraiment, lu dans son `argument_spec`."""
    trouve: dict[str, set[str]] = {}
    for chemin in sorted(modules_dir.glob("*.py")):
        if chemin.stem.startswith("_"):
            continue
        source = chemin.read_text(encoding="utf-8")
        doc = _bloc(source, "DOCUMENTATION") or {}
        for corps in (doc.get("options") or {}).values():
            choix = (corps or {}).get("choices")
            if choix:
                trouve.setdefault(chemin.stem, set()).update(str(x) for x in choix)
    return trouve


def mesurer() -> tuple[Mesure, list[Defaut]]:
    collection = load_collection()
    modules_dir = collection.path / "plugins" / "modules"
    if not modules_dir.is_dir():
        raise QualiteError(f"{modules_dir} n'existe pas : lancer `mise run generate`.")

    exposes = choix_par_module(modules_dir)
    total = Mesure()
    tous: list[Defaut] = []
    for chemin in sorted(modules_dir.glob("*.py")):
        if chemin.stem.startswith("_"):
            continue
        mesure, defauts = examiner(chemin, exposes)
        total.modules += mesure.modules
        total.options += mesure.options
        total.options_decrites += mesure.options_decrites
        total.retours += mesure.retours
        total.retours_decrits += mesure.retours_decrits
        total.retours_composites += mesure.retours_composites
        total.retours_detailles += mesure.retours_detailles
        total.sans_detail.extend(mesure.sans_detail)
        total.exemples += mesure.exemples
        total.exemples_copiables += mesure.exemples_copiables
        tous.extend(defauts)
    if total.modules == 0:
        raise QualiteError("aucun module examiné : une mesure vide passerait pour un vert.")
    return total, tous


def rendre(mesure: Mesure, defauts: list[Defaut]) -> str:
    bloquants = [d for d in defauts if d.bloquant]
    lignes = [
        f"{mesure.modules} modules publiés",
        f"  options décrites   {mesure.options_decrites:4d} / {mesure.options:<4d} "
        f"{mesure.ratio(mesure.options_decrites, mesure.options)}",
        f"  retours décrits    {mesure.retours_decrits:4d} / {mesure.retours:<4d} "
        f"{mesure.ratio(mesure.retours_decrits, mesure.retours)}",
        f"  retours détaillés  {mesure.retours_detailles:4d} / {mesure.retours_composites:<4d} "
        f"{mesure.ratio(mesure.retours_detailles, mesure.retours_composites)}"
        + (
            f"   (sans schéma au contrat : {', '.join(sorted(mesure.sans_detail))})"
            if mesure.sans_detail
            else ""
        ),
        f"  exemples copiables {mesure.exemples_copiables:4d} / {mesure.exemples:<4d} "
        f"{mesure.ratio(mesure.exemples_copiables, mesure.exemples)}",
        "",
        f"  {len(bloquants)} défaut(s) bloquant(s), {len(defauts) - len(bloquants)} à corriger",
    ]
    par_genre: dict[str, list[Defaut]] = {}
    for defaut in defauts:
        par_genre.setdefault(defaut.genre, []).append(defaut)
    for genre, liste in sorted(par_genre.items(), key=lambda x: (-len(x[1]), x[0])):
        marque = "bloquant" if liste[0].bloquant else "        "
        modules = sorted({d.module for d in liste})
        lignes.append(
            f"  {marque}  {genre:32s} {len(liste):3d}  {', '.join(modules[:3])}"
            + (" ..." if len(modules) > 3 else "")
        )
    return "\n".join(lignes) + "\n"


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--check", action="store_true", help="échouer sur un défaut bloquant")
    parseur.add_argument("--json", action="store_true", help="sortir la mesure en JSON")
    arguments = parseur.parse_args(argv[1:])

    try:
        mesure, defauts = mesurer()
    except QualiteError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return 1

    if arguments.json:
        print(
            json.dumps(
                {
                    "modules": mesure.modules,
                    "options": [mesure.options_decrites, mesure.options],
                    "retours": [mesure.retours_decrits, mesure.retours],
                    "retours_detailles": [
                        mesure.retours_detailles,
                        mesure.retours_composites,
                    ],
                    "exemples": [mesure.exemples_copiables, mesure.exemples],
                    "defauts": [vars(d) for d in defauts],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print(rendre(mesure, defauts))

    if arguments.check:
        bloquants = [d for d in defauts if d.bloquant]
        if bloquants:
            print(
                f"{len(bloquants)} défaut(s) bloquant(s) : cette documentation n'est pas\n"
                "publiable. Un lecteur de Galaxy doit comprendre le module depuis sa\n"
                "seule page, sans lire le contrat ni le code.\n"
                "Chacun se répare dans le générateur, jamais dans le fichier produit.",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
