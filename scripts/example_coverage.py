"""Le troisième étage de couverture : ce que l'exemple exerce, et ce qu'un run a joué.

Le dépôt publiait deux ratios, chacun nommé, chacun avec sa fraction :
**classées** pour génération automatique, et **portées par un module**. Ils
disent ce que le générateur autorise et ce qu'il produit. Il en manquait un
troisième, et c'est le seul qui parle d'usage : un module écrit n'est pas un
module éprouvé.

Trois choses distinctes, et les confondre serait le maquillage habituel :

* **appelé par l'exemple** se dérive hors ligne, du texte des playbooks. C'est
  une intention : le playbook nomme le module. Ce nombre entre dans le README ;
* **joué contre une cible** vient de l'artefact qu'un run laisse derrière lui,
  et il ne vaut que pour le run qui l'a produit. Une tâche sautée ou une route
  non émulée n'y comptent pas ;
* **idempotence prouvée** ne concerne que les modules de gestion, et vient du
  même artefact.

Le premier ne remplace pas les deux autres. Publier « exercé » en laissant
croire que ça veut dire « éprouvé contre le cloud réel » serait exactement ce
que la règle du dépôt sur les ratios interdit.

    python scripts/example_coverage.py            la matrice, en texte
    python scripts/example_coverage.py --json     la même chose, pour un script
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# **Le lecteur de la collection, pas un second.** `galaxy.yml` est déjà lu par
# `load_collection`, et le relire ici avec `yaml` ferait deux lecteurs d'une
# même identité, qui divergeraient au premier format inhabituel.
from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "examples" / "playbooks"
COLLECTION = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "plugins"
MODULES = COLLECTION / "modules"
INVENTAIRE = COLLECTION / "inventory"
ARTEFACTS = ROOT / "build" / "example"

#: Préfixe complet d'un contenu de cette collection dans un playbook.
PREFIXE = "stephrobert.scaleway."


#: Les modules qu'aucune cible de la stack ne peut exercer, et **pourquoi**.
#:
#: Ce n'est pas une liste de dispenses : c'est le seul endroit où un écart a le
#: droit d'exister, et il y est nommé. Le contrôle échoue sur un module absent
#: d'ici comme d'un playbook, donc en ajouter un demande d'écrire sa raison.
#: En retirer un demande de l'exercer.
@dataclass(frozen=True)
class SansCible:
    """Un module que l'exemple n'exerce pas, et ce qu'il faudrait pour lever ça.

    **Une raison seule vieillit sans que personne s'en aperçoive.** Elle décrit
    l'obstacle du jour où elle a été écrite, et rien ne rappelle de vérifier
    qu'il tient encore. Les champs qui l'accompagnent le rappellent :

    * `preuve` dit **ce qu'il faudrait**, et c'est la partie actionnable : une
      exemption qui n'attend qu'un changement de stack ne se traite pas comme
      une qui attend l'amont ;
    * `revoir_en` dit **quand rouvrir**, et le contrôle sort en 2 quand la
      version publiée l'a atteinte. Une échéance qu'on peut ignorer n'est pas
      une échéance ;
    * `issue` renvoie à l'endroit où la discussion vit, quand il y en a un.

    L'issue qui a demandé ça le disait elle-même : « bureaucratique à six
    exemptions, précieux à deux cents ». C'est écrit maintenant parce que le
    coût est bas maintenant.
    """

    raison: str
    #: Ce qu'il faudrait pour exercer le module. `stack` : étendre la
    #: topologie Terraform. `reel` : une décision sur le compte, coût ou
    #: résidu. `amont` : quelque chose que ni la stack ni nous ne contrôlons.
    preuve: str
    #: Version de la collection à partir de laquelle l'exemption se rouvre.
    revoir_en: str
    issue: int | None = None


#: Ce que `preuve` peut valoir. Fermée, pour qu'une faute de frappe ne produise
#: pas une exemption dont personne ne sait ce qu'elle attend.
PREUVES: frozenset[str] = frozenset({"stack", "reel", "amont"})

SANS_CIBLE: dict[str, SansCible] = {
    "instance_snapshot": SansCible(
        raison=(
            "demande un instantané que l'API Instance liste. Celui de la stack passe par "
            "l'API Block, seule à voir un volume SBS, et l'API Instance ne le liste pas. "
            "En tailler un dans le volume `l_ssd` échoue : « cannot create a RO disk from "
            "an empty disk », mesuré sur le compte réel."
        ),
        preuve="stack",
        revoir_en="0.6.0",
    ),
    "instance_snapshot_action": SansCible(
        raison=(
            "exporte un instantané, donc il lui en faut un : même raison que "
            "`instance_snapshot`, et le même volume vide."
        ),
        preuve="stack",
        revoir_en="0.6.0",
    ),
    "instance_ip_action": SansCible(
        raison=(
            "rend une adresse à l'IPAM. Toutes les adresses de la stack appartiennent à "
            "Terraform : en rendre une laisserait son état en désaccord avec le compte, "
            "et c'est exactement le résidu que la règle du dépôt interdit."
        ),
        preuve="stack",
        revoir_en="0.6.0",
    ),
    "lb_load_balancer_action": SansCible(
        raison=(
            "migre un load balancer vers un autre type commercial, et **refuse le "
            "non-changement** : migrer vers le type courant rend 400 `invalid_arguments`, "
            "mesuré sur le compte réel. Le seul appel que l'API accepte change donc la "
            "facture du compte pour la durée de l'exercice, et ce n'est pas une décision "
            "que l'exemple prend à la place de qui le lance. feint ne sert pas cette "
            "route non plus (501), donc aucune des deux cibles ne l'exerce."
        ),
        preuve="reel",
        revoir_en="0.7.0",
    ),
    "lb_subscriber": SansCible(
        raison=(
            "demande un destinataire d'alertes, et le provider Terraform ne déclare "
            "aucune ressource `scaleway_lb_subscriber` : il n'existe aucun moyen d'en "
            "créer un que la destruction emporte."
        ),
        preuve="amont",
        revoir_en="0.7.0",
    ),
}


def echeances_depassees(publiee: str) -> list[str]:
    """Les exemptions que la version publiée a rattrapées.

    **Une échéance qu'on peut ignorer n'est pas une échéance.** Le contrôle sort
    en 2 sur celles-là : soit l'obstacle tient toujours et la ligne se réécrit
    avec une échéance neuve et la mesure qui la justifie, soit il est tombé et
    le module rejoint l'exemple.

    Repousser en changeant le nombre est permis, et c'est le but : ce qui est
    refusé, c'est de ne rien décider.
    """
    return sorted(
        f"{nom} : à revoir depuis {exemption.revoir_en}, "
        f"attend {exemption.preuve} · {exemption.raison}"
        for nom, exemption in SANS_CIBLE.items()
        if _rang(publiee) >= _rang(exemption.revoir_en)
    )


def _rang(version: str) -> tuple[int, ...]:
    """`0.10.0` est postérieure à `0.9.0`, ce qu'une comparaison de chaînes nie."""
    return tuple(int(morceau) for morceau in version.split(".") if morceau.isdigit())


