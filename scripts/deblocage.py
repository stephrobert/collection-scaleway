"""Ce qui empêche une destruction d'aboutir, retiré pour qu'elle aboutisse.

`terraform destroy` échoue tant que les cartes réseau privées sont attachées :

```text
Error: scaleway-sdk-go: precondition failed: ,
       Can't delete a private network interface attached to a server
```

`scaleway_instance_private_nic` porte un `server_id`, donc Terraform la détruit
**avant** le serveur. Arrêter les serveurs n'y change rien.

**Ce ne sont pas deux façons d'appeler la même route, mais deux routes.** Le
provider passe par `instance/v2alpha1`, qui prend la carte seule et refuse en
412 tant qu'elle est attachée ; `scw instance private-nic delete` passe par la
route v1 imbriquée sous le serveur, qui rend 204 sur la même carte attachée.
C'est celle-là qu'on appelle ici, et c'est la seule qui accepte. ADR-017 porte
l'incident, la transcription qui l'établit, et sa date.

**Il ne s'exécute que sur un échec de destruction.** Le chemin heureux ne le
traverse jamais, donc un défaut ici ne peut pas casser une destruction qui
marchait. Et il ne retente qu'**une** fois : une boucle de destruction sans
borne sur un vrai cloud est pire que l'échec qu'elle prétend rattraper.

**Il ne touche que ce que le run a créé.** Le filtre est le préfixe de la
plateforme, et un filtre relâché supprimerait les cartes réseau des machines du
compte. C'est la seule chose vraiment dangereuse ici, et c'est pour ça qu'elle
est une fonction pure, testée, et couverte par une mutation.

    python scripts/deblocage.py acs-abc123     # ce qui serait retiré, sans rien retirer
    python scripts/deblocage.py acs-abc123 --retirer
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass


class DeblocageError(RuntimeError):
    """L'inventaire n'a pas pu être pris, ou une suppression a échoué."""


@dataclass(frozen=True)
class Carte:
    """Une carte réseau privée, et le serveur auquel elle est attachée."""

    zone: str
    serveur: str
    serveur_nom: str
    identifiant: str


def scw(arguments: tuple[str, ...]) -> list[dict[str, object]]:
    """Liste des ressources. Une commande qui échoue est une erreur.

    Elle n'est **pas** traitée comme « aucune carte » : un déblocage qui ne
    retire rien parce que la commande a échoué laisserait la destruction
    échouer une seconde fois sans que personne sache pourquoi.
    """
    resultat = subprocess.run(
        ["scw", *arguments, "-o", "json"], capture_output=True, text=True, check=False
    )
    if resultat.returncode != 0:
        raise DeblocageError(f"`scw {' '.join(arguments)}` a échoué :\n{resultat.stderr.strip()}")
    try:
        charge = json.loads(resultat.stdout or "[]")
    except ValueError as erreur:
        raise DeblocageError(
            f"`scw {' '.join(arguments)}` n'a pas rendu du JSON : {erreur}"
        ) from erreur
    return charge if isinstance(charge, list) else []


def serveurs_du_run(serveurs: list[dict[str, object]], prefixe: str) -> list[dict[str, object]]:
    """Ceux dont le nom porte le préfixe de la plateforme, et eux seuls.

    **C'est la seule chose dangereuse de ce module.** Un préfixe vide ou ignoré
    ferait retirer les cartes réseau de toutes les machines du compte, y compris
    celles que personne n'a créées pour cet exercice, et une machine sans carte
    n'est plus jointe à son réseau privé.

    Un préfixe vide est donc refusé plutôt que traité comme « tout ».
    """
    if not prefixe:
        raise DeblocageError(
            "préfixe vide : sans lui, le filtre porterait sur toutes les machines "
            "du compte, et pas sur la plateforme de l'exercice."
        )
    return [s for s in serveurs if str(s.get("name") or "").startswith(prefixe)]


def cartes(prefixe: str) -> list[Carte]:
    """Les cartes réseau privées des serveurs de la plateforme."""
    trouvees: list[Carte] = []
    for serveur in serveurs_du_run(scw(("instance", "server", "list")), prefixe):
        identifiant = str(serveur.get("id"))
        zone = str(serveur.get("zone") or "")
        for carte in scw(("instance", "private-nic", "list", f"server-id={identifiant}")):
            trouvees.append(
                Carte(
                    zone=zone,
                    serveur=identifiant,
                    serveur_nom=str(serveur.get("name") or "sans nom"),
                    identifiant=str(carte.get("id")),
                )
            )
    return sorted(trouvees, key=lambda c: (c.serveur_nom, c.identifiant))


def retirer(carte: Carte) -> None:
    """Supprime une carte. Un échec est une erreur, jamais un silence."""
    resultat = subprocess.run(
        [
            "scw",
            "instance",
            "private-nic",
            "delete",
            f"server-id={carte.serveur}",
            f"private-nic-id={carte.identifiant}",
            f"zone={carte.zone}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if resultat.returncode != 0:
        raise DeblocageError(
            f"la carte {carte.identifiant} de {carte.serveur_nom} n'a pas pu être "
            f"retirée :\n{resultat.stderr.strip()}"
        )


def deverrouiller(prefixe: str) -> list[Carte]:
    """Retire les cartes qui bloquent la destruction. Rend ce qui est parti.

    Rendre la liste plutôt qu'un compte : le lanceur l'imprime, et une
    destruction qui a demandé un déblocage doit dire lequel, sinon le défaut
    reste invisible d'un run à l'autre.
    """
    a_retirer = cartes(prefixe)
    for carte in a_retirer:
        retirer(carte)
    return a_retirer


def main(argv: list[str]) -> int:
    analyseur = argparse.ArgumentParser(
        description="Retirer les cartes réseau qui empêchent une destruction d'aboutir"
    )
    analyseur.add_argument("prefixe", help="préfixe de la plateforme, `acs-<run_id>`")
    analyseur.add_argument(
        "--retirer", action="store_true", help="retirer vraiment ; sans lui, seulement lister"
    )
    options = analyseur.parse_args(argv)

    try:
        trouvees = cartes(options.prefixe)
    except DeblocageError as erreur:
        print(str(erreur), file=sys.stderr)
        return 1

    if not trouvees:
        print(f"aucune carte réseau privée sur les serveurs de {options.prefixe}.")
        return 0

    for carte in trouvees:
        print(f"  {carte.serveur_nom}  carte {carte.identifiant}  zone {carte.zone}")
    if not options.retirer:
        print(f"\n{len(trouvees)} carte(s) listée(s). Ajouter --retirer pour les supprimer.")
        return 0

    try:
        for carte in trouvees:
            retirer(carte)
    except DeblocageError as erreur:
        print(str(erreur), file=sys.stderr)
        return 1
    print(f"\n{len(trouvees)} carte(s) retirée(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
