"""Ce qu'un produit doit passer avant d'entrer dans la collection.

`mise run report` dit qu'un produit est classé. `mise run parser:coverage` dit
ce que le parser ne sait pas lire. `mise run docs:quality` dit si la page se
comprend. Chacun mesure une chose, et aucun ne répond à la question qu'on pose
vraiment en ajoutant un troisième contrat :

    est-il sûr d'ajouter RDB ?

Et depuis #213, celle qui décide de l'adoption plutôt que de la correction :

    quelle opération récurrente ce produit débloque-t-il ?

Un produit dont aucun enchaînement n'appelle les modules ajoute des noms à
un README et rien à personne. La réponse est dérivée de ce qui
tourne, et un produit sans opération est admis en le disant, jamais refusé.

Répondre « les tests passent » à cette question n'est pas une réponse : les
tests passent aussi sur un produit dont le parser ignore la moitié des
constructions, dont personne n'a lu les pages, et dont la moitié des
opérations sortent en UNKNOWN.

Cette porte enchaîne les étapes dans l'ordre où elles s'éclairent, et rend un
verdict :

    couverture syntaxique OpenAPI
            v
    contraintes sémantiques traduites ou nommées
            v
    champs effaçables, comptés
            v
    classification Day-2 complète
            v
    complétude des écritures
            v
    stratégies de comparaison décidées
            v
    couverture documentaire
            v
    opérations récurrentes débloquées
            v
    ADMIS

**Toutes les étapes ne bloquent pas, et c'est délibéré.** Une porte qui
refuserait sur chaque mesure refuserait les deux produits déjà livrés, donc
personne ne la lancerait. Les étapes bloquantes sont celles dont l'échec
produit un module faux ; les autres publient un nombre, qui est le prix
d'admission et non un défaut.

    python scripts/admission.py instance      # un produit
    python scripts/admission.py --tous        # tous ceux de l'index

Codes de sortie : `0` admis, `1` erreur, `2` refusé.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from generator.plan import ProductPlan, build_plan
from generator.source.base import VendoredSpecSource

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs" / "scaleway"

EXIT_OK = 0
EXIT_ERREUR = 1
EXIT_REFUSE = 2


@dataclass(frozen=True)
class Etape:
    """Le verdict d'une étape, et ce qu'elle a regardé.

    `bloquante` porte la seule décision qui compte : un produit entre ou
    n'entre pas. `mesure` porte ce qui se paie sans interdire, et sa valeur est
    publiée telle quelle.
    """

    nom: str
    bloquante: bool
    tenue: bool
    detail: str

    @property
    def symbole(self) -> str:
        if self.tenue:
            return "ok"
        return "KO" if self.bloquante else "~ "


def etape_syntaxe(produit: str, version: str) -> Etape:
    """Ce que le parser ne sait pas lire dans ce contrat.

    Informative : une construction présente n'est pas un défaut, c'est un
    travail à décider. Le Load Balancer en a apporté une que personne n'avait
    prévue, et le prix s'est payé en connaissance de cause.
    """
    import parser_coverage

    _, lignes = parser_coverage.relever(produit, version)
    non_gerees = [nom for nom, compte, etat in lignes if compte and etat.startswith("non")]
    return Etape(
        nom="couverture syntaxique OpenAPI",
        bloquante=False,
        tenue=not non_gerees,
        detail=(
            f"{len(non_gerees)} construction(s) présente(s) et non gérée(s) : "
            f"{', '.join(non_gerees)}"
            if non_gerees
            else "aucune construction non gérée"
        ),
    )


def etape_contraintes(plan: ProductPlan) -> Etape:
    """Une contrainte trouvée dans le document est traduite, ou nommée (ADR-008).

    Bloquante : une contrainte trouvée et tue produit un module qui accepte ce
    que l'API refuse, et le défaut ne se voit qu'au premier playbook.
    """
    from generator.parser.openapi import CONTRAINTES_TRADUITES

    tues = [
        f"{mot} ({compte})"
        for mot, compte in plan.found_constraints()
        if mot not in CONTRAINTES_TRADUITES
        and not any(mot in avertissement for avertissement in plan.service.warnings)
    ]
    portees = plan.constraints()
    return Etape(
        nom="contraintes sémantiques",
        bloquante=True,
        tenue=not tues,
        detail=(
            f"trouvée(s) et ni traduite(s) ni nommée(s) : {', '.join(tues)}"
            if tues
            else ", ".join(f"{nom} : {compte}" for nom, compte in sorted(portees.items()))
        ),
    )


def etape_effacables(plan: ProductPlan) -> Etape:
    """Combien de champs le module ne saura pas effacer (#87, #114).

    Informative : la limite est connue, documentée et chiffrée. En faire un
    refus bloquerait la collection entière sur un travail déjà planifié.
    """
    import nullabilite

    champs = nullabilite.effacables(plan)
    return Etape(
        nom="champs effaçables",
        bloquante=False,
        tenue=not champs,
        detail=(
            f"{len(champs)} champ(s) qu'un playbook ne pourra pas effacer"
            if champs
            else "aucun champ effaçable écrit par un module"
        ),
    )


def etape_classification(plan: ProductPlan) -> Etape:
    """Aucune opération ne disparaît en silence (ADR-001).

    Bloquante, et c'est la règle de sécurité du projet : une opération
    qu'aucune règle ne tranche est indiscernable d'une opération oubliée.
    """
    manques = [item.operation.key for item in plan.unknown]
    orphelins = list(plan.orphan_overrides)
    problemes = [f"{len(manques)} non classée(s)"] if manques else []
    if orphelins:
        problemes.append(f"{len(orphelins)} override(s) orphelin(s)")
    return Etape(
        nom="classification Day-2",
        bloquante=True,
        tenue=not problemes,
        detail=(
            ", ".join(problemes)
            if problemes
            else f"{len(plan.operations)} opération(s) classée(s), {len(plan.day2)} Day-2"
        ),
    )


def etape_ecritures(
    plan: ProductPlan, specs: Sequence[object], ecartes: tuple[tuple[str, str], ...]
) -> Etape:
    """Tout module de gestion prévu est écrit, ou écarté avec sa raison.

    Bloquante : un module de gestion prévu qui disparaît en silence est
    indiscernable d'un module oublié, et c'est ADR-001.

    **Écarté avec sa raison n'est pas manquant**, et confondre les deux punirait
    le comportement que le dépôt encourage. `instance_server_user_data` n'est
    pas écrit parce que le contrat ne décrit aucun champ du corps de
    `SetServerUserData` : le module ne saurait pas quoi envoyer, la raison est
    portée, et le compte rendu de génération la publie. La première version de
    cette étape le refusait, sur un produit livré.
    """
    from generator.ir.enums import OperationKind

    attendus = {
        item.module for item in plan.operations if item.kind is OperationKind.MANAGE and item.module
    }
    ecrits = {getattr(spec, "name", None) for spec in specs}
    excuses = {nom for nom, raison in ecartes if raison}
    manquants = sorted(attendus - ecrits - excuses)
    return Etape(
        nom="complétude des écritures",
        bloquante=True,
        tenue=not manquants,
        detail=(
            f"module(s) de gestion prévu(s), non écrit(s) et sans raison : {', '.join(manquants)}"
            if manquants
            else (
                f"{len(attendus & ecrits)} module(s) de gestion écrit(s), "
                f"{len(attendus & excuses)} écarté(s) avec sa raison"
            )
        ),
    )


def etape_comparaisons(plan: ProductPlan, specs: Sequence[object]) -> Etape:
    """Chaque paramètre géré porte une stratégie de comparaison (ADR-009).

    Bloquante sur l'absence, informative sur le repli : un paramètre sans
    stratégie serait comparé strictement sans que personne l'ait décidé, alors
    qu'un `ordered_list` est une décision prise et comptée.
    """
    strategies = plan.comparison_strategies(specs)
    sans = sum(
        1
        for spec in specs
        for nom in getattr(spec, "managed_params", ())
        if nom not in dict(getattr(spec, "comparisons", ()))
    )
    return Etape(
        nom="stratégies de comparaison",
        bloquante=True,
        tenue=sans == 0,
        detail=(
            f"{sans} paramètre(s) géré(s) sans stratégie"
            if sans
            else ", ".join(f"{nom} : {compte}" for nom, compte in sorted(strategies.items()))
            or "aucun module de gestion"
        ),
    )


def etape_documentation(modules: set[str]) -> Etape:
    """Les pages de ce produit se comprennent sans le contrat (ADR-005).

    Bloquante : le critère du dépôt est qu'un module se comprenne depuis sa
    seule page Galaxy, et une page est publiée pour toujours.
    """
    import docs_quality

    _, defauts = docs_quality.mesurer()
    miens = [defaut for defaut in defauts if defaut.bloquant and defaut.module in modules]
    return Etape(
        nom="couverture documentaire",
        bloquante=True,
        tenue=not miens,
        detail=(
            f"{len(miens)} défaut(s) documentaire(s) bloquant(s)"
            if miens
            else f"{len(modules)} page(s) sans défaut bloquant"
        ),
    )


#: Où vivent les opérations livrées : les rôles portent ce qu'elles font, les
#: playbooks les appellent. Lire les deux évite de manquer une opération qui
#: n'aurait pas encore de rôle.
OPERATIONS = (
    ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "roles",
    ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "playbooks",
)

#: Un appel de module dans une tâche : indenté, préfixé, suivi de deux-points.
#:
#: Le tiret optionnel couvre la forme compacte `- stephrobert.scaleway.x:`, du
#: YAML légitime qu'aucun playbook de ce dépôt n'emploie mais qu'une
#: contribution peut employer. Un commentaire ne passe pas : le `#` s'intercale
#: là où le motif attend le préfixe.
_APPEL = re.compile(r"^\s+(?:-\s+)?stephrobert\.scaleway\.([a-z0-9_]+):", re.MULTILINE)


def operations_du_produit(produit: str) -> dict[str, set[str]]:
    """Les opérations livrées qui appellent un module de ce produit.

    **Dérivé de ce qui tourne, jamais déclaré.** Une table écrite à la main
    dirait qu'un produit débloque une opération le jour où cette opération
    aura changé de modules, et personne ne le verrait.

    Un module se rattache à son produit par son préfixe, qui est la convention
    de nommage que le générateur applique : `lb_load_balancer_info` appartient
    à `lb`, `instance_server_action` à `instance`.
    """
    trouvees: dict[str, set[str]] = {}
    for racine in OPERATIONS:
        if not racine.is_dir():
            continue
        for chemin in sorted(racine.rglob("*.yml")):
            appels = {
                module
                for module in _APPEL.findall(chemin.read_text(encoding="utf-8"))
                if module.startswith(f"{produit}_")
            }
            if appels:
                # Le nom de l'opération est celui du rôle, ou du playbook quand
                # il n'a pas de rôle : c'est ce qu'un opérateur tape.
                nom = chemin.parent.parent.name if chemin.parent.name == "tasks" else chemin.stem
                trouvees.setdefault(nom, set()).update(appels)
    return trouvees


def etape_operations(produit: str) -> Etape:
    """Quelle opération récurrente ce produit débloque-t-il ?

    Non bloquante. Un produit sans opération n'est pas refusé : il est admis
    sans opération, et le rapport le dit. Refuser serait interdire d'ajouter un
    contrat avant d'avoir écrit l'enchaînement qui s'en sert, c'est à dire
    interdire l'ordre dans lequel le travail se fait.
    """
    operations = operations_du_produit(produit)
    return Etape(
        nom="opérations débloquées",
        bloquante=False,
        tenue=bool(operations),
        detail=(
            ", ".join(sorted(operations))
            if operations
            else "aucune : les modules existent, aucun enchaînement livré ne les appelle"
        ),
    )


def examiner(produit: str, version: str) -> list[Etape]:
    """Les étapes d'un produit, dans l'ordre où elles s'éclairent."""
    from generator.ansible.collection import load_collection
    from generator.ansible.models import build_module_specs

    plan = build_plan(produit, version, spec_root=SPECS)
    construits, ecartes = build_module_specs(plan, load_collection())
    specs = list(construits)
    modules = {spec.name for spec in construits}
    return [
        etape_syntaxe(produit, version),
        etape_contraintes(plan),
        etape_effacables(plan),
        etape_classification(plan),
        etape_ecritures(plan, specs, ecartes),
        etape_comparaisons(plan, specs),
        etape_documentation(modules),
        etape_operations(produit),
    ]


def rendre(produit: str, version: str, etapes: list[Etape]) -> bool:
    """Imprime le verdict d'un produit, et dit s'il est admis."""
    print(f"═══ {produit} {version}")
    for etape in etapes:
        print(f"  {etape.symbole} {etape.nom:<34} {etape.detail}")

    refus = [etape.nom for etape in etapes if etape.bloquante and not etape.tenue]
    prix = [etape for etape in etapes if not etape.bloquante and not etape.tenue]
    if prix:
        print("\n  Le prix d'admission, mesuré et non interdit :")
        for etape in prix:
            print(f"    {etape.nom} : {etape.detail}")
    if refus:
        print(f"\n  REFUSÉ : {', '.join(refus)}")
        return False
    print("\n  ADMIS")
    return True


def main(argv: list[str]) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("produit", nargs="?", help="le produit à examiner")
    analyseur.add_argument("--api-version", default="v1")
    analyseur.add_argument("--tous", action="store_true", help="tous les produits de l'index")
    options = analyseur.parse_args(argv)

    if options.tous:
        cibles = list(VendoredSpecSource(root=SPECS).available())
    elif options.produit:
        cibles = [(options.produit, options.api_version)]
    else:
        analyseur.error("nommer un produit, ou passer --tous")

    if not cibles:
        print(
            "aucun produit examiné : une porte qui n'examine rien admet tout.",
            file=sys.stderr,
        )
        return EXIT_ERREUR

    admis = True
    for produit, version in cibles:
        admis = rendre(produit, version, examiner(produit, version)) and admis
        print()
    return EXIT_OK if admis else EXIT_REFUSE


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