def non_modules() -> set[str]:
    """Ce qui porte le préfixe de la collection sans être un module.

    Les plugins d'inventaire se lisent sur le disque plutôt que d'être nommés
    ici. La liste écrite à la main valait `{"scaleway"}`, et le jour où le
    plugin a été renommé en `compute`, ce contrôle a refusé le playbook en
    disant que `compute` n'était pas un module. Il avait raison sur la forme et
    tort sur le fond, ce qui est la pire façon d'avoir raison.
    """
    if not INVENTAIRE.is_dir():
        return set()
    return {chemin.stem for chemin in INVENTAIRE.glob("*.py") if not chemin.stem.startswith("_")}


#: Les cibles de l'exercice, dans l'ordre où leur preuve coûte cher.
CIBLES = ("emulateur", "machines", "reel")


class CouvertureError(RuntimeError):
    """Une source manque ou se contredit, et un nombre faux serait pire."""


def modules_ecrits() -> set[str]:
    if not MODULES.is_dir():
        raise CouvertureError(f"{MODULES} n'existe pas : lancer `mise run generate`.")
    return {chemin.stem for chemin in MODULES.glob("*.py") if chemin.stem != "__init__"}


def _taches(noeud: Any) -> Iterator[dict[str, Any]]:
    """Toutes les tâches d'un document, `block`, `rescue` et `always` compris."""
    if isinstance(noeud, list):
        for element in noeud:
            yield from _taches(element)
        return
    if not isinstance(noeud, dict):
        return
    yield noeud
    for cle in ("tasks", "pre_tasks", "post_tasks", "handlers", "block", "rescue", "always"):
        if cle in noeud:
            yield from _taches(noeud[cle])


