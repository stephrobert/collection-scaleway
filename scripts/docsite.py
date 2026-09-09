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
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_specs import read_products

from generator.ansible.collection import load_collection
from generator.ir.enums import OperationKind
from generator.plan import build_plan

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
    """Les produits qui doivent avoir une page de mesure, lus dans l'index.

    Un produit marqué `suivi` n'en a pas : son contrat est versionné pour que
    sa dérive se voie, mais rien n'est généré à partir de lui, donc il n'y a ni
    rapport ni classification à publier.
    """
    return tuple(
        (entry.product, entry.version) for entry in read_products() if not entry.tracked_only
    )


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True)


#: Un lien Markdown dont la cible est un chemin relatif du dépôt.
#:
#: `http`, `#` et `mailto:` sont laissés tels quels : les premiers sortent déjà
#: du dépôt, le deuxième vise la page elle-même.
_LIEN_RELATIF = re.compile(r"\]\((?!https?://|#|mailto:)([^)]+)\)")


def _liens_absolus(texte: str) -> str:
    """Les liens relatifs du README, repointés vers le dépôt.

    Le README vit dans le dossier de la collection : `playbooks/README.md` y
    est juste, et ne l'est plus une fois la page servie ailleurs. Sphinx le dit
    en avertissement, et `-W` en fait un échec, ce qui est le comportement
    voulu : un lien mort sur une page publiée est un défaut.

    Ils partent vers GitHub plutôt que vers une page du site, parce que ce
    qu'ils désignent, `LICENSE` ou `changelogs/`, n'est pas publié ici. La
    référence est la version publiée, comme le reste des liens que le README
    écrit déjà en absolu.
    """
    base = (
        f"https://github.com/stephrobert/collection-scaleway/blob/"
        f"{COLLECTION.version}/{COLLECTION.path.relative_to(ROOT).as_posix()}/"
    )
    return _LIEN_RELATIF.sub(lambda trouve: f"]({base}{trouve.group(1)})", texte)


def _page_depuis_readme(source: Path, nom: str, titre: str, phrase: str) -> str:
    """Assemble une page du site depuis un README de la collection.

    **Assemblée, jamais versionnée.** Recopier ces textes dans `docs/` en
    ferait une seconde source, qui divergerait du README au premier
    changement, et c'est exactement ce que cet assemblage existe pour éviter.
    Le titre de premier niveau est remplacé : sur le site, une page s'appelle
    par ce qu'elle sert, pas par le nom du dossier qui la porte.
    """
    if not source.is_file():
        # `relative_to` lève quand le chemin sort de la racine, et un message
        # d'erreur qui lève ne dit plus rien : le nom suffit à s'y retrouver.
        nom_lisible = source.name if ROOT not in source.parents else source.relative_to(ROOT)
        raise SiteError(f"{nom_lisible} est absent : le site n'invente pas ce qu'il sert.")
    lignes = _liens_absolus(source.read_text(encoding="utf-8")).splitlines()
    corps = [ligne for ligne in lignes if not ligne.startswith("# ")]

    dossier = SITE_SRC / "guides"
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{nom}.md").write_text(
        f"# {titre}\n\n```{{note}}\n{phrase}\n```\n\n" + "\n".join(corps).lstrip("\n") + "\n",
        encoding="utf-8",
    )
    return f"guides/{nom}"


#: Ce que chaque classe d'opération donne comme module, dit en anglais parce
#: que cette page est publiée. L'ordre est celui de la lecture : on cherche
#: d'abord ce qu'on peut lire, puis ce qu'on peut changer, puis ce qu'on
#: déclenche.
_CLASSES: tuple[tuple[OperationKind, str], ...] = (
    (OperationKind.INFO, "read"),
    (OperationKind.MANAGE, "manage"),
    (OperationKind.ACTION, "trigger"),
)


def write_reference_page() -> str:
    """La référence, groupée par produit puis par ressource.

    **antsibull rend les modules à plat**, par ordre alphabétique. C'est déjà
    pénible à cinquante ; à cent cinquante ce serait inutilisable, et le nombre
    ne cesse pas de croître puisque personne ne suit l'API à la main (#164).

    Cette page ne remplace pas les pages générées, elle les ordonne : chaque
    entrée renvoie à celle qu'antsibull écrit, qui reste la référence. Elle est
    **générée depuis le plan**, donc depuis la décision du générateur lui-même :
    la ressource et la classe sont celles qui ont nommé le module, pas une
    seconde lecture de son nom qui divergerait le jour où la règle change.
    """
    lignes = [
        "# Module reference",
        "",
        "Every module the collection ships, grouped by product and by resource.",
        "Each entry links to its generated page, which stays the reference.",
        "",
    ]
    ecrits = set(expected_modules())
    for produit, version in expected_products():
        plan = build_plan(produit, version, spec_root=ROOT / "specs" / "scaleway")
        par_ressource: dict[str, dict[OperationKind, str]] = {}
        for nom, items in plan.modules().items():
            # Un module porte plusieurs opérations, `GetServer` et `ListServers`
            # par exemple, et toutes partagent sa ressource et sa classe : la
            # première suffit, et c'est le plan qui les a nommées.
            if nom not in ecrits or not items:
                continue
            par_ressource.setdefault(items[0].resource, {})[items[0].kind] = nom

        lignes.append(f"## {plan.service.title or produit}")
        lignes.append("")
        for ressource in sorted(par_ressource):
            lignes.append(f"### {ressource.replace('_', ' ')}")
            lignes.append("")
            for classe, verbe in _CLASSES:
                module = par_ressource[ressource].get(classe)
                if module is None:
                    continue
                lignes.append(
                    f"- {{ansplugin}}`{module} <stephrobert.scaleway.{module}#module>` -- {verbe}"
                )
            lignes.append("")

    (SITE_SRC / "guides").mkdir(parents=True, exist_ok=True)
    (SITE_SRC / "guides" / "module-reference.md").write_text(
        "\n".join(lignes) + "\n", encoding="utf-8"
    )
    return "guides/module-reference"


def write_usage_page() -> str:
    """La page d'usage, tirée du README que Galaxy publie.

    **Le parcours existait déjà, le site ne le servait pas.** Installation,
    authentification, « Sixty seconds », inventaire : le README de la collection
    les porte, et Galaxy les affiche. Le site ouvrait sur l'architecture du
    générateur, et sa section d'usage tenait en une page (#164).
    """
    return _page_depuis_readme(
        COLLECTION.path / "README.md",
        "using-the-collection",
        "Using the collection",
        "This page is the collection's README, the one Galaxy publishes. It is\n"
        "assembled here rather than copied, so the two cannot diverge.",
    )


def write_playbooks_page() -> str:
    """Les playbooks livrés, qui sont les pages de tâches de ce site.

    **Ils tournent.** `mise run integration` les joue contre un émulateur à
    chaque exécution de cette cible : ce sont des tâches éprouvées, pas des
    extraits qui illustrent. Écrire des pages de tâches à la main à côté ferait
    une seconde source, que rien n'exécuterait et qui pourrirait.
    """
    return _page_depuis_readme(
        COLLECTION.path / "playbooks" / "README.md",
        "shipped-playbooks",
        "Task playbooks",
        "These playbooks ship with the collection and are played by\n"
        "`mise run integration` on every run. This page is their README,\n"
        "assembled here rather than copied.",
    )


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
    write_usage_page()
    write_playbooks_page()
    write_reference_page()
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
