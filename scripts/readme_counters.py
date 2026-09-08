"""Les nombres publiés dans le README, dérivés plutôt que recopiés.

Le README annonçait un compte de tests et de mutations que la mesure
démentait au même instant, et le message d'un commit un autre encore. ADR-007
relève ces écarts avec leurs nombres et leur date. Le défaut n'a rien
d'anecdotique dans un dépôt dont la thèse est qu'on mesure au lieu de supposer :
**un nombre recopié à la main vieillit en silence, et se lit exactement comme
une mesure.**

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
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import docs_quality
import yaml
from example_coverage import mesurer as mesurer_exemple

from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
#: Le README que `galaxy.yml` désigne, donc celui que Galaxy publiera.
README_COLLECTION = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "README.md"
#: Il porte lui aussi un lien vers le dépôt, et Galaxy l'affiche à côté de la
#: version : un lien vers `main` y mène à un fichier qui a bougé depuis.
GALAXY = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "galaxy.yml"
RAPPORTS = ROOT / "build" / "reports"

#: La raison qu'un compte rendu porte quand `--module` a restreint la
#: production. Sa présence dit que le fichier ne mesure pas le dépôt, et le
#: générateur l'écrit déjà : rien à ajouter là-bas, seulement à le lire ici.
RESTREINTE = "`--module` restreint cette production"
MUTATIONS = ROOT / "tests" / "falsify" / "specs.json"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

DEBUT = "<!-- compteurs:début, produits par scripts/readme_counters.py -->"
FIN = "<!-- compteurs:fin -->"


#: Un bloc nommé, pour les fichiers qui en portent plusieurs.
#:
#: Le mécanisme n'en acceptait qu'un par fichier, et c'est cette limite qui a
#: fait écrire à la main la table de compatibilité, les exemples de
#: versionnement et un compte de modules, trois nombres qu'un audit de la
#: 0.2.0 publiée a trouvés faux.
def _marqueurs(nom: str) -> tuple[str, str]:
    return (
        f"<!-- compteurs:{nom}:début, produits par scripts/readme_counters.py -->",
        f"<!-- compteurs:{nom}:fin -->",
    )


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

    **Ce compteur n'a longtemps lu qu'`instance.v1`**, et annonçait donc le
    compte d'un seul produit sous une liste qui les parcourait tous (ADR-007).
    Pire, le contrôle qui existe pour empêcher un compteur périmé le déclarait
    conforme :
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

        # **Un compte rendu de génération restreinte n'est pas une mesure du
        # dépôt.** `--module` écarte tout le reste, et le compte rendu part dans
        # le même répertoire que celui d'une génération complète : le fichier se
        # lit pareil et dit autre chose. Le README a publié le compte d'un seul
        # module, et `--check` l'a déclaré conforme puisqu'il compare le bloc à
        # cette même source (ADR-007).
        if RESTREINTE in chemin.read_text(encoding="utf-8"):
            raise CompteursError(
                f"{_affichable(chemin)} vient d'une génération restreinte par "
                "`--module` : elle ne mesure pas le dépôt. Relancer "
                "`mise run generate` sans périmètre."
            )

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
    annoncer un compte de tests démenti par la mesure (ADR-007) : elle est
    restée à deux modules pendant que la collection en produisait bien plus.

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
    qualite, _ = docs_quality.mesurer()

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
            # **Ce qu'une page publiée vaut, et pas seulement combien il y en
            # a.** Le bloc comptait les modules écrits ; il ne disait rien de ce
            # qu'un lecteur y trouve. Les options sans description et les
            # exemples en `<zone>` étaient invisibles d'ici, et une page Galaxy
            # est publiée pour toujours.
            f"  {qualite.modules} published pages: "
            f"{qualite.options_decrites}/{qualite.options} options and "
            f"{qualite.retours_decrits}/{qualite.retours} returned keys documented",
            f"  {qualite.exemples_copiables}/{qualite.exemples} examples copyable as is · "
            f"{qualite.retours_detailles}/{qualite.retours_composites} returned keys "
            "list their fields",
            f"  {_tests()} unit tests · {_mutations()} mutations proven by /falsify",
            f"  CI: {nb_jobs} jobs, {' · '.join(noms_jobs)}",
            "  ansible-test sanity, playbooks and inventory against the emulator:",
            "  reported by `mise run sanity` and `mise run integration`",
            "```",
        ]
    )


#: Un lien vers ce dépôt, avec la référence git qu'il traverse. Seul ce dépôt
#: est concerné : un lien vers `ansible-collections/ansible-inclusion` désigne
#: un autre projet, dont `main` est la bonne référence.
LIEN_DU_DEPOT = re.compile(
    r"(https://github\.com/stephrobert/collection-scaleway/(?:blob|tree)/)([^/\s)]+)(/)"
)


def _versionner_les_liens(texte: str, version: str) -> str:
    """Fait pointer les liens du dépôt sur le tag de la version publiée.

    Sur Galaxy, la page annonce une version et ses liens menaient à `main`,
    donc à des fichiers qui ont bougé depuis. Le tag existe forcément quand
    quelqu'un lit la page : `release.py` refuse de publier si le tag et
    `galaxy.yml` divergent.
    """
    return LIEN_DU_DEPOT.sub(rf"\g<1>{version}\g<3>", texte)


def _remplace(
    fichier: Path,
    texte: str,
    nouveau: str,
    bornes: tuple[str, str] = (DEBUT, FIN),
) -> str:
    debut, fin = bornes
    if debut not in texte or fin not in texte:
        raise CompteursError(
            f"les marqueurs manquent dans {_affichable(fichier)}. Encadrer le bloc par :\n"
            f"{debut}\n...\n{fin}"
        )
    avant = texte[: texte.index(debut) + len(debut)]
    apres = texte[texte.index(fin) :]
    return f"{avant}\n{nouveau}\n{apres}"


def _serie(version: str) -> str:
    """`0.2.0` -> `0.2.x` : la série que la compatibilité décrit."""
    majeure, mineure, _ = version.split(".", 2)
    return f"{majeure}.{mineure}.x"


def _versions_dansible() -> list[str]:
    """Les versions d'`ansible-core` que la CI éprouve vraiment.

    Elles se lisent dans la matrice du workflow, pas dans une liste recopiée :
    une version déclarée et jamais jouée est une promesse sans preuve, et une
    version jouée et jamais déclarée ne se voit nulle part.
    """
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for job in (document.get("jobs") or {}).values():
        matrice = (job.get("strategy") or {}).get("matrix") or {}
        for valeurs in matrice.values():
            if not isinstance(valeurs, list):
                continue
            trouve = [
                re.sub(r"[^0-9.]", "", str(v).split(",")[0])
                for v in valeurs
                if isinstance(v, str) and v.startswith(">=")
            ]
            if trouve:
                return trouve
    raise CompteursError(
        f"aucune matrice d'`ansible-core` dans {_affichable(WORKFLOW)} : "
        "la table de compatibilité annoncerait des versions que rien n'éprouve."
    )


def bloc_compatibilite() -> str:
    """La table de compatibilité, dont la série suit `galaxy.yml`."""
    collection = load_collection()
    versions = ", ".join(_versions_dansible())
    return "\n".join(
        [
            "| collection | `ansible-core` | Python | Scaleway SDK |",
            "|---|---|---|---|",
            f"| {_serie(collection.version)} | {versions} | >= 3.12 | >= 2.9.0 |",
        ]
    )


def bloc_versionnement() -> str:
    """Les exemples de versionnement, comptés depuis la version publiée.

    Illustrer un correctif par `0.1.1` sur une page qui affiche 0.2.0 se lit
    comme un texte hérité, et c'est bien ce que c'était.
    """
    majeure, mineure, correctif = (int(x) for x in load_collection().version.split(".", 2))
    return "\n".join(
        [
            f"* **patch** (`{majeure}.{mineure}.{correctif + 1}`): bug fixes only;",
            f"* **minor** (`{majeure}.{mineure + 1}.0`): backward-compatible features "
            "and new modules;",
            f"* **major** (`{majeure + 1}.0.0`): may contain breaking changes.",
        ]
    )


def bloc_classification() -> str:
    """Ce que la classification d'Instance donne, mesuré sur le compte rendu.

    Le document publiait 41 Day-2, 40 AUTO, 97,6 % et 14 IGNORE, quand la
    mesure disait 40, 39, 97,5 % et 15. Quatre nombres faux dans une phrase qui
    commence par « Measured on Instance v1 ».
    """
    rapport = _rapport("instance", "v1")
    totaux = rapport["totals"]
    genres = totaux["by_kind"]
    modes = totaux["by_mode"]
    return (
        f"Measured on Instance v1: **{totaux['day2_candidates']} Day-2 candidates, "
        f"{modes['auto']} AUTO, {modes['manual']} MANUAL, coverage "
        f"{_pourcent(rapport['day2_automation_coverage'])}**, out of "
        f"{totaux['operations']} operations discovered, of which "
        f"{genres['lifecycle']} LIFECYCLE and {genres['ignore']} IGNORE."
    )


def bloc_runtime_etat() -> str:
    """L'état du runtime, dont le nombre de tests qui le mesurent.

    Le document en annonçait 49, un compte figé au jour où la phrase a été
    écrite. Ce qui est publié ici est le nombre de tests qui portent vraiment
    sur le runtime, pas le total du dépôt : le second serait vrai et hors sujet.
    """
    resultat = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            str(ROOT / "tests" / "unit" / "collection"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    compte = None
    for ligne in reversed(resultat.stdout.splitlines()):
        mots = ligne.split()
        if len(mots) >= 3 and mots[1] in {"test", "tests"} and mots[2] == "collected":
            compte = int(mots[0])
            break
    if compte is None:
        raise CompteursError(
            "pytest n'a pas dit combien de tests portent sur le runtime. "
            "Un compte deviné vaut moins que pas de compte."
        )
    return (
        f"State: written, measured by {compte} unit tests, judged by "
        "`ansible-test sanity`, and\nexercised end to end against a local emulator "
        "and against a real Scaleway\naccount."
    )


def bloc_effacables() -> str:
    """Combien de champs un module sait effacer, et sur combien de modules.

    Le nombre est publié plutôt que décrit : il disait le travail restant tant
    que rien ne s'effaçait, il dit maintenant la portée de ce qui s'efface, et
    une phrase sans nombre laisserait croire que la question est anecdotique.
    """
    from nullabilite import auditer

    champs = auditer()
    modules = len({champ.module for champ in champs})
    if not champs:
        return (
            "The contract marks no writable field as clearable on the products\n"
            "generated today: the question does not arise."
        )
    return (
        f"The contract marks **{len(champs)} writable fields** as clearable, "
        f"across {modules} modules.\n"
        "A managing module clears one when the playbook writes `field: null`, and\n"
        "leaves it untouched when the option is omitted. The two are told apart by\n"
        "an omission witness, which publishes nothing on the page: the option keeps\n"
        "its natural type, its choices and its elements. `mise run nullabilite`\n"
        "names the fields one by one."
    )


def bloc_tests_badge() -> str:
    """La phrase du questionnaire OpenSSF qui compte les tests."""
    return (
        f"> {_tests()} unit tests, plus `ansible-test sanity` on four "
        "`ansible-core` versions and\n> an integration run of the shipped playbooks "
        "against a local emulator."
    )


def bloc_image() -> str:
    """La commande qui tire l'environnement d'exécution de la version publiée.

    Le numéro y était écrit à la main, et il aurait vieilli comme les trois
    autres qu'un audit a trouvés faux : il n'y a pas de `latest`, donc une
    commande périmée tire une image qui n'existe pas.
    """
    version = load_collection().version
    image = f"ghcr.io/stephrobert/collection-scaleway/ee:{version}"
    return "\n".join(
        [
            "```bash",
            f"podman pull {image}",
            "ansible-navigator run playbook.yml \\",
            f"  --execution-environment-image {image}",
            "```",
        ]
    )


#: Ce que le plugin d'inventaire pose sur chaque hôte découvert, et qu'un
#: module trouve donc sans rien demander à personne.
POSE_PAR_LINVENTAIRE: frozenset[str] = frozenset({"server_id", "zone", "region"})


def _autonomie_des_modules() -> tuple[int, int]:
    """Combien de modules se contentent de ce que l'inventaire pose, sur combien.

    **La phrase publiée disait « all any module needs », et c'était faux pour
    plus de la moitié** (#134). Une sous-ressource porte son propre identifiant,
    qu'aucune découverte de machine ne peut donner : `backend_id`,
    `certificate_id`, `route_id`. Le lecteur s'en aperçoit à l'essai, ce qui
    n'est pas un dommage, mais une affirmation absolue et fausse dans le premier
    exemple d'une page publiée abîme le reste.

    Un paramètre requis qui n'est pas un identifiant, `action` par exemple, est
    ce qu'un playbook écrit exprès : il ne compte pas comme un obstacle, il
    compte comme le sujet de la tâche.
    """
    import ast

    # Le chemin vient de `galaxy.yml`, jamais écrit segment par segment : c'est
    # ce qui a fait survivre trois chemins au renommage du namespace.
    dossier = load_collection().path / "plugins" / "modules"
    autonomes = total = 0
    for chemin in sorted(dossier.glob("*.py")):
        if chemin.name.startswith("_"):
            continue
        documentation: dict[str, Any] = {}
        for noeud in ast.parse(chemin.read_text(encoding="utf-8")).body:
            if isinstance(noeud, ast.Assign) and any(
                getattr(cible, "id", None) == "DOCUMENTATION" for cible in noeud.targets
            ):
                documentation = yaml.safe_load(ast.literal_eval(noeud.value)) or {}
        total += 1
        requis = {
            nom
            for nom, corps in (documentation.get("options") or {}).items()
            if (corps or {}).get("required") and nom not in POSE_PAR_LINVENTAIRE
        }
        if not any(nom.endswith(("_id", "_ids")) for nom in requis):
            autonomes += 1
    return autonomes, total


def bloc_nombre_de_modules() -> str:
    """La phrase du README racine, et ce qu'elle promet vraiment.

    Elle contredisait, à quelques lignes de distance, le bloc dérivé qui
    compte les mêmes modules (ADR-007). Elle promettait ensuite que ces
    variables suffisaient à **tous** les modules (#134).
    """
    autonomes, total = _autonomie_des_modules()
    return (
        f"The inventory sets `scaleway_id` and `scaleway_zone`, which is what {autonomes}\n"
        f"of the {total} modules need behind `delegate_to: localhost`. The other\n"
        f"{total - autonomes} act on a sub-resource carrying its own identifier, which the\n"
        "matching `_info` module returns."
    )


#: Ce que chaque bloc nommé produit.
NOMMES = {
    "compatibilite": lambda: bloc_compatibilite(),
    "versionnement": lambda: bloc_versionnement(),
    "image": lambda: bloc_image(),
    "classification": lambda: bloc_classification(),
    "runtime-etat": lambda: bloc_runtime_etat(),
    "effacables": lambda: bloc_effacables(),
    "tests-badge": lambda: bloc_tests_badge(),
    "modules": lambda: bloc_nombre_de_modules(),
}

#: Les blocs nommés, et le fichier de chacun. Un fichier, pas une catégorie :
#: le premier essai rangeait par « collection ou pas », et `galaxy.yml`, qui
#: n'est ni l'un ni l'autre, se voyait réclamer les marqueurs du README racine.
BLOCS_NOMMES: tuple[tuple[str, Path], ...] = (
    ("compatibilite", README_COLLECTION),
    ("versionnement", README_COLLECTION),
    ("image", README_COLLECTION),
    ("classification", ROOT / "docs" / "architecture" / "generator.md"),
    ("runtime-etat", ROOT / "docs" / "architecture" / "runtime.md"),
    ("effacables", ROOT / "docs" / "architecture" / "runtime.md"),
    ("tests-badge", ROOT / "docs" / "best-practices.md"),
    ("modules", README),
)


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

    version = load_collection().version
    perimes: list[str] = []
    # `galaxy.yml` n'a pas de bloc dérivé mais porte un lien : la liste des
    # fichiers à versionner n'est donc pas celle des blocs.
    a_versionner = {README, README_COLLECTION, GALAXY}
    # Les documents qui portent un bloc nommé entrent dans la boucle, même
    # sans bloc principal ni lien à versionner : sinon leurs blocs ne seraient
    # jamais produits, et la garde de `scripts/chiffres.py` se contenterait de
    # marqueurs autour de chiffres faux.
    a_versionner |= {cible for _, cible in BLOCS_NOMMES}
    for fichier in sorted(set(blocs()) | a_versionner):
        contenu = blocs().get(fichier)
        texte = fichier.read_text(encoding="utf-8")
        attendu = _remplace(fichier, texte, contenu) if contenu is not None else texte
        for nom, cible in BLOCS_NOMMES:
            if cible != fichier:
                continue
            attendu = _remplace(fichier, attendu, NOMMES[nom](), _marqueurs(nom))
        attendu = _versionner_les_liens(attendu, version)
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