def modules_appeles() -> set[str]:
    """Ce que les playbooks appellent, lu dans les **clés de tâches**.

    **Pas dans le texte.** Le premier jet cherchait `stephrobert.scaleway.<nom>`
    dans le fichier entier, et c'était tenable tant que ce compte n'était qu'un
    ratio publié. Depuis qu'il est une porte, un module cité dans un commentaire
    qui explique son absence suffirait à la franchir : le contrôle mesurerait
    alors la prose du playbook, pas ce qu'il joue.

    Le YAML est donc parcouru, `block`, `rescue` et `always` compris, et seule
    une clé de tâche compte.
    """
    ecrits = modules_ecrits()
    trouves: set[str] = set()
    for chemin in sorted(PLAYBOOKS.glob("*.yml")):
        document = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        for tache in _taches(document):
            for cle in tache:
                nom = str(cle)
                if nom.startswith(PREFIXE):
                    trouves.add(nom[len(PREFIXE) :])
        # Un fichier d'inventaire n'est pas un playbook : son plugin se déclare
        # par une clé `plugin`, et c'est le seul cas où un nom complet compte
        # hors d'une clé de tâche.
        if isinstance(document, dict) and str(document.get("plugin", "")).startswith(PREFIXE):
            trouves.add(str(document["plugin"])[len(PREFIXE) :])
    inconnus = sorted(trouves - ecrits - non_modules())
    if inconnus:
        # Une faute de frappe dans un playbook ne doit pas se ranger en silence
        # du côté « pas un module » : elle produirait une tâche qui n'existe pas.
        raise CouvertureError(
            f"les playbooks nomment {inconnus}, qui n'est ni un module écrit ni le "
            "plugin d'inventaire. Faute de frappe, ou module supprimé sans que "
            "l'exemple suive."
        )
    return trouves & ecrits


def artefacts() -> dict[str, dict[str, Any]]:
    """Le dernier run enregistré par cible, quand il y en a un."""
    trouves: dict[str, dict[str, Any]] = {}
    for cible in CIBLES:
        chemin = ARTEFACTS / f"dernier-{cible}.json"
        if chemin.is_file():
            trouves[cible] = json.loads(chemin.read_text(encoding="utf-8"))
    return trouves


def _ratio(numerateur: int, denominateur: int) -> str:
    """Un ratio sans dénominateur est indéfini, pas nul."""
    if denominateur == 0:
        return "n/a"
    return f"{numerateur / denominateur * 100:.1f} %".replace(".", ",", 1)


def mesurer() -> dict[str, Any]:
    ecrits = modules_ecrits()
    appeles = modules_appeles()
    runs = artefacts()
    return {
        "modules_ecrits": sorted(ecrits),
        "appeles_par_lexemple": sorted(appeles),
        "jamais_appeles": sorted(ecrits - appeles),
        "sans_cible_declaree": sorted(ecrits & set(SANS_CIBLE)),
        "non_couverts": sorted(ecrits - appeles - set(SANS_CIBLE)),
        "ratio_appeles": _ratio(len(appeles), len(ecrits)),
        "runs": {
            cible: {
                "horodatage": run.get("horodatage"),
                "run_id": run.get("run_id"),
                "modules_joues": sorted(run.get("modules_joues", [])),
                "ratio_joues": _ratio(len(run.get("modules_joues", [])), len(ecrits)),
                "idempotence_prouvee": len(run.get("idempotence_prouvee", [])),
                "residu": run.get("residu"),
            }
            for cible, run in runs.items()
        },
    }


