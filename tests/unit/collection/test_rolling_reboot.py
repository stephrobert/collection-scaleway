"""Attendre, c'est observer. Un délai fixe n'est pas une attente.

C'est le critère central de ce playbook : le contrat ne dit pas sous quel délai
une machine redémarre, donc rien ici ne le suppose. Un `sleep 60` qui marche
aujourd'hui devient le contrat de demain et ne mesure rien.

Le runtime porte déjà l'attente correcte : `poll_until` exige d'observer la
machine **quitter** `running` avant d'accepter qu'elle y soit revenue, et refuse
de conclure quand il n'a rien vu changer. Ce playbook ne la réécrit pas, il la
met dans un travail asynchrone pour tenir des lots.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parents[3]
COLLECTION = RACINE / "ansible_collections" / "stephrobert" / "scaleway"
PLAYBOOK = COLLECTION / "playbooks" / "rolling_reboot.yml"
#: Le comportement vit dans le rôle depuis #207. Deux fichiers le portent : les
#: tâches, et le lot qu'elles incluent.
ROLE = COLLECTION / "roles" / "rolling_reboot"
TACHES = ROLE / "tasks" / "main.yml"
LOT = ROLE / "tasks" / "batch.yml"


def _jouer(*options: str) -> tuple[int, str]:
    resultat = subprocess.run(
        ["ansible-playbook", str(PLAYBOOK), *options],
        env={
            "PATH": f"/usr/bin:/bin:{RACINE}/.venv/bin",
            "HOME": os.environ.get("HOME", "/tmp"),
            "ANSIBLE_COLLECTIONS_PATH": str(RACINE),
            "SCW_API_URL": "http://127.0.0.1:4999",
            "SCW_ACCESS_KEY": "SCW" + "XXXXXXXXXXXXXXXXXXX",
            "SCW_SECRET_KEY": "11111111-2222-3333-4444-555555555555",
        },
        capture_output=True,
        text=True,
        timeout=300,
    )
    return resultat.returncode, resultat.stdout + resultat.stderr


@pytest.fixture(scope="module")
def ansible_disponible() -> None:
    if not (RACINE / ".venv" / "bin" / "ansible-playbook").is_file():
        pytest.skip("ansible-playbook absent de l'environnement")


# --- la règle qui fonde le playbook ---------------------------------------


def test_aucune_attente_nest_une_duree_fixe() -> None:
    """Ni `pause`, ni `sleep`, ni `wait_for` sur un délai : que des observations.

    Le test lit les deux fichiers : une temporisation ajoutée demain rougit ici,
    même si aucun scénario ne l'exerce. C'est exactement ce qu'on ne peut pas
    mesurer autrement, parce qu'un `sleep` qui marche ne se distingue pas d'une
    attente juste tant que la machine est rapide.
    """
    for chemin in (TACHES, LOT):
        texte = chemin.read_text(encoding="utf-8")
        lignes = [
            ligne
            for ligne in texte.splitlines()
            # Les commentaires parlent de `sleep` pour dire qu'on n'en veut pas.
            if not ligne.lstrip().startswith("#")
        ]
        corps = "\n".join(lignes)
        for interdit in ("ansible.builtin.pause", "sleep", "wait_for:"):
            assert interdit not in corps, (
                f"{chemin.name} porte `{interdit}` : une attente se mesure sur une "
                "condition observée, jamais sur une durée"
            )


def test_lattente_passe_par_celle_du_module() -> None:
    """`wait: true` déclenche `poll_until`, qui exige d'observer un changement."""
    texte = LOT.read_text(encoding="utf-8")

    assert "wait: true" in texte, "le module doit porter l'attente"
    assert "async_status" in texte, "le lot attend des travaux, pas une durée"
    assert "until: retours.finished" in texte, "l'attente du lot est une observation"


def test_le_travail_asynchrone_survit_a_lattente_du_module() -> None:
    """Un travail tué en plein redémarrage ferait rendre le verdict au harnais.

    C'est la leçon que `runtime-proof.yml` porte chez le voisin : un harnais
    échoue plus souvent que ce qu'il mesure.
    """
    texte = LOT.read_text(encoding="utf-8")
    # Le nom de la variable est celui du rôle depuis #207. Le fait tenu est le
    # même : la marge vient de l'attente du module, pas d'un nombre écrit à côté.
    assert "(scaleway_rolling_reboot_wait_timeout | int) + 60" in texte, (
        "la durée de vie du travail doit dépasser l'attente du module"
    )


# --- ce que le playbook refuse --------------------------------------------


def test_sans_groupe_le_playbook_ne_fait_rien_et_le_dit(ansible_disponible: None) -> None:
    code, sortie = _jouer()

    assert code == 0
    assert "No group named" in sortie
    assert "without touching anything" in sortie


def test_un_groupe_nomme_et_vide_est_un_echec(ansible_disponible: None) -> None:
    code, sortie = _jouer("-e", "group=scw_tag_absent")

    assert code != 0
    assert "holds no host" in sortie
    assert "does not authorise acting on everything" in sortie


def test_un_lot_non_positif_est_refuse(ansible_disponible: None) -> None:
    code, sortie = _jouer("-e", "group=scw_tag_production", "-e", "batch_size=0")

    assert code != 0
    assert "must be a positive number" in sortie


# --- ce qu'il ne fait pas par construction --------------------------------


def test_aucune_valeur_par_defaut_ne_designe_une_cible() -> None:
    """Les deux endroits comptent : le rôle pour qui l'inclut, le playbook pour
    qui le lance. Un défaut ajouté d'un seul côté suffirait à redémarrer une
    production entière."""
    defauts = yaml.safe_load((ROLE / "defaults" / "main.yml").read_text(encoding="utf-8"))
    assert defauts.get("scaleway_rolling_reboot_group") == "", (
        "`scaleway_rolling_reboot_group` doit rester vide par défaut : un "
        "redémarrage progressif qui devine sa cible redémarre une production entière"
    )

    play = yaml.safe_load(PLAYBOOK.read_text(encoding="utf-8"))[0]
    assert play.get("vars", {}).get("group") == "", (
        "`group` doit rester vide par défaut dans le playbook livré"
    )


def test_une_seule_tache_ecrit() -> None:
    """Le reste lit. Et un redémarrage progressif n'allume jamais rien."""
    appels: list[str] = []
    for chemin in (TACHES, LOT):
        appels += re.findall(
            r"^\s+stephrobert\.scaleway\.([a-z0-9_]+):",
            chemin.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
    assert appels, "le motif ne reconnaît plus aucun appel : il ne mesure plus rien"

    ecritures = [nom for nom in appels if not nom.endswith("_info")]
    assert ecritures == ["instance_server_action"], ecritures


def test_seule_laction_reboot_est_declenchee() -> None:
    """`poweron` dans un redémarrage progressif démarrerait ce qui était arrêté."""
    texte = LOT.read_text(encoding="utf-8")
    actions = set(re.findall(r"^\s+action:\s*([a-z_]+)\s*$", texte, flags=re.MULTILINE))

    assert actions == {"reboot"}, actions
