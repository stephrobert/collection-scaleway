"""Un audit qui corrigerait ne serait plus un audit.

C'est la frontière que ce dépôt tient partout : Terraform provisionne, Ansible
exploite. Un audit qui réparerait ce qu'il trouve la franchirait, et la
réparation que personne n'a demandée est la façon dont une automatisation perd
la confiance qu'elle avait (#209).

Ces tests portent sur ce que le rôle ne peut pas faire par construction, et sur
ce que son verdict distingue.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[3]
COLLECTION = RACINE / "ansible_collections" / "stephrobert" / "scaleway"
ROLE = COLLECTION / "roles" / "fleet_audit"
TACHES = ROLE / "tasks" / "main.yml"


def test_laudit_nappelle_aucune_ecriture() -> None:
    """Lecture seule, et c'est ce qui en fait une commande qu'on planifie.

    Le test lit le rôle plutôt que son exécution : un module d'écriture ajouté
    demain doit rougir ici, même si aucune politique du jour ne l'exerce.
    """
    appels = set(
        re.findall(
            r"^\s+stephrobert\.scaleway\.([a-z0-9_]+):",
            TACHES.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
    )
    assert appels, "le motif ne reconnaît plus aucun appel : il ne mesure plus rien"

    non_lecteurs = sorted(nom for nom in appels if not nom.endswith("_info"))
    assert non_lecteurs == [], f"un audit en lecture seule appelle {non_lecteurs}"


def test_la_politique_livree_ne_fait_echouer_personne_le_premier_jour() -> None:
    """Un rapport qui échoue au premier run est un rapport qu'on désactive.

    La politique livrée est un point de départ, pas un avis sur le parc de
    quelqu'un : toutes ses règles sont des avertissements, et les remplacer est
    l'objet de l'exercice.
    """
    defauts = yaml.safe_load((ROLE / "defaults" / "main.yml").read_text(encoding="utf-8"))
    regles = defauts["scaleway_fleet_audit_policy"]["rules"]

    assert regles, "la politique livrée est vide : l'audit refuserait de juger"
    severites = {nom: regle["severity"] for nom, regle in regles.items()}
    assert set(severites.values()) == {"warn"}, (
        f"la politique livrée porte {severites} : une règle `fail` par défaut "
        "impose un avis sur le parc de quelqu'un d'autre"
    )


def test_le_verdict_distingue_un_avertissement_dun_echec() -> None:
    """Sinon les deux sévérités n'en feraient qu'une.

    Une planification qui n'échoue jamais visiblement est une planification que
    personne ne regarde ; une qui échoue sur tout est une planification qu'on
    éteint.
    """
    verdict = yaml.safe_load(TACHES.read_text(encoding="utf-8"))
    assertion = next(
        tache for tache in verdict if tache.get("name") == "No rule of severity fail is broken"
    )
    condition = assertion["ansible.builtin.assert"]["that"][0]

    assert "_scaleway_fleet_audit_fail" in condition
    assert "warn" not in condition, (
        "le verdict compte aussi les avertissements : ils cesseraient d'être des avertissements"
    )


def test_une_zone_muette_ne_compte_jamais_comme_conforme() -> None:
    """Un `PASS` sur un parc qu'on n'a pas lu serait pire que pas d'audit.

    Il serait crédible. Les zones muettes ressortent dans le résultat
    d'opération, du côté de ce qui n'a pas été mesuré.
    """
    texte = TACHES.read_text(encoding="utf-8")

    assert "unmeasured=_scaleway_fleet_audit_muettes" in texte, (
        "les zones muettes n'entrent plus dans le résultat : elles "
        "disparaîtraient du rapport au lieu d'y être nommées"
    )
    conformes = re.search(r"already_compliant=(\S+),", texte)
    assert conformes and "muettes" not in conformes.group(1), (
        "une zone muette est comptée comme conforme"
    )
