"""Prouve qu'un exercice contre le cloud réel n'a rien laissé derrière lui.

`terraform destroy` ne suffit pas comme garantie, et ce n'est pas une opinion :

* un `apply` interrompu laisse un état partiel, donc des ressources hors état ;
* supprimer un serveur Scaleway ne supprime pas toujours son volume, ce qui est
  le piège le plus courant du fournisseur. Mesuré sur le projet dédié avant
  d'écrire une ligne de stack : un volume block de 10 Go, zéro référence,
  survivait déjà à un serveur disparu.

La garantie est donc un **différentiel**, et non « le projet doit être vide » :
Scaleway crée d'office un VPC et un groupe de sécurité par projet, qui ne
doivent jamais être balayés.

    python scripts/residue.py capture   avant l'exercice
    python scripts/residue.py verify    après la destruction, sort en 1 s'il reste quelque chose

Le fichier de référence vit sous `build/`, jamais dans le dépôt : c'est l'état
d'un compte à un instant, pas un artefact du produit.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "build" / "residue" / "baseline.json"

#: Ce qu'on inventorie, et comment. Chaque entrée est un type de ressource que
#: la stack peut créer, avec la commande `scw` qui la liste.
#:
#: `iam` est à l'échelle de l'**organisation**, pas du projet : une clé SSH n'y
#: appartient pas au projet dédié, et la balayer d'office effacerait celles du
#: mainteneur. Elle est donc inventoriée comme les autres, et le différentiel
#: seul décide.
SURFACE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("instance.server", ("instance", "server", "list")),
    ("instance.ip", ("instance", "ip", "list")),
    ("instance.volume", ("instance", "volume", "list")),
    ("instance.snapshot", ("instance", "snapshot", "list")),
    ("instance.image", ("instance", "image", "list")),
    ("instance.security-group", ("instance", "security-group", "list")),
    ("instance.placement-group", ("instance", "placement-group", "list")),
    ("vpc.vpc", ("vpc", "vpc", "list")),
    ("vpc.private-network", ("vpc", "private-network", "list")),
    ("vpc-gw.gateway", ("vpc-gw", "gateway", "list")),
    ("vpc-gw.ip", ("vpc-gw", "ip", "list")),
    ("lb.lb", ("lb", "lb", "list")),
    ("lb.ip", ("lb", "ip", "list")),
    ("block.volume", ("block", "volume", "list")),
    ("block.snapshot", ("block", "snapshot", "list")),
    ("ipam.ip", ("ipam", "ip", "list")),
    ("iam.ssh-key", ("iam", "ssh-key", "list")),
)


class ResidueError(RuntimeError):
    """L'inventaire n'a pas pu être pris, ou il reste quelque chose."""


def scw(arguments: tuple[str, ...]) -> list[dict[str, Any]]:
    """Liste un type de ressource. Une commande qui échoue est une erreur.

    Elle n'est **pas** traitée comme « zéro ressource » : un inventaire qui
    compte zéro parce que la commande a échoué prouverait l'absence de résidu
    par sa propre panne, ce qui est exactement le vert qu'on refuse ailleurs.
    """
    resultat = subprocess.run(
        ["scw", *arguments, "-o", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if resultat.returncode != 0:
        raise ResidueError(f"`scw {' '.join(arguments)}` a échoué :\n{resultat.stderr.strip()}")
    try:
        charge = json.loads(resultat.stdout or "[]")
    except ValueError as erreur:
        raise ResidueError(
            f"`scw {' '.join(arguments)}` n'a pas rendu du JSON : {erreur}"
        ) from erreur
    return charge if isinstance(charge, list) else []


def inventaire() -> dict[str, dict[str, str]]:
    """L'état du compte : par type, les identifiants présents et leur nom."""
    etat: dict[str, dict[str, str]] = {}
    for nom, commande in SURFACE:
        etat[nom] = {
            str(item.get("id")): str(item.get("name") or item.get("address") or "sans nom")
            for item in scw(commande)
            if item.get("id")
        }
    return etat


def capture() -> int:
    etat = inventaire()
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(etat, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(v) for v in etat.values())
    print(f"référence prise : {total} ressource(s) préexistante(s), {BASELINE.relative_to(ROOT)}")
    for nom, items in sorted(etat.items()):
        if items:
            print(f"  {nom} : {', '.join(sorted(items.values()))}")
    return 0


def verify() -> int:
    if not BASELINE.is_file():
        raise ResidueError(
            f"{BASELINE.relative_to(ROOT)} est absent : lancer `capture` **avant** "
            "l'exercice. Sans référence, on ne peut rien prouver, et surtout pas "
            "l'absence de quelque chose."
        )
    avant = json.loads(BASELINE.read_text(encoding="utf-8"))
    apres = inventaire()

    residus: list[str] = []
    for nom, items in sorted(apres.items()):
        connus = avant.get(nom, {})
        for identifiant, libelle in sorted(items.items()):
            if identifiant not in connus:
                residus.append(f"  {nom}  {libelle}  ({identifiant})")

    if residus:
        print(f"{len(residus)} ressource(s) apparue(s) et non détruite(s) :", file=sys.stderr)
        print("\n".join(residus), file=sys.stderr)
        print(
            "\nLe compte n'est pas revenu à son état d'avant. Les supprimer à la main, "
            "puis comprendre pourquoi la destruction ne les a pas emportées : c'est "
            "cette raison-là qui doit être corrigée, pas seulement la ressource.",
            file=sys.stderr,
        )
        return 1

    disparus = [
        f"  {nom}  {libelle}"
        for nom, items in sorted(avant.items())
        for identifiant, libelle in sorted(items.items())
        if identifiant not in apres.get(nom, {})
    ]
    if disparus:
        print(f"{len(disparus)} ressource(s) préexistante(s) ont disparu :", file=sys.stderr)
        print("\n".join(disparus), file=sys.stderr)
        print(
            "\nL'exercice a détruit ce qu'il n'avait pas créé. C'est plus grave qu'un résidu.",
            file=sys.stderr,
        )
        return 1

    total = sum(len(v) for v in apres.values())
    print(f"aucun résidu : le compte est revenu à ses {total} ressource(s) d'avant")
    return 0


def main(argv: list[str]) -> int:
    action = argv[1] if len(argv) > 1 else ""
    if action == "capture":
        return capture()
    if action == "verify":
        return verify()
    print("usage : python scripts/residue.py capture|verify", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except ResidueError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
