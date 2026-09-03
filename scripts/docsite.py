"""Assemble le site de documentation, puis le construit sous `-W`.

**Rien de ce que ce script produit n'entre dans le dépôt.** Les pages viennent
de trois sources, et elles sont refabriquées à chaque publication :

    docs/                        écrit à la main, versionné
    build/docs/collections/      antsibull-docs, depuis les modules générés
    build/reports/*.md           le rapport, depuis la représentation intermédiaire
              |
              v  build/site-src/     arborescence jetable
              |
              v  sphinx-build -W --keep-going
           build/site/

C'est ce qui rend la péremption impossible plutôt que surveillée : il n'existe
aucun état intermédiaire versionné qui puisse dériver. Versionner ces pages
pour les mettre sous `check:generated` n'aurait de sens que si quelqu'un
pouvait les éditer, et personne ne les édite.

`-W` transforme en échec la référence croisée morte, le module documenté qui
n'existe plus et la page hors toctree. Mais un site vide se construit aussi
très bien : ce script compte donc ce qu'il a assemblé, et refuse un vert obtenu
sur rien.

Le fichier ne s'appelle pas `site.py` : ce nom est celui d'un module de la
bibliothèque standard, importé au démarrage de tout interpréteur, et un module
de `scripts/` qui le porterait ne serait jamais celui qu'un `import site`
résout. Un fichier qu'aucun test ne peut importer est un fichier qu'aucun test
ne garde.

    python scripts/docsite.py
    python scripts/docsite.py --linkcheck    # liens externes, demande le réseau
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_specs import read_products

from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BUILD = ROOT / "build"
ANTSIBULL = BUILD / "docs" / "collections"
REPORTS = BUILD / "reports"
SITE_SRC = BUILD / "site-src"
SITE = BUILD / "site"
#: **Dérivés de `galaxy.yml`, et non écrits segment par segment.** Ces deux
#: chemins nommaient `local` et `scaleway` en morceaux, donc un renommage de
#: namespace ne pouvait pas les voir : aucune recherche de `local/scaleway` ne
#: trouve un chemin découpé. Le symptôme sortait trois couches plus loin, dans
#: le harnais de falsification.
COLLECTION = load_collection()
MODULES = COLLECTION.path / "plugins" / "modules"

#: Les sous-paquets du générateur, dans l'ordre du pipeline, avec ce qu'ils
#: font. La liste est écrite ici parce qu'elle porte un ordre et une intention
#: qu'aucune découverte de répertoire ne saurait deviner ; un paquet qui
#: disparaît fait échouer la construction, ce qui est le contrôle voulu.
GENERATOR_PACKAGES: tuple[tuple[str, str], ...] = (
    ("generator.source", "Lecture des contrats versionnés. Jamais le réseau."),
    ("generator.parser", "OpenAPI vers représentation intermédiaire. Traduit, ne décide rien."),
    ("generator.ir", "Les dataclasses gelées, et leur sérialisation déterministe."),
    ("generator.classifier", "Six règles mécaniques. Ce qui reste est UNKNOWN."),
    ("generator.overrides", "Les décisions humaines, chacune avec sa raison."),
    ("generator.ansible", "Noms de modules, types d'argument_spec, modèle du module."),
    ("generator.renderer", "Jinja2, rendu seul."),
    ("generator.report", "Texte, JSON, Markdown."),
)


class SiteError(RuntimeError):
    """Le site ne peut pas être assemblé, et il faut le dire au lieu de sauter."""


def expected_modules() -> tuple[str, ...]:
    """Les modules qui doivent avoir une page, lus là où ils sont écrits."""
    return tuple(sorted(p.stem for p in MODULES.glob("*.py") if p.stem != "__init__"))


def _pourcent(valeur: float | None) -> str:
    """Un ratio absent est `n/a`, jamais `0,0 %` : indéfini n'est pas nul."""
    if valeur is None:
        return "n/a"
    return f"{valeur * 100:.1f} %".replace(".", ",", 1)


def expected_products() -> tuple[tuple[str, str], ...]:
    """Les produits qui doivent avoir une page de mesure, lus dans l'index."""
    return tuple((produit, version) for _slug, produit, version in read_products())


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True)