def rendre(mesure: dict[str, Any]) -> str:
    ecrits = len(mesure["modules_ecrits"])
    lignes = [
        f"modules écrits : {ecrits}",
        f"appelés par l'exemple : {len(mesure['appeles_par_lexemple'])} "
        f"sur {ecrits} ({mesure['ratio_appeles']})",
        "",
        "  ce ratio dit que le playbook nomme le module, pas qu'un run l'a joué.",
        "  Les deux se distinguent, et le second ne vaut que pour le run qui l'a produit.",
        "",
    ]
    if mesure["jamais_appeles"]:
        lignes += [
            "jamais appelés par l'exemple :",
            *(f"  {nom}" for nom in mesure["jamais_appeles"]),
            "",
        ]
    if not mesure["runs"]:
        lignes += [
            "aucun run enregistré sous build/example/. Le dire vaut mieux que",
            "d'écrire 0 % : rien n'a été mesuré, ce n'est pas que rien n'a marché.",
        ]
        return "\n".join(lignes) + "\n"
    lignes.append("derniers runs enregistrés :")
    for cible, run in mesure["runs"].items():
        lignes += [
            f"  {cible:10s} {run['horodatage']}  run {run['run_id']}",
            f"             joués {len(run['modules_joues'])} sur {ecrits} "
            f"({run['ratio_joues']}) · idempotences prouvées "
            f"{run['idempotence_prouvee']} · résidu : {run['residu']}",
        ]
    return "\n".join(lignes) + "\n"


def comparer(mesure: dict[str, Any]) -> dict[str, Any]:
    """Ce que le cloud réel sert et que l'émulateur ne sert pas.

    **C'est le matériau d'une issue de feint**, et il n'a rien d'une impression :
    les deux listes viennent de deux exécutions du même playbook, sur la même
    stack, chacune ayant laissé son artefact. Un module qui figure d'un côté et
    pas de l'autre a été appelé des deux côtés, et n'a répondu que d'un.

    `machines` plutôt qu'`emulateur` : c'est la cible qui démarre de vraies
    machines, donc la seule comparable au réel sur autre chose que le plan de
    contrôle.
    """
    runs = mesure["runs"]
    reel = runs.get("reel")
    feint = runs.get("machines") or runs.get("emulateur")
    if reel is None or feint is None:
        return {}
    cible_feint = "machines" if "machines" in runs else "emulateur"
    joues_reel = set(reel["modules_joues"])
    joues_feint = set(feint["modules_joues"])
    return {
        "reel": reel,
        "feint": feint,
        "cible_feint": cible_feint,
        "servis_par_le_reel_seul": sorted(joues_reel - joues_feint),
        "servis_par_feint_seul": sorted(joues_feint - joues_reel),
        "routes_non_emulees": feint.get("routes_non_emulees", []),
    }


