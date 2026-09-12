"""Le journal des apparitions dit-il encore la vérité sur ce qui est publié ?

`version_added` est un fait historique : le générateur ne le déduit pas, il le
lit dans `generator/ansible/introductions.yml` (ADR-013). Un fichier qu'on tient
à la main peut se désynchroniser de deux façons, et ce contrôle regarde les
deux.

**La version en préparation peut être périmée.** Elle date tout ce que le
journal ne connaît pas encore. Si elle reste sur le numéro qui vient d'être
publié, ou si elle annonce un correctif alors que les fragments promettent une
mineure, le premier module neuf partira avec une date qui ne sortira jamais.

**Un nom peut n'être daté par personne.** Un module, une option ou une valeur de
retour qu'aucun bloc ne mentionne reçoit la version en préparation. Ce n'est pas
un défaut, c'est l'état normal d'un ajout ; c'est un défaut de ne pas le voir.

Ce que ce contrôle **refuse** est étroit, et c'est délibéré :

* la version en préparation n'est pas postérieure à celle que `galaxy.yml`
  porte. Une version a donc été publiée sans que le journal soit figé, et le
  prochain figeage écrirait deux fois la même date ;
* elle contredit ce que les fragments impliquent, **et** quelque chose attend
  d'être daté. Sans rien en attente, sa valeur ne publie rien et la signaler
  suffit.

Le reste est publié sans interdire : refuser un module non encore daté
bloquerait l'ajout d'un produit entre son écriture et sa publication, et une
porte qu'on ne peut pas franchir est une porte qu'on désactive.

    python scripts/introductions.py                    le contrôle
    python scripts/introductions.py --enregistrer X.Y.Z  fige, et prépare la suite

Codes de sortie : `0` conforme, `1` erreur, `2` refusé.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import version as version_module
import yaml

from generator.ansible.collection import load_collection
from generator.ansible.introductions import (
    DEFAULT_JOURNAL,
    Introductions,
    IntroductionsError,
    load_introductions,
)
from generator.ansible.models import build_module_specs
from generator.plan import build_plan
from generator.source.base import VendoredSpecSource

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs" / "scaleway"

EXIT_OK = 0
EXIT_ERREUR = 1
EXIT_REFUSE = 2


def _rang(version: str) -> tuple[int, ...]:
    """Ordonne deux numéros. Comparer des chaînes daterait `0.10.0` avant `0.9.0`."""
    return tuple(int(morceau) for morceau in version.split("."))


def noms_produits(journal: Introductions) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Ce que le générateur écrit aujourd'hui : les modules, et leurs membres.

    Le journal est passé au constructeur plutôt que laissé par défaut : sans
    lui, les dates seraient celles de la collection courante, et la comparaison
    se ferait contre ce qu'on cherche justement à corriger.
    """
    collection = load_collection()
    modules: list[str] = []
    membres: list[tuple[str, str, str]] = []
    for produit, api in VendoredSpecSource(root=SPECS).available():
        plan = build_plan(produit, api, spec_root=SPECS)
        specs, _ = build_module_specs(plan, collection, introductions=journal)
        for spec in specs:
            modules.append(spec.name)
            membres.extend(("option", spec.name, option.name) for option in spec.options)
            membres.extend(("retour", spec.name, valeur.name) for valeur in spec.returns)
    return sorted(modules), sorted(membres)


def non_dates(
    journal: Introductions, modules: list[str], membres: list[tuple[str, str, str]]
) -> list[str]:
    """Les noms qu'aucun bloc ne date, et qui portent donc `en_preparation`."""
    attente = [f"module {nom}" for nom in modules if nom not in journal.modules]
    for genre, module, nom in membres:
        table = journal.options if genre == "option" else journal.retours
        if (module, nom) not in table and module in journal.modules:
            attente.append(f"{genre} {module}.{nom}")
    return attente


def plus_ecrits(journal: Introductions, modules: list[str]) -> list[str]:
    """Les modules que le journal date et que le générateur n'écrit plus.

    **Publié, jamais refusé.** Un module retiré reste une chose que la
    collection a publiée, et sa date reste vraie : effacer son entrée effacerait
    l'histoire que ce fichier existe pour tenir.
    """
    return sorted(set(journal.modules) - set(modules))


def implique(collection_path: Path, version_publiee: str) -> tuple[str | None, str]:
    """Ce que les fragments en attente promettent comme prochain numéro."""
    sections = version_module.sections_en_attente(collection_path)
    echelon = version_module.portee(sections)
    if echelon is None:
        return None, "aucun fragment en attente : rien à confronter"
    attendu = version_module.suivante(version_publiee, echelon)
    return attendu, f"les fragments impliquent une version {echelon}, soit {attendu}"


