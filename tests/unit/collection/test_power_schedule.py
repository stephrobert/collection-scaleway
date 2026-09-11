"""Un planificateur d'extinction refuse avant d'agir, ou il coûte une production.

Le mode de défaillance de cette catégorie est simple et cher : une sélection que
personne n'a vérifiée, et un `poweroff` à 20:00 sur des machines que le
planificateur n'était pas censé atteindre. Ces tests portent sur ce que le
playbook refuse, parce que c'est là qu'il vaut quelque chose.

**Rien ici ne touche à une API.** Les refus arrivent tous avant le premier
appel, ce qui est précisément ce qu'on leur demande : un refus qui arriverait
après aurait déjà éteint quelque chose.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parents[3]
PLAYBOOK = RACINE / "ansible_collections/stephrobert/scaleway/playbooks/power_schedule.yml"


def _jouer(*options: str) -> tuple[int, str]:
    resultat = subprocess.run(
        ["ansible-playbook", str(PLAYBOOK), *options],
        env={
            "PATH": f"/usr/bin:/bin:{RACINE}/.venv/bin",
            "HOME": os.environ.get("HOME", "/tmp"),
            "ANSIBLE_COLLECTIONS_PATH": str(RACINE),
            # Un port sans personne derrière : si un refus laissait passer, la
            # tâche qui écrit échouerait à joindre l'API plutôt que d'éteindre
            # quoi que ce soit.
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


# --- ne rien demander n'est pas une erreur --------------------------------


def test_sans_groupe_le_playbook_ne_fait_rien_et_le_dit(ansible_disponible: None) -> None:
    """C'est la convention de `stop_server.yml`, et ce qui permet à
    `mise run integration` de jouer chaque playbook livré sans argument."""
    code, sortie = _jouer()

    assert code == 0
    assert "No group named" in sortie
    assert "without touching anything" in sortie


# --- demander quelque chose d'introuvable en est une ----------------------


def test_un_groupe_nomme_et_vide_est_un_echec(ansible_disponible: None) -> None:
    """À 20:00, un planificateur qui ne trouve rien et sort en 0 échoue en
    silence, ce qui est le pire des deux."""
    code, sortie = _jouer("-e", "group=scw_tag_absent", "-e", "desired_state=off")

    assert code != 0
    assert "holds no host" in sortie
    assert "does not authorise acting on everything" in sortie


def test_un_inventaire_absent_est_nomme_comme_tel(ansible_disponible: None) -> None:
    """C'est la cause la plus probable d'un groupe vide, et la moins visible."""
    _, sortie = _jouer("-e", "group=scw_tag_absent", "-e", "desired_state=off")

    assert "No inventory was parsed" in sortie
    assert "-i <name>.scaleway.yml" in sortie


def test_un_groupe_sans_etat_desire_est_refuse(ansible_disponible: None) -> None:
    """Nommer la cible sans dire dans quel sens la déplacer n'est pas une demande."""
    code, sortie = _jouer("-e", "group=scw_tag_office_hours")

    assert code != 0
    assert "was named without" in sortie


def test_un_etat_desire_hors_des_deux_valeurs_est_refuse(ansible_disponible: None) -> None:
    code, sortie = _jouer("-e", "group=scw_tag_office_hours", "-e", "desired_state=maybe")

    assert code != 0
    assert "desired_state=on|off" in sortie


# --- ce que le playbook ne peut pas faire par construction -----------------


def test_aucune_valeur_par_defaut_ne_designe_une_cible(ansible_disponible: None) -> None:
    """Une valeur par défaut sur `group` vaudrait « tout le parc ».

    Le test lit le playbook : un défaut ajouté demain doit rougir ici, même si
    aucun scénario du jour ne l'exerce.
    """
    texte = PLAYBOOK.read_text(encoding="utf-8")
    declarations = re.search(r"\n  vars:\n(.*?)\n  tasks:", texte, flags=re.DOTALL)
    assert declarations, "la section vars du play n'est plus reconnue"

    for nom in ("group", "desired_state"):
        motif = rf'^\s+{nom}:\s*""\s*$'
        assert re.search(motif, declarations.group(1), flags=re.MULTILINE), (
            f"`{nom}` doit rester vide par défaut : une cible implicite est "
            "le mode de défaillance le plus cher de ce playbook"
        )


def _tache(chemin: Path, nom: str) -> dict:
    """La tâche portant ce nom, lue dans le YAML plutôt que cherchée au texte.

    Un `grep` sur le message rendrait vert une reformulation qui perdrait la
    distinction : c'est la structure qu'on tient, pas la présence d'une chaîne
    quelque part dans le fichier.
    """
    jeu = yaml.safe_load(chemin.read_text(encoding="utf-8"))[0]

    def _parcourir(taches: list) -> dict | None:
        for tache in taches:
            if tache.get("name") == nom:
                return tache
            trouvee = _parcourir(tache.get("block", []))
            if trouvee is not None:
                return trouvee
        return None

    tache = _parcourir(jeu["tasks"])
    assert tache is not None, f"la tâche « {nom} » a disparu du playbook"
    return tache


def test_une_seule_tache_ecrit(ansible_disponible: None) -> None:
    """Tout le reste lit. Une écriture ajoutée hors du chemin gardé rougit ici."""
    texte = PLAYBOOK.read_text(encoding="utf-8")
    appels = re.findall(r"^\s+stephrobert\.scaleway\.([a-z0-9_]+):", texte, flags=re.MULTILINE)
    assert appels, "le motif ne reconnaît plus aucun appel : il ne mesure plus rien"

    ecritures = [nom for nom in appels if not nom.endswith("_info")]
    assert ecritures == ["instance_server_action"], ecritures


def test_le_compte_rendu_distingue_une_repetition_dun_vrai_passage() -> None:
    """Une répétition qui rend compte comme un vrai passage est pire que rien.

    En mode check, le module d'action annonce le changement sans l'envoyer :
    `changed` compte alors ce qui **bougerait**. Le compte rendu disait « acted
    on », donc l'opérateur lisait que ses machines étaient éteintes pendant
    qu'elles tournaient encore. Mesuré en jouant le playbook contre l'émulateur
    du quickstart : `--check` annonçait trois extinctions, et l'inventaire
    montrait les trois machines toujours `running`.
    """
    compte_rendu = _tache(PLAYBOOK, "The result")
    message = compte_rendu["ansible.builtin.debug"]["msg"]

    assert "ansible_check_mode" in message, (
        "le compte rendu ne distingue pas une répétition d'un vrai passage : "
        "il dit avoir agi dans les deux cas"
    )
    assert "would be acted on" in message and "acted on" in message, (
        "les deux formulations doivent exister, sinon la distinction n'en est pas une"
    )
