"""Un rapport de parc ne compte jamais une zone qu'il n'a pas pu lire.

C'est la règle sur laquelle tout le playbook repose, et la seule qui le rend
digne de confiance : une zone qui ne répond pas n'a pas été mesurée vide. Un
rapport qui la compterait comme zéro serait pire que pas de rapport, parce qu'il
serait plausible.

`residue.py` refuse le même amalgame contre un compte réel, et `doctor` en fait
son troisième état. Ces tests jouent le playbook contre un port que personne
n'écoute : toutes les zones sont muettes, et rien de ce qui sort ne doit se lire
comme un parc vide.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]
COLLECTION = RACINE / "ansible_collections" / "stephrobert" / "scaleway"
PLAYBOOK = COLLECTION / "playbooks" / "fleet_report.yml"
#: Le comportement vit dans le rôle depuis #207 : la façade se joue, le rôle se lit.
TACHES = COLLECTION / "roles" / "fleet_report" / "tasks" / "main.yml"
PORT_MORT = "http://127.0.0.1:4999"


def _jouer(*options: str) -> tuple[int, str]:
    resultat = subprocess.run(
        ["ansible-playbook", str(PLAYBOOK), *options],
        env={
            "PATH": f"/usr/bin:/bin:{RACINE}/.venv/bin",
            "HOME": os.environ.get("HOME", "/tmp"),
            "ANSIBLE_COLLECTIONS_PATH": str(RACINE),
            "SCW_API_URL": PORT_MORT,
            "SCW_ACCESS_KEY": "SCW" + "XXXXXXXXXXXXXXXXXXX",
            "SCW_SECRET_KEY": "11111111-2222-3333-4444-555555555555",
        },
        capture_output=True,
        text=True,
        timeout=600,
    )
    return resultat.returncode, resultat.stdout + resultat.stderr


@pytest.fixture(scope="module")
def ansible_disponible() -> None:
    if not (RACINE / ".venv" / "bin" / "ansible-playbook").is_file():
        pytest.skip("ansible-playbook absent de l'environnement")


@pytest.fixture(scope="module")
def sortie_muette(ansible_disponible: None) -> str:
    """Un run où aucune zone ne répond, joué une fois pour tous les tests."""
    code, sortie = _jouer("-e", "zones=fr-par-1,nl-ams-1")
    assert code == 0, sortie
    return sortie


# --- la règle qui fonde tout ----------------------------------------------


def test_aucune_zone_mesuree_ne_se_lit_pas_comme_un_parc_vide(sortie_muette: str) -> None:
    assert "No zone answered" in sortie_muette
    assert "which is not the same as nothing being there" in sortie_muette


def test_les_zones_muettes_sont_nommees(sortie_muette: str) -> None:
    """Savoir lesquelles est ce qui permet de réparer, ou de relancer plus étroit."""
    assert "fr-par-1" in sortie_muette
    assert "nl-ams-1" in sortie_muette


def test_le_rapport_chiffre_ne_sort_pas_quand_rien_na_ete_mesure(sortie_muette: str) -> None:
    """Sinon `instances_total: 0` s'imprimerait à côté de « rien n'a répondu »."""
    assert "instances_by_state" not in sortie_muette


def test_une_zone_muette_ne_figure_quune_fois(ansible_disponible: None) -> None:
    """Elle est interrogée deux fois, pour les Instances et pour les balanceurs.

    La première version concaténait les deux listes et ne dédoublonnait que la
    seconde, une question de priorité dans Jinja : chaque zone apparaissait en
    double.
    """
    _, sortie = _jouer("-e", "zones=fr-par-1", "-e", "output=json")
    citees = re.findall(r"No zone answered: ([^.]+)\.", sortie)
    assert citees, sortie
    noms = [nom.strip() for nom in citees[0].split(",")]
    assert noms == ["fr-par-1"], noms


# --- ce que le playbook refuse --------------------------------------------


def test_un_format_de_sortie_inconnu_est_refuse(ansible_disponible: None) -> None:
    code, sortie = _jouer("-e", "zones=fr-par-1", "-e", "output=csv")

    assert code != 0
    # Le refus vient du contrat d'arguments du rôle, donc avant la première
    # tâche, et il nomme les valeurs acceptées. Le test mesure le refus et ce
    # qu'il apprend, pas la phrase que ce dépôt aurait écrite : une garde
    # accrochée à une formulation rougit sur une reformulation d'Ansible.
    assert "text, json, markdown" in sortie
    assert "scaleway_fleet_report_output" in sortie


# --- ce qu'il ne fait jamais ----------------------------------------------


def test_le_rapport_nappelle_aucune_ecriture(ansible_disponible: None) -> None:
    """Lecture seule, et c'est ce qui en fait une première commande sans risque.

    Le test lit le rôle plutôt que son exécution : un module d'écriture ajouté
    demain doit rougir ici, même si la cible du jour ne l'exerce pas. Laisser ce
    test sur la façade l'aurait rendu vert sur un playbook qui n'appelle plus
    rien, ce qui est la façon la plus discrète de désarmer une garde.
    """
    texte = TACHES.read_text(encoding="utf-8")
    # Un appel de module, et pas un exemple d'usage en commentaire : en YAML il
    # est indenté et suivi de deux-points. Le motif large attrapait
    # `stephrobert.scaleway.fleet_report` de l'en-tête, qui n'appelle rien.
    appels = set(re.findall(r"^\s+stephrobert\.scaleway\.([a-z0-9_]+):", texte, flags=re.MULTILINE))
    assert appels, "le motif ne reconnaît plus aucun appel : il ne mesure plus rien"

    non_lecteurs = sorted(nom for nom in appels if not nom.endswith("_info"))
    assert non_lecteurs == [], f"un rapport en lecture seule appelle {non_lecteurs}"