def write_measure_pages() -> tuple[str, ...]:
    """La section « Mesure » : une page par produit, plus son index.

    Elle ne s'écrit pas à la main. La classification opération par opération
    avec sa raison, la couverture avec son dénominateur nommé et les limites
    du contrat viennent de la représentation intermédiaire, donc du même
    contrat versionné que la CI juge.
    """
    dossier = SITE_SRC / "mesure"
    dossier.mkdir(parents=True, exist_ok=True)
    lignes: list[str] = []
    ecrites: list[str] = []

    for produit, version in expected_products():
        base = f"{produit}.{version}"
        markdown = REPORTS / f"{base}.md"
        donnees = REPORTS / f"{base}.json"
        if not markdown.is_file() or not donnees.is_file():
            raise SiteError(
                f"le rapport de {base} manque dans {REPORTS.relative_to(ROOT)}. "
                "Lancer `mise run report` avant, ou retirer le produit de "
                "specs/scaleway/products.txt s'il n'est plus suivi."
            )

        generation = REPORTS / f"{base}.generation.md"
        if not generation.is_file():
            raise SiteError(
                f"le compte rendu de génération de {base} manque : lancer "
                "`mise run generate`. C'est lui qui dit pourquoi tel module n'existe pas."
            )

        rapport = json.loads(donnees.read_text(encoding="utf-8"))
        totaux = rapport["totals"]
        couverture = rapport.get("day2_automation_coverage")
        lignes.append(
            f"| [{produit} {version}]({base}.md) | {totaux['operations']} | "
            f"{totaux['day2_candidates']} | {totaux['by_mode']['auto']} | "
            f"{totaux['by_mode']['manual']} | "
            f"{_pourcent(couverture)} |"
        )

        entete = (
            f"<!-- Page dérivée : produite par scripts/docsite.py depuis "
            f"build/reports/{base}.md. Ne pas éditer. -->\n\n"
        )
        (dossier / f"{base}.md").write_text(
            entete + markdown.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (dossier / f"{base}.generation.md").write_text(
            entete + generation.read_text(encoding="utf-8"), encoding="utf-8"
        )
        ecrites.append(base)

    index = [
        "# Mesure",
        "",
        "Ce que le générateur trouve dans les contrats, produit par produit.",
        "Ces pages sont **dérivées** de la représentation intermédiaire : elles",
        "ne s'écrivent pas à la main, et elles changent le jour où l'API change.",
        "",
        "```{warning}",
        "La couverture Day-2 se lit avec son dénominateur, et cette colonne",
        "compte les opérations **classées** pour la génération automatique.",
        "LIFECYCLE et IGNORE n'y sont pas, parce que ce n'est pas du travail",
        "automatisé mais du travail écarté.",
        "",
        "Classée n'est pas portée par un module : la classification autorise la",
        "génération, elle ne la produit pas. Le compte rendu de génération de",
        "chaque produit publie les deux ratios côte à côte, et l'écart s'y lit",
        "module par module, chacun avec sa raison.",
        "```",
        "",
        "| produit | opérations | candidates Day-2 | AUTO | MANUAL | classées |",
        "|---|---|---|---|---|---|",
        *lignes,
        "",
        "Chaque produit porte aussi un **compte rendu de génération** : ce qui a",
        "été écrit, ce qui a été écarté avec sa raison, et ce que le contrat n'a",
        "pas su dire. C'est là que se lit pourquoi tel module n'existe pas.",
        "",
        "```{toctree}",
        ":hidden:",
        "",
        *[ligne for base in ecrites for ligne in (base, f"{base}.generation")],
        "```",
        "",
    ]
    (dossier / "index.md").write_text("\n".join(index), encoding="utf-8")
    return tuple(ecrites)


def write_api_pages() -> tuple[str, ...]:
    """La section « Le générateur » : les docstrings, rendues telles quelles.

    Les docstrings de ce dépôt sont en français et denses ; elles portent les
    raisons des décisions. Les recopier dans une page écrite à la main créerait
    une seconde source qui divergerait.
    """
    dossier = SITE_SRC / "api"
    dossier.mkdir(parents=True, exist_ok=True)
    ecrites: list[str] = []

    for paquet, resume in GENERATOR_PACKAGES:
        nom = paquet.replace(".", "-")
        contenu = [
            f"# `{paquet}`",
            "",
            resume,
            "",
            "```{eval-rst}",
            f".. automodule:: {paquet}",
            "   :members:",
            "```",
            "",
        ]
        (dossier / f"{nom}.md").write_text("\n".join(contenu), encoding="utf-8")
        ecrites.append(nom)

    index = [
        "# Le générateur",
        "",
        "Le producteur, sous-paquet par sous-paquet, dans l'ordre du pipeline.",
        "Les textes sont les docstrings du code : il n'existe pas de seconde",
        "source qui pourrait en diverger.",
        "",
        *[
            f"- [`{paquet}`]({paquet.replace('.', '-')}.md) : {resume}"
            for paquet, resume in GENERATOR_PACKAGES
        ],
        "",
        "```{toctree}",
        ":hidden:",
        "",
        *ecrites,
        "```",
        "",
    ]
    (dossier / "index.md").write_text("\n".join(index), encoding="utf-8")
    return tuple(ecrites)


def assemble() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Construit `build/site-src/`, et rend ce qui a été assemblé."""
    if not (ANTSIBULL / "index.rst").is_file():
        raise SiteError(
            f"{ANTSIBULL.relative_to(ROOT)} est absent : lancer `mise run docs` avant. "
            "Le site n'invente pas les pages de la collection."
        )

    shutil.rmtree(SITE_SRC, ignore_errors=True)
    SITE_SRC.mkdir(parents=True)

    copy_tree(DOCS, SITE_SRC)
    copy_tree(ANTSIBULL, SITE_SRC / "collections")
    produits = write_measure_pages()
    paquets = write_api_pages()
    return produits, paquets


def check_population(produits: tuple[str, ...], paquets: tuple[str, ...]) -> None:
    """Refuse un site vert obtenu sur rien.

    Sphinx construit très bien un site sans page. Ce contrôle compare ce qui
    est là à ce que le dépôt contient : chaque module de `plugins/modules/`
    doit avoir sa page, chaque produit de `products.txt` sa mesure, chaque
    sous-paquet du générateur sa page d'API.
    """
    reference = SITE_SRC / "collections" / COLLECTION.namespace / COLLECTION.name
    modules = expected_modules()
    if not modules:
        raise SiteError("aucun module dans plugins/modules/ : le site n'aurait rien à documenter")

    manquants = [nom for nom in modules if not (reference / f"{nom}_module.rst").is_file()]
    if manquants:
        raise SiteError(
            f"{len(manquants)} module(s) sans page antsibull, dont {manquants[:3]} : "
            "la documentation ne couvre pas ce que la collection livre"
        )

    if not produits:
        raise SiteError("aucune page de mesure : specs/scaleway/products.txt est-il vide ?")
    if len(paquets) != len(GENERATOR_PACKAGES):
        raise SiteError("les pages d'API ne couvrent pas tous les sous-paquets déclarés")

    print(
        f"assemblé : {len(modules)} module(s) documenté(s), {len(produits)} produit(s) "
        f"mesuré(s), {len(paquets)} sous-paquet(s) du générateur"
    )


def build(builder: str) -> int:
    """Construit, en refusant le moindre avertissement.

    `-W` est ce qui fait de cette commande une porte : une référence croisée
    morte, un module documenté qui n'existe plus ou une page hors toctree sont
    des avertissements, donc des échecs. `--keep-going` les montre tous d'un
    coup plutôt qu'un par exécution.
    """
    commande = [
        str(Path(sys.executable).parent / "sphinx-build"),
        "-M",
        builder,
        str(SITE_SRC),
        str(SITE),
        "-W",
        "--keep-going",
        "-q",
    ]
    return subprocess.run(commande, check=False).returncode


def main(argv: list[str]) -> int:
    builder = "linkcheck" if "--linkcheck" in argv[1:] else "html"
    produits, paquets = assemble()
    check_population(produits, paquets)

    code = build(builder)
    if code != 0:
        return code

    if builder == "html":
        pages = len(list((SITE / "html").rglob("*.html")))
        print(f"{pages} page(s) dans {SITE.relative_to(ROOT)}/html")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except SiteError as error:
        print(f"erreur : {error}", file=sys.stderr)
        raise SystemExit(1) from error
