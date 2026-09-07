"""Ce qu'un module ne sait pas dire : « efface ce champ ».

Le contrat marque un champ effaçable de deux façons, `oneOf: [X, null]` ou
`type: [X, "null"]`, et l'IR les porte toutes deux depuis ADR-008. Le runtime,
lui, construit sa demande depuis les valeurs qui ne sont pas `None` :

    demande = {nom: params[nom] for nom in geres if params.get(nom) is not None}

Conséquence, et c'est tout le sujet :

```yaml
description: null        # « efface la description »
# description absente    # « n'y touche pas »
```

Les deux produisent **la même requête**. Un playbook qui veut effacer un champ ne
le peut pas, et rien ne le lui dit : le module rend `ok`, et le champ garde sa
valeur.

**Mesurer avant d'abstraire.** Une sémantique d'effacement se conçoit mal sans
savoir combien de champs la réclament, ni lesquels. Ce programme les compte et
les nomme. Si le compte vaut zéro, il n'y a rien à faire et c'est écrit ; il ne
vaut pas zéro, et le nombre chiffre le travail restant.

Ce programme ne juge pas : il ne rend jamais autre chose que 0, sauf quand il
n'a rien pu examiner. Compter n'est pas refuser, et transformer ce compte en
porte bloquerait la collection sur une limite connue et documentée.

    python scripts/nullabilite.py            # le rapport lisible
    python scripts/nullabilite.py --json     # le même, pour un autre programme
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from generator.ir.enums import ParameterLocation
from generator.plan import ProductPlan, build_plan
from generator.source.base import VendoredSpecSource

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs" / "scaleway"


@dataclass(frozen=True)
class ChampEffacable:
    """Un champ que le contrat dit effaçable et qu'un module écrit."""

    produit: str
    module: str
    operation: str
    champ: str
    type: str

    def to_dict(self) -> dict[str, str]:
        return {
            "product": self.produit,
            "module": self.module,
            "operation": self.operation,
            "field": self.champ,
            "type": self.type,
        }


def produits() -> list[tuple[str, str]]:
    """Les produits générés, lus par la même source que le rapport.

    Relire `products.txt` à la main ici ferait un second lecteur du même index,
    et les deux divergeraient au premier format inhabituel. Les contrats
    marqués `suivi` sont écartés par cette source : aucun module ne les porte,
    et compter leurs champs gonflerait la dette d'un travail que personne n'a
    l'intention de faire.
    """
    return list(VendoredSpecSource(root=SPECS).available())


def effacables(plan: ProductPlan) -> list[ChampEffacable]:
    """Les champs effaçables qu'un module écrit, pour un produit.

    Seuls les paramètres de **corps** comptent. Un identifiant de chemin ou un
    filtre de requête déclaré effaçable ne pose pas la question : personne
    n'efface une zone.
    """
    trouves: list[ChampEffacable] = []
    for item in plan.operations:
        if item.module is None:
            continue
        for parametre in item.operation.parameters:
            if parametre.nullable and parametre.location is ParameterLocation.BODY:
                trouves.append(
                    ChampEffacable(
                        produit=f"{plan.service.name}.{plan.service.version}",
                        module=item.module,
                        operation=item.operation.id,
                        champ=parametre.name,
                        type=parametre.type.value,
                    )
                )
    return sorted(
        trouves, key=lambda champ: (champ.produit, champ.module, champ.operation, champ.champ)
    )


def auditer() -> list[ChampEffacable]:
    """Le relevé complet, sur tous les produits générés."""
    return [
        champ
        for produit, version in produits()
        for champ in effacables(build_plan(produit, version, spec_root=SPECS))
    ]


def main(argv: list[str]) -> int:
    analyseur = argparse.ArgumentParser(description="Champs effaçables qu'un module écrit")
    analyseur.add_argument("--json", action="store_true", help="rendre le relevé en JSON")
    options = analyseur.parse_args(argv)

    if not produits():
        print(
            "aucun contrat examiné : un contrôle qui ne lit rien rend vert sur n'importe quoi.",
            file=sys.stderr,
        )
        return 1

    champs = auditer()
    if options.json:
        print(json.dumps([champ.to_dict() for champ in champs], indent=2, ensure_ascii=False))
        return 0

    print(f"{len(champs)} champ(s) que le contrat dit effaçables et qu'un module écrit.\n")
    if not champs:
        print("Aucun : la question de l'effacement ne se pose sur aucun module livré.")
        return 0

    print("Pour chacun, `champ: null` et `champ` absent produisent aujourd'hui la")
    print("même requête : le runtime construit sa demande depuis les valeurs non")
    print("nulles. Un playbook qui veut effacer ne le peut pas, et le module rend")
    print("`ok` sans avoir rien effacé.\n")
    print(f"{'module':<38} {'opération':<24} {'champ':<28} type")
    for champ in champs:
        print(f"{champ.module:<38} {champ.operation:<24} {champ.champ:<28} {champ.type}")

    par_module = len({champ.module for champ in champs})
    print(f"\n{par_module} module(s) concerné(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
