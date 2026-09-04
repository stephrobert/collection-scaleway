"""Le recensement des réécritures compte-t-il ce qu'il annonce compter ?

Chaque assertion d'idempotence du playbook d'exemple tolère une route non
émulée par une disjonction. La tolérance est voulue : contre l'émulateur, une
route absente n'est pas un défaut de la collection. Mais une assertion
satisfaite par sa branche de tolérance ne vérifie rien, et le playbook publie
donc le nombre d'idempotences réellement prouvées.

**Ce fichier lit les tâches dans le playbook réel**, plutôt que d'en recopier
les expressions. Une copie donnerait un test vert sur du Jinja que plus
personne ne joue, et ce serait exactement le défaut qu'on prétend corriger.

Et il les **joue** : `yaml.safe_load` accepte une expression Jinja fautive, et
`selectattr('value.api_type', ...)` sur un chemin pointé ne se vérifie qu'en
l'exécutant.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
PLAYBOOK = REPO_ROOT / "examples" / "playbooks" / "modules.yml"

# Les quatre tâches qui construisent le recensement, nommées comme dans le
# playbook. Une tâche renommée fait rougir ce test plutôt que de le vider.
TACHES = (
    "Les réécritures identiques, recensées par leur registre",
    "Chaque réécriture, avec ce que son module a rendu",
    "Ce que la cible n'a pas mesuré, faute de cible ou faute de route",
    "Les idempotences réellement prouvées",
)

# Les trois formes qu'un registre prend réellement, et une variable voisine que
# le recensement ne doit pas ramasser.
REGISTRES: dict[str, Any] = {
    "repris_ok": {"changed": False, "failed": False},
    # Une réécriture qui a changé quelque chose n'est pas une idempotence
    # prouvée. Le premier recensement la comptait quand même, en s'appuyant sur
    # les assertions écrites à côté ; quatre réécritures ajoutées sans assertion
    # ont suffi à rendre ce compte faux.
    "repris_a_change": {"changed": True, "failed": False},
    "repris_saute": {"changed": False, "skipped": True, "skip_reason": "pas de cible"},
    "repris_absent": {"changed": False, "failed": True, "api_type": "not_emulated"},
    "ecrit_serveur": {"changed": True},
}


def _taches_du_recensement() -> list[dict[str, Any]]:
    document = yaml.safe_load(PLAYBOOK.read_text(encoding="utf-8"))
    toutes = {tache["name"]: tache for jeu in document for tache in jeu["tasks"]}
    manquantes = [nom for nom in TACHES if nom not in toutes]
    if manquantes:
        raise AssertionError(
            "le playbook ne porte plus ces tâches, le recensement a été renommé "
            f"ou supprimé : {manquantes}"
        )
    return [toutes[nom] for nom in TACHES]


@pytest.fixture(scope="module")
def recensement(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Joue les tâches du playbook sur des registres fabriqués."""
    executable = shutil.which("ansible-playbook")
    if executable is None:
        pytest.skip("ansible-playbook absent")

    dossier = tmp_path_factory.mktemp("recensement")
    sortie = dossier / "mesure.json"
    tache_finale = {
        "name": "Ce que le recensement a conclu",
        "ansible.builtin.copy": {
            "dest": str(sortie),
            "content": (
                "{{ {'noms': noms_repris,"
                " 'non_mesurees': reecritures_non_mesurees,"
                " 'prouvees': idempotences_prouvees} | to_json }}"
            ),
        },
    }
    jeu = {
        "name": "Le recensement, joué hors de la stack",
        "hosts": "localhost",
        "gather_facts": False,
        "tasks": [
            {"name": "Les registres", "ansible.builtin.set_fact": dict(REGISTRES)},
            *_taches_du_recensement(),
            tache_finale,
        ],
    }
    fichier = dossier / "recensement.yml"
    fichier.write_text(yaml.safe_dump([jeu], allow_unicode=True), encoding="utf-8")

    environnement = dict(os.environ, ANSIBLE_LOCALHOST_WARNING="False")
    resultat = subprocess.run(
        [executable, "-i", "localhost,", "-c", "local", str(fichier)],
        capture_output=True,
        text=True,
        cwd=dossier,
        env=environnement,
    )
    if resultat.returncode != 0:
        raise AssertionError(f"le recensement n'a pas joué :\n{resultat.stdout}\n{resultat.stderr}")
    return dict(json.loads(sortie.read_text(encoding="utf-8")))


