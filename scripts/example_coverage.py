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
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "examples" / "playbooks"
COLLECTION = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "plugins"
MODULES = COLLECTION / "modules"
INVENTAIRE = COLLECTION / "inventory"
ARTEFACTS = ROOT / "build" / "example"


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


def modules_appeles() -> set[str]:
    """Ce que les playbooks nomment, lu dans leur texte.

    Une analyse du texte plutôt que du YAML : un module peut être appelé sous
    une clé de tâche, dans un `notify`, ou dans un commentaire qui documente son
    absence. Le premier cas est le seul qui compte, et l'intersection avec les
    modules écrits suffit à trancher, à une exception près qu'on refuse plutôt
    que d'avaler.
    """
    ecrits = modules_ecrits()
    trouves: set[str] = set()
    for chemin in sorted(PLAYBOOKS.glob("*.yml")):
        texte = chemin.read_text(encoding="utf-8")
        trouves |= set(re.findall(r"stephrobert\.scaleway\.([a-z0-9_]+)", texte))
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


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--json", action="store_true", help="sortir la mesure en JSON")
    arguments = parseur.parse_args(argv[1:])
    try:
        mesure = mesurer()
    except CouvertureError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return 1
    print(json.dumps(mesure, indent=2, ensure_ascii=False) if arguments.json else rendre(mesure))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
