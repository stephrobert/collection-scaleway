"""Les nombres publiés dans le README, dérivés plutôt que recopiés.

Le README annonçait 366 tests unitaires et 46 mutations. Mesuré au même
instant : 420 tests et 73 mutations. Le message d'un commit annonçait 373 pour
376. Trois occurrences du même défaut, et il n'a rien d'anecdotique dans un
dépôt dont la thèse est qu'on mesure au lieu de supposer : **un nombre recopié
à la main vieillit en silence, et se lit exactement comme une mesure.**

Ce script produit le bloc entre les deux marqueurs du README depuis les
sources qui font foi. Deux modes, et la CI se sert du second :

    python scripts/readme_counters.py --write    réécrit le bloc
    python scripts/readme_counters.py --check    échoue si le bloc a vieilli

Ce qui n'est pas mesurable hors ligne n'entre pas dans le bloc. Le compte de
`ansible-test sanity` et celui des serveurs listés contre l'émulateur
demandent chacun de lancer autre chose ; les recopier ici les remettrait
exactement dans l'état qu'on corrige. Ils sont dits sans nombre, et le lecteur
qui veut le nombre lance la commande nommée.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from example_coverage import mesurer as mesurer_exemple

from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
#: Le README que `galaxy.yml` désigne, donc celui que Galaxy publiera.
README_COLLECTION = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "README.md"
RAPPORTS = ROOT / "build" / "reports"
MUTATIONS = ROOT / "tests" / "falsify" / "specs.json"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

DEBUT = "<!-- compteurs:début, produits par scripts/readme_counters.py -->"
FIN = "<!-- compteurs:fin -->"


class CompteursError(RuntimeError):
    """Une source manque, et il vaut mieux le dire que publier un nombre faux."""


def _affichable(chemin: Path) -> str:
    """Un chemin lisible, même hors du dépôt.

    `relative_to` lève quand le chemin est ailleurs, et un message d'erreur qui
    plante en se composant cache l'erreur qu'il devait annoncer. Le cas est
    arrivé sur un test qui déplace le répertoire des rapports.
    """
    try:
        return str(chemin.relative_to(ROOT))
    except ValueError:
        return str(chemin)


def _rapport(produit: str, version: str) -> dict[str, Any]:
    chemin = RAPPORTS / f"{produit}.{version}.json"
    if not chemin.is_file():
        raise CompteursError(
            f"{_affichable(chemin)} manque : lancer `mise run report` avant. "
            "Un compteur sans sa source n'est pas un compteur."
        )
    donnees: dict[str, Any] = json.loads(chemin.read_text(encoding="utf-8"))
    return donnees


def _modules_ecrits() -> tuple[int, int]:
    """Modules écrits et modules du plan, sommés sur **tous** les produits.

    **Ce compteur n'a longtemps lu qu'`instance.v1`**, et annonçait donc « 25
    modules produits sur 30 au plan » sous une liste de 46 lignes. Pire, le
    contrôle qui existe pour empêcher un compteur périmé le déclarait conforme :
    il comparait le bloc à ce que ce script produit, et ce script produisait le
    mauvais nombre.

    C'est le défaut que ce fichier corrige, retourné d'un cran : le nombre ne se
    recopie plus à la main, mais sa dérivation ne regardait qu'une partie du
    dépôt. Elle parcourt désormais les comptes rendus présents, comme
    `report_all.py` parcourt l'index des produits.
    """
    comptes = sorted(RAPPORTS.glob("*.generation.md"))
    if not comptes:
        raise CompteursError(
            f"aucun compte rendu de génération dans {_affichable(RAPPORTS)} : "
            "lancer `mise run generate` avant. Un bloc qui annonce zéro module "
            "produit passerait pour un dépôt vide."
        )
    ecrits = plan = 0
    for chemin in comptes:
        ligne = next(
            (
                ligne
                for ligne in chemin.read_text(encoding="utf-8").splitlines()
                if ligne.startswith("Modules écrits :")
            ),
            None,
        )
        if ligne is None:
            raise CompteursError(f"{_affichable(chemin)} ne porte pas sa ligne de modules")
        produits = int(ligne.split("**")[1])
        ecrits += produits
        plan += produits + int(ligne.split("**")[3])
    return ecrits, plan


def _tests() -> int:
    """Le nombre de tests que pytest collecte, demandé à pytest."""
    resultat = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", str(ROOT / "tests")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    # `N tests collected`, la ligne que pytest écrit lui-même. La forme courte
    # `-q` rend un compte par fichier qu'il faudrait sommer, et une somme est
    # une occasion de se tromper là où pytest a déjà fait le calcul.
    for ligne in reversed(resultat.stdout.splitlines()):
        mots = ligne.split()
        if len(mots) >= 3 and mots[1] in {"test", "tests"} and mots[2] == "collected":
            return int(mots[0])
    raise CompteursError(
        f"pytest n'a pas dit combien de tests il collecte :\n{resultat.stdout[-500:]}"
    )


def _mutations() -> int:
    donnees = json.loads(MUTATIONS.read_text(encoding="utf-8"))
    return len(donnees["mutations"])


def _jobs() -> tuple[int, tuple[str, ...]]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    noms = tuple(str(details.get("name", cle)).split(" (")[0] for cle, details in jobs.items())
    return len(jobs), noms


def _lignes_de_modules() -> list[str]:
    """Les modules livrés, avec leur `short_description`, lue dans le fichier.

    Recopier cette liste à la main était le même défaut que celui qui a fait
    annoncer 366 tests pour 420 : elle est restée à deux modules pendant que la
    collection en produisait seize.

    La description vient du module lui-même, donc du contrat : ce sont les mots
    qu'un utilisateur lira dans `ansible-doc`, pas une glose écrite à côté.
    """
    # Dérivé de `galaxy.yml`, jamais écrit segment par segment : c'est ce qui
    # a fait survivre trois chemins au renommage du namespace, chacun invisible
    # à toute recherche textuelle.
    dossier = load_collection().path / "plugins" / "modules"
    lignes: list[str] = []
    for fichier in sorted(dossier.glob("*.py")):
        if fichier.name.startswith("_"):
            continue
        courte = ""
        for ligne in fichier.read_text(encoding="utf-8").splitlines():
            if ligne.startswith("short_description:"):
                courte = ligne.split(":", 1)[1].strip().strip("\"'")
                break
        lignes.append(f"  {fichier.stem:<38s} {courte}")
    if not lignes:
        raise CompteursError(
            f"{_affichable(dossier)} ne porte aucun module : lancer "
            "`mise run generate`. Un bloc qui annonce zéro module est un bloc faux."
        )
    return lignes


def _plugins_dinventaire() -> list[str]:
    """Les plugins d'inventaire livrés, lus sur le disque.

    Le nom du plugin a changé une fois, de `scaleway` à `compute`, et cette
    ligne l'aurait annoncé sous son ancien nom : un bloc dérivé qui code un nom
    en dur n'est dérivé qu'à moitié.
    """
    dossier = load_collection().path / "plugins" / "inventory"
    return sorted(p.stem for p in dossier.glob("*.py") if not p.stem.startswith("_"))


def _table_des_modules() -> list[str]:
    """La table des modules du README de la collection, par produit.

    **Même source que la liste du README racine, et c'est le point.** Ce README
    documentait deux modules quand la collection en produisait 46, et c'est le
    fichier que `galaxy.yml` désigne, donc celui que Galaxy publie. Une seconde
    source recopiée à la main aurait exactement le défaut mesuré en #55 : deux
    dérivations pour une même chose, une seule tenue à jour.

    Les produits se déduisent du préfixe du nom de module, qui est le nom du
    produit dans le contrat. Un troisième produit apparaîtra donc tout seul,
    sans qu'un titre de section soit à écrire.
    """
    dossier = load_collection().path / "plugins" / "modules"
    par_produit: dict[str, list[tuple[str, str]]] = {}
    for fichier in sorted(dossier.glob("*.py")):
        if fichier.name.startswith("_"):
            continue
        courte = ""
        for ligne in fichier.read_text(encoding="utf-8").splitlines():
            if ligne.startswith("short_description:"):
                courte = ligne.split(":", 1)[1].strip().strip("\"'")
                break
        produit = fichier.stem.split("_", 1)[0]
        par_produit.setdefault(produit, []).append((fichier.stem, courte))

    if not par_produit:
        raise CompteursError(
            f"{_affichable(dossier)} ne porte aucun module : lancer "
            "`mise run generate`. Une table qui annonce zéro module est une table fausse."
        )

    titres = {"instance": "Instance", "lb": "Load Balancer"}
    lignes: list[str] = []
    for produit, modules in sorted(par_produit.items()):
        lignes += [
            "",
            f"### {titres.get(produit, produit.title())} ({len(modules)} modules)",
            "",
            "| module | what it does |",
            "|---|---|",
            *(f"| `{nom}` | {courte} |" for nom, courte in modules),
        ]
    inventaire = load_collection().path / "plugins" / "inventory"
    plugins = sorted(p.stem for p in inventaire.glob("*.py") if not p.stem.startswith("_"))
    if plugins:
        lignes += [
            "",
            "### Inventory plugins",
            "",
            "| plugin | what it discovers |",
            "|---|---|",
            *(
                f"| `{nom}` | Instances, Elastic Metal and Apple Silicon, "
                "with their private-network addresses |"
                for nom in plugins
            ),
        ]
    return lignes[1:]


def _pourcent(valeur: float) -> str:
    """Le point décimal et l'espace insécable de l'anglais.

    Ce nombre atterrit dans un README publié, et la frontière de langue du
    projet passe là : ce qui est publié est en anglais, le code qui le produit
    reste en français.
    """
    return f"{valeur * 100:.1f}%"


def _pourcent_anglais(numerateur: int, denominateur: int) -> str:
    """Le ratio des modules appelés, recalculé plutôt que reformaté.

    `example_coverage` rend une chaîne à la virgule décimale, parce que sa
    sortie terminal reste en français. La reformater à coups de `replace`
    marcherait aujourd'hui et casserait le jour où l'un des deux change.
    """
    if denominateur == 0:
        return "n/a"
    return _pourcent(numerateur / denominateur)


def bloc() -> str:
    """Le bloc, tel qu'il doit être aujourd'hui."""
    rapport = _rapport("instance", "v1")
    totaux = rapport["totals"]
    genres = totaux["by_kind"]
    modes = totaux["by_mode"]
    couverture = rapport["day2_automation_coverage"]
    ecrits, plan = _modules_ecrits()
    nb_jobs, noms_jobs = _jobs()
    exemple = mesurer_exemple()
    appeles = len(exemple["appeles_par_lexemple"])

    return "\n".join(
        [
            "```text",
            f"instance v1: {totaux['operations']} operations discovered",
            f"  INFO {genres['info']} · ACTION {genres['action']} · "
            f"MANAGE {genres['manage']} · WORKFLOW {genres['workflow']} · "
            f"LIFECYCLE {genres['lifecycle']} · IGNORE {genres['ignore']} · "
            f"UNKNOWN {genres['unknown']}",
            f"  Day-2 {totaux['day2_candidates']} · AUTO {modes['auto']} · "
            f"MANUAL {modes['manual']} · classified for automatic generation "
            f"{_pourcent(couverture)} ({modes['auto'] + modes['override']}"
            f"/{totaux['day2_candidates']})",
            "",
            f"collection stephrobert.scaleway: {ecrits} modules written out of {plan} planned",
            *_lignes_de_modules(),
            # Le nom du plugin se lit sur le disque, il ne se recopie pas : il
            # vient d'être renommé, et cette ligne aurait continué d'annoncer
            # `scaleway` sur un plugin qui s'appelle `compute`.
            *(
                f"  {nom + ' (inventory)':<38s} instance, elastic_metal, apple_silicon"
                for nom in _plugins_dinventaire()
            ),
            # **Le troisième étage, et il ne dit pas la même chose que les deux
            # autres.** « Classées » dit ce que le générateur autorise,
            # « produites » ce qu'il écrit, et celui-ci ce que l'exemple appelle.
            # Un module écrit n'est pas un module éprouvé.
            #
            # Il s'arrête là où le hors-ligne s'arrête : ce ratio dit que le
            # playbook nomme le module, pas qu'un run l'a joué. Ce second
            # nombre existe, il vient de l'artefact qu'un run laisse derrière
            # lui, et il ne peut pas entrer ici puisqu'il dépend d'une
            # exécution. `mise run coverage:example` le publie.
            f"  {appeles} modules called by the example playbook out of {ecrits} "
            f"({_pourcent_anglais(appeles, ecrits)}), which is not the same as played",
            f"  {_tests()} unit tests · {_mutations()} mutations proven by /falsify",
            f"  CI: {nb_jobs} jobs, {' · '.join(noms_jobs)}",
            "  ansible-test sanity, playbooks and inventory against the emulator:",
            "  reported by `mise run sanity` and `mise run integration`",
            "```",
        ]
    )


def _remplace(fichier: Path, texte: str, nouveau: str) -> str:
    if DEBUT not in texte or FIN not in texte:
        raise CompteursError(
            f"les marqueurs manquent dans {_affichable(fichier)}. Encadrer le bloc par :\n"
            f"{DEBUT}\n...\n{FIN}"
        )
    avant = texte[: texte.index(DEBUT) + len(DEBUT)]
    apres = texte[texte.index(FIN) :]
    return f"{avant}\n{nouveau}\n{apres}"


def blocs() -> dict[Path, str]:
    """Les blocs dérivés, et le fichier de chacun.

    **Deux publics, deux fichiers, un seul mécanisme.** Le README racine
    s'adresse à qui veut comprendre le générateur, celui de la collection à qui
    veut l'installer, et `galaxy.yml` désigne le second, donc c'est lui que
    Galaxy publie. Les deux dérivent des mêmes modules : les tenir par deux
    scripts ferait revenir le défaut de #55, où deux sources d'un même bloc
    n'avaient pas suivi le même élargissement.
    """
    return {
        README: bloc(),
        README_COLLECTION: "\n".join(_table_des_modules()),
    }


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    groupe = parseur.add_mutually_exclusive_group(required=True)
    groupe.add_argument("--write", action="store_true", help="réécrire le bloc")
    groupe.add_argument("--check", action="store_true", help="échouer s'il a vieilli")
    arguments = parseur.parse_args(argv[1:])

    perimes: list[str] = []
    for fichier, contenu in blocs().items():
        texte = fichier.read_text(encoding="utf-8")
        attendu = _remplace(fichier, texte, contenu)
        nom = _affichable(fichier)
        if arguments.write:
            if attendu == texte:
                print(f"{nom} : déjà à jour")
                continue
            fichier.write_text(attendu, encoding="utf-8")
            print(f"{nom} : réécrit")
            continue
        if attendu != texte:
            perimes.append(nom)
        else:
            print(f"{nom} : conforme à la mesure")

    if perimes:
        print(
            f"ces blocs ne correspondent plus à ce qui est mesuré : {', '.join(perimes)}.\n"
            "Lancer `mise run readme` puis relire le diff : un nombre recopié à la\n"
            "main vieillit en silence, et se lit exactement comme une mesure.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except CompteursError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