def controler(journal: Introductions) -> tuple[bool, list[str]]:
    """Rend le verdict et les lignes à imprimer."""
    collection = load_collection()
    lignes: list[str] = []
    refus: list[str] = []

    lignes.append(f"version publiée (galaxy.yml) : {collection.version}")
    lignes.append(f"version en préparation        : {journal.en_preparation}")

    if _rang(journal.en_preparation) <= _rang(collection.version):
        refus.append(
            f"la version en préparation {journal.en_preparation} n'est pas postérieure à "
            f"la version publiée {collection.version} : une release est partie sans que "
            "le journal soit figé (`--enregistrer`)"
        )

    modules, membres = noms_produits(journal)
    attente = non_dates(journal, modules, membres)
    retires = plus_ecrits(journal, modules)

    attendu, phrase = implique(collection.path, collection.version)
    lignes.append(f"fragments                     : {phrase}")
    if attendu is not None and attendu != journal.en_preparation and attente:
        refus.append(
            f"la version en préparation {journal.en_preparation} contredit ce que les "
            f"fragments impliquent ({attendu}), et {len(attente)} nom(s) en dépendent : "
            "ils partiraient avec une date qui ne sortira pas"
        )

    lignes.append(f"modules écrits                : {len(modules)}")
    if attente:
        lignes.append(f"\nen attente de date, donc datés {journal.en_preparation} :")
        lignes.extend(f"  {nom}" for nom in attente)
    else:
        lignes.append("tout ce qui est écrit est daté par un bloc du journal.")
    if retires:
        lignes.append("\ndatés par le journal et plus écrits (l'histoire reste vraie) :")
        lignes.extend(f"  {nom}" for nom in retires)

    if refus:
        lignes.append("")
        lignes.extend(f"REFUSÉ : {motif}" for motif in refus)
    return not refus, lignes


def enregistrer(journal: Introductions, version: str, chemin: Path) -> list[str]:
    """Fige ce qui attend une date sous `version`, et prépare la suivante.

    Le fichier est réécrit **textuellement** : une réécriture par YAML perdrait
    l'en-tête, qui porte les raisons de sa forme. Le bloc s'ajoute à la fin, ce
    qui garde l'ordre croissant tant qu'on fige la version la plus récente.
    """
    modules, membres = noms_produits(journal)
    neufs = [nom for nom in modules if nom not in journal.modules]
    options: dict[str, list[str]] = {}
    retours: dict[str, list[str]] = {}
    for genre, module, nom in membres:
        # Les membres d'un module neuf ne se datent pas séparément : ils
        # héritent de la date de leur module, et les inscrire ferait publier un
        # badge identique sur chaque ligne de la page.
        if module not in journal.modules:
            continue
        deja = journal.options if genre == "option" else journal.retours
        if (module, nom) not in deja:
            (options if genre == "option" else retours).setdefault(module, []).append(nom)

    bloc = [f'\n  "{version}":']
    if neufs:
        bloc.append("    modules:")
        bloc.extend(f"      - {nom}" for nom in sorted(neufs))
    for cle, table in (("options", options), ("retours", retours)):
        if not table:
            continue
        bloc.append(f"    {cle}:")
        for module in sorted(table):
            bloc.append(f"      {module}:")
            bloc.extend(f"        - {nom}" for nom in sorted(table[module]))

    suivante = version_module.suivante(version, "correctif")
    texte = chemin.read_text(encoding="utf-8")
    texte, remplacements = re.subn(
        r'^en_preparation:\s*"?[^"\s]+"?$',
        f'en_preparation: "{suivante}"',
        texte,
        count=1,
        flags=re.M,
    )
    if remplacements != 1:
        raise IntroductionsError(f"{chemin} ne porte pas exactement une ligne `en_preparation:`")

    # **Le bloc se saute, l'avancement jamais.** Un cycle peut ne rien ajouter
    # que le journal date : la 0.6.0 était faite de playbooks, d'un plugin et de
    # documentation. Un bloc vide publierait un badge de version sur rien, mais
    # la release, elle, est bien partie, et le cycle suivant prépare la version
    # d'après. Sortir ici sans avancer laissait le contrôle refuser la release
    # qui venait de se faire, en accusant un figeage qui avait eu lieu.
    rien_a_dater = not neufs and not options and not retours
    contenu = texte.rstrip("\n") + "\n"
    if not rien_a_dater:
        contenu += "\n".join(bloc) + "\n"
    chemin.write_text(contenu, encoding="utf-8")

    # Relire prouve que le fichier écrit se charge encore : un bloc mal indenté
    # ne se verrait qu'à la génération suivante, c'est-à-dire trop tard.
    load_introductions(chemin)
    fige = (
        f"rien à figer : aucun nom n'attend de date sous {version}."
        if rien_a_dater
        else (
            f"{len(neufs)} module(s), {sum(map(len, options.values()))} option(s) et "
            f"{sum(map(len, retours.values()))} retour(s) figés sous {version}."
        )
    )
    return [
        fige,
        f"version en préparation portée à {suivante} ; la corriger si les "
        "fragments du cycle suivant impliquent autre chose.",
    ]


def main(argv: list[str]) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument(
        "--enregistrer",
        metavar="VERSION",
        help="figer sous ce numéro ce qui attend une date",
    )
    arguments = analyseur.parse_args(argv)

    try:
        journal = load_introductions()
        if arguments.enregistrer:
            for ligne in enregistrer(journal, arguments.enregistrer, DEFAULT_JOURNAL):
                print(ligne)
            return EXIT_OK
        conforme, lignes = controler(journal)
    except (IntroductionsError, version_module.VersionError, yaml.YAMLError) as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return EXIT_ERREUR

    print("\n".join(lignes))
    return EXIT_OK if conforme else EXIT_REFUSE


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
