"""Les clés que l'exemple lit, confrontées à celles que les modules publient.

Un playbook qui lit `types.result` sur un module rendant `servers` ne le dit
qu'au run : `mise run check` reste vert, `mise run sanity` aussi, et c'est le
job `Plateforme d'exemple` qui rougit, plusieurs minutes après la poussée. Le
cas est arrivé (#161), sur une clé qu'un correctif du parser venait de renommer.

Ce contrôle est **statique et hors ligne**. Il relève les `register:` des tâches
qui appellent un module de la collection, cherche les `<variable>.<clé>` dans
tout le fichier, et refuse une clé que le `RETURN` du module ne déclare pas.

**Ce qu'il ne sait pas lire, il le compte et le nomme.** Jinja permet plus que
ce qu'une expression régulière attrape : `resultat[nom_calculé]` ne se résout
pas hors ligne. Compter une expression inanalysable comme vérifiée serait
exactement la décoration que ce dépôt refuse ailleurs ; elle sort donc dans une
rubrique à part, et le compte est publié.

    python scripts/cles_lues.py            # le relevé
    python scripts/cles_lues.py --check    # la porte

Codes de sortie : `0` conforme, `1` erreur, `2` une clé lue que rien ne publie.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "examples" / "playbooks"
MODULES = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "plugins" / "modules"
RUNTIME = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "plugins"
RUNTIME = RUNTIME / "module_utils" / "scaleway.py"
PREFIXE = "stephrobert.scaleway."

#: Ce qu'Ansible ajoute à tout résultat de tâche, quel que soit le module.
#:
#: Elles ne viennent pas du `RETURN`, et les refuser ferait rougir le contrôle
#: sur `resultat is changed` ou `resultat.msg`, que tout playbook écrit.
RESULTAT_ANSIBLE: frozenset[str] = frozenset(
    {
        "changed",
        "failed",
        "failed_when_result",
        "msg",
        "skipped",
        "skip_reason",
        "results",
        "rc",
        "stdout",
        "stderr",
        "stdout_lines",
        "stderr_lines",
        "diff",
        "invocation",
        "warnings",
        "deprecations",
        "attempts",
        "exception",
        "item",
        "ansible_facts",
        "start",
        "end",
        "delta",
        "elapsed",
        "changed_when_result",
    }
)


def erreur_du_runtime() -> frozenset[str]:
    """Les clés que le runtime ajoute quand un module échoue.

    **Lues dans le code, pas recopiées à côté.** `ScalewayApiError.details()`
    les construit une par une ; une seconde liste ici vieillirait sans que
    personne s'en aperçoive, et le contrôle refuserait alors une lecture
    parfaitement légitime, `resultat.api_type` par exemple.

    C'est le même choix que `test_derive_ipam_vpc` : confronter ce que le code
    fait **vraiment**, lu par AST.
    """
    arbre = ast.parse(RUNTIME.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if not (isinstance(noeud, ast.FunctionDef) and noeud.name == "details"):
            continue
        cles = {
            cible.slice.value
            for interne in ast.walk(noeud)
            if isinstance(interne, ast.Assign)
            for cible in interne.targets
            if isinstance(cible, ast.Subscript)
            and isinstance(cible.slice, ast.Constant)
            and isinstance(cible.slice.value, str)
        }
        cles |= {
            element.value
            for interne in ast.walk(noeud)
            if isinstance(interne, ast.Dict)
            for element in interne.keys
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        }
        if cles:
            return frozenset(cles)
    raise ClesError(
        "`ScalewayApiError.details()` est introuvable ou ne pose aucune clé : "
        "le contrôle refuserait alors les lectures d'erreur, qui sont légitimes."
    )


#: Une lecture d'attribut : `types.servers`. Le nom de la variable est injecté.
_LECTURE = r"\b{}\.([A-Za-z_][A-Za-z0-9_]*)"

#: Un accès qu'on ne sait pas résoudre : `resultat[...]`. Compté, jamais ignoré.
_INDIRECT = r"\b{}\s*\["


class ClesError(RuntimeError):
    """Le contrôle n'a rien pu examiner."""


def playbooks() -> list[Path]:
    return sorted(PLAYBOOKS.glob("*.yml"))