def test_le_recensement_ne_ramasse_que_les_reecritures(recensement: dict[str, Any]) -> None:
    """Il se construit sur le préfixe `repris_`, pas sur une liste tenue à la main.

    `ecrit_serveur` est une écriture, pas une réécriture : la compter
    doublerait le dénominateur et gonflerait le taux d'idempotence.
    """
    assert recensement["noms"] == [
        "repris_a_change",
        "repris_absent",
        "repris_ok",
        "repris_saute",
    ]


def test_une_reecriture_sautee_ou_non_emulee_nest_pas_une_preuve(
    recensement: dict[str, Any],
) -> None:
    """Les deux formes de non-mesure, et elles sont nommées plutôt que comptées.

    Une tâche sautée n'a rien écrit ; une route non émulée a rendu 501. Dans les
    deux cas l'assertion d'idempotence est passée par sa branche de tolérance.
    """
    assert recensement["non_mesurees"] == ["repris_absent", "repris_saute"]


def test_seule_une_reecriture_jouee_compte_comme_prouvee(recensement: dict[str, Any]) -> None:
    """Le nombre publié est celui des idempotences que quelqu'un a vraiment vues.

    Trois façons de ne pas compter, et la troisième est la plus récente : une
    réécriture **jouée** qui a changé quelque chose n'a rien prouvé du tout.
    """
    assert recensement["prouvees"] == ["repris_ok"]


# --- l'assertion qui ne tolère rien sur le compte réel ---------------------

ASSERTION_REELLE = "Contre le cloud réel, chaque réécriture doit être mesurée"


def _joue(dossier: Path, faits: dict[str, Any], taches: list[dict[str, Any]]) -> int:
    """Joue des tâches sur des faits fabriqués, et rend le code de retour."""
    executable = shutil.which("ansible-playbook")
    if executable is None:
        pytest.skip("ansible-playbook absent")
    jeu = {
        "name": "Une tâche du playbook, jouée hors de la stack",
        "hosts": "localhost",
        "gather_facts": False,
        "tasks": [{"name": "Les faits", "ansible.builtin.set_fact": faits}, *taches],
    }
    fichier = dossier / "joue.yml"
    fichier.write_text(yaml.safe_dump([jeu], allow_unicode=True), encoding="utf-8")
    return subprocess.run(
        [executable, "-i", "localhost,", "-c", "local", str(fichier)],
        capture_output=True,
        text=True,
        cwd=dossier,
        env=dict(os.environ, ANSIBLE_LOCALHOST_WARNING="False"),
    ).returncode


def _tache(nom: str) -> dict[str, Any]:
    document = yaml.safe_load(PLAYBOOK.read_text(encoding="utf-8"))
    for jeu in document:
        for tache in jeu["tasks"]:
            if tache.get("name") == nom:
                return dict(tache)
    raise AssertionError(f"le playbook ne porte plus la tâche « {nom} »")


def test_sur_le_cloud_reel_une_reecriture_non_mesuree_fait_rougir(tmp_path: Path) -> None:
    """Une route absente y est un défaut, pas une limite déclarée.

    C'est la moitié qui compte : sans elle, la tolérance écrite pour
    l'émulateur suivrait jusque sur le compte réel, où elle n'a aucune raison
    d'être, et un module non exercé se lirait comme un module prouvé.
    """
    faits = {"cible": "reel", "reecritures_non_mesurees": ["repris_carte"]}
    assert _joue(tmp_path, faits, [_tache(ASSERTION_REELLE)]) != 0


def test_contre_lemulateur_la_meme_reecriture_est_toleree(tmp_path: Path) -> None:
    """Le cas voisin, qui ne doit pas bouger : la tolérance reste, elle est comptée."""
    faits = {"cible": "feint", "reecritures_non_mesurees": ["repris_carte"]}
    assert _joue(tmp_path, faits, [_tache(ASSERTION_REELLE)]) == 0