def rendre_comparaison(ecart: dict[str, Any]) -> str:
    if not ecart:
        return (
            "il manque un artefact pour comparer. Lancer `python scripts/example.py reel`\n"
            "et `python scripts/example.py machines` : la comparaison porte sur ce que\n"
            "chaque exécution a réellement joué, pas sur ce que le playbook nomme.\n"
        )
    reel, feint = ecart["reel"], ecart["feint"]
    lignes = [
        f"reel        {reel['horodatage']}  run {reel['run_id']}  "
        f"{len(reel['modules_joues'])} modules joués",
        f"{ecart['cible_feint']:<11s} {feint['horodatage']}  run {feint['run_id']}  "
        f"{len(feint['modules_joues'])} modules joués",
        "",
    ]
    seuls = ecart["servis_par_le_reel_seul"]
    if seuls:
        lignes += [
            f"servis par le cloud réel et pas par feint ({len(seuls)}) :",
            *(f"  {nom}" for nom in seuls),
            "",
            "  Chacun a été appelé des deux côtés. C'est le matériau d'une issue feint :",
            "  mesuré le même jour, sur la même stack, avec le même playbook.",
            "",
        ]
    else:
        lignes += ["feint sert tout ce que le cloud réel a servi.", ""]
    if ecart["servis_par_feint_seul"]:
        lignes += [
            "servis par feint et pas par le cloud réel :",
            *(f"  {nom}" for nom in ecart["servis_par_feint_seul"]),
            "",
            "  C'est l'écart le plus intéressant : feint accepte ce que l'API refuse.",
            "",
        ]
    if ecart["routes_non_emulees"]:
        lignes += [
            "routes que feint déclare ne pas servir :",
            *(f"  {nom}" for nom in ecart["routes_non_emulees"]),
        ]
    return "\n".join(lignes) + "\n"


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--json", action="store_true", help="sortir la mesure en JSON")
    parseur.add_argument(
        "--check",
        action="store_true",
        help="échouer si un module livré n'est appelé par aucun playbook d'exemple",
    )
    parseur.add_argument(
        "--diff",
        action="store_true",
        help="comparer le dernier run réel au dernier run contre l'émulateur",
    )
    arguments = parseur.parse_args(argv[1:])
    try:
        mesure = mesurer()
    except CouvertureError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return 1

    if arguments.diff:
        ecart = comparer(mesure)
        print(
            json.dumps(ecart, indent=2, ensure_ascii=False)
            if arguments.json
            else rendre_comparaison(ecart)
        )
        return 0

    if arguments.check:
        # **Hors ligne et déterministe**, donc légitime dans `mise run check` :
        # ce contrôle lit le texte des playbooks et le répertoire des modules,
        # jamais un artefact de run.
        manquants = mesure["non_couverts"]
        if manquants:
            print(
                f"{len(manquants)} module(s) livré(s) qu'aucun playbook d'exemple n'appelle,\n"
                "et qui ne sont pas déclarés sans cible :\n"
                + "\n".join(f"  {nom}" for nom in manquants)
                + "\n\nUn module écrit que rien n'exerce est un module dont on ignore s'il\n"
                "marche, et la collection en publie le nom comme si de rien n'était.\n"
                "Étendre `examples/playbooks/modules.yml`, et la stack Terraform si le\n"
                "module n'a pas de cible. Si aucune cible n'est possible, l'écrire dans\n"
                "`SANS_CIBLE` avec sa raison : un écart se déclare, il ne se saute pas.",
                file=sys.stderr,
            )
            return 1

        # Un module déclaré sans cible qui a **cessé** d'être sans cible reste
        # une déclaration morte : elle raconterait un obstacle qui n'existe plus.
        perimees = sorted(set(SANS_CIBLE) & set(mesure["appeles_par_lexemple"]))
        if perimees:
            print(
                f"{len(perimees)} module(s) déclarés sans cible que l'exemple appelle "
                f"pourtant : {perimees}.\nRetirer la déclaration de `SANS_CIBLE` : elle "
                "décrit un obstacle qui n'existe plus.",
                file=sys.stderr,
            )
            return 1

        # **L'échéance est le dernier contrôle, et pas le premier.** Un module
        # qu'aucun playbook n'appelle est un défaut ; une exemption à rouvrir
        # est une décision qui attend. Les deux ne se lisent pas de la même
        # façon, et les mélanger ferait passer la seconde pour la première.
        rattrapees = echeances_depassees(load_collection().version)
        if rattrapees:
            print(
                f"{len(rattrapees)} exemption(s) que la version publiée a rattrapées :\n"
                + "\n".join(f"  {ligne}" for ligne in rattrapees)
                + "\n\nSoit l'obstacle tient toujours, et la ligne se réécrit avec une\n"
                "échéance neuve et la mesure qui la justifie ; soit il est tombé, et le\n"
                "module rejoint `examples/playbooks/`. Repousser est permis, ne rien\n"
                "décider ne l'est pas.",
                file=sys.stderr,
            )
            return 2

        exerces = len(mesure["appeles_par_lexemple"])
        total = len(mesure["modules_ecrits"])
        print(f"{exerces} module(s) sur {total} appelés par l'exemple")
        for nom in mesure["sans_cible_declaree"]:
            exemption = SANS_CIBLE[nom]
            print(
                f"  sans cible, déclaré : {nom} · à revoir en {exemption.revoir_en}, "
                f"attend {exemption.preuve} · {exemption.raison}"
            )
        return 0

    print(json.dumps(mesure, indent=2, ensure_ascii=False) if arguments.json else rendre(mesure))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