def registres(document: object) -> dict[str, str]:
    """Variable enregistrée -> module de la collection qui l'a produite.

    Une tâche qui enregistre le résultat d'autre chose qu'un module de la
    collection n'est pas retenue : ce contrôle ne sait rien des clés que
    `ansible.builtin.command` publie, et prétendre le contraire ferait un refus
    sur ce qu'il ne comprend pas.
    """
    trouves: dict[str, str] = {}
    jeux = document if isinstance(document, list) else [document]
    for jeu in jeux:
        if not isinstance(jeu, dict):
            continue
        for cle in ("tasks", "pre_tasks", "post_tasks", "handlers"):
            for tache in jeu.get(cle) or []:
                if not isinstance(tache, dict) or not tache.get("register"):
                    continue
                module = next(
                    (nom for nom in tache if isinstance(nom, str) and nom.startswith(PREFIXE)),
                    None,
                )
                if module is not None:
                    trouves[str(tache["register"])] = module[len(PREFIXE) :]
    return trouves


def cles_publiees(module: str) -> frozenset[str]:
    """Les clés de premier niveau que le `RETURN` du module déclare.

    Lues sur le fichier livré plutôt que sur le plan : c'est ce fichier que
    l'utilisateur chargera, et un plan qui dirait autre chose serait le défaut
    à trouver, pas la référence à croire.
    """
    chemin = MODULES / f"{module}.py"
    if not chemin.is_file():
        raise ClesError(f"{module} : aucun module livré de ce nom")
    texte = chemin.read_text(encoding="utf-8")
    if 'RETURN = r"""' not in texte:
        return frozenset()
    bloc = texte.split('RETURN = r"""', 1)[1].split('"""', 1)[0]
    declare = yaml.safe_load(bloc) or {}
    return frozenset(declare) if isinstance(declare, dict) else frozenset()


def examiner(chemin: Path) -> tuple[list[str], list[str]]:
    """Rend les clés fautives, et les expressions qu'on n'a pas su lire."""
    texte = chemin.read_text(encoding="utf-8")
    connus = registres(yaml.safe_load(texte))

    fautives: list[str] = []
    illisibles: list[str] = []
    for variable, module in sorted(connus.items()):
        publiees = cles_publiees(module) | RESULTAT_ANSIBLE | erreur_du_runtime()
        for cle in sorted(set(re.findall(_LECTURE.format(re.escape(variable)), texte))):
            if cle not in publiees:
                fautives.append(
                    f"{chemin.name} : `{variable}.{cle}` sur {module}, "
                    f"qui publie {sorted(cles_publiees(module)) or 'rien'}"
                )
        if re.search(_INDIRECT.format(re.escape(variable)), texte):
            illisibles.append(f"{chemin.name} : `{variable}[...]`, index non résolu hors ligne")
    return fautives, illisibles


def main(argv: list[str]) -> int:
    analyseur = argparse.ArgumentParser(description="Les clés que l'exemple lit")
    analyseur.add_argument("--check", action="store_true", help="refuser une clé non publiée")
    options = analyseur.parse_args(argv)

    fichiers = playbooks()
    if not fichiers:
        print(
            "aucun playbook examiné : un contrôle qui ne lit rien rend vert sur n'importe quoi.",
            file=sys.stderr,
        )
        return 1

    fautives: list[str] = []
    illisibles: list[str] = []
    variables = 0
    try:
        for chemin in fichiers:
            variables += len(registres(yaml.safe_load(chemin.read_text(encoding="utf-8"))))
            a, b = examiner(chemin)
            fautives.extend(a)
            illisibles.extend(b)
    except ClesError as erreur:
        print(str(erreur), file=sys.stderr)
        return 1

    if not variables:
        print(
            "aucune variable enregistrée sur un module de la collection : le "
            "contrôle ne mesure plus rien.",
            file=sys.stderr,
        )
        return 1

    print(f"{variables} variable(s) enregistrée(s) sur un module de la collection.")
    if illisibles:
        print(f"\n{len(illisibles)} expression(s) que ce contrôle n'a pas su lire :")
        for ligne in illisibles:
            print(f"  {ligne}")
        print("  Elles ne sont pas vérifiées, et ne comptent pas comme telles.")

    if fautives:
        print(
            f"\n{len(fautives)} clé(s) lue(s) qu'aucun module ne publie :\n"
            + "\n".join(f"  {ligne}" for ligne in fautives)
            + "\n\nLe playbook lit une clé que le `RETURN` du module ne déclare pas.\n"
            "Soit le playbook a vieilli, soit le module a changé de clé : dans les\n"
            "deux cas, le run le dirait, mais plusieurs minutes plus tard.",
            file=sys.stderr,
        )
        return 2 if options.check else 0

    print("\nToutes les clés lues sont publiées par le module qui les produit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
