"""Ce que le contrôle des exemples de documentation analyse, et ce qu'il enveloppe.

**Le README de la collection est ce que Galaxy publie**, donc le premier
playbook qu'un utilisateur copie, et il n'était analysé par rien : le contrôle
ne parcourait que `docs/`. Un module renommé y serait resté jusqu'à ce que
quelqu'un essaie (#134).

En l'y ajoutant, deux de ses blocs ont échoué. Le README avait raison et le
détecteur avait tort : un README publie des **tâches**, pas des jeux, et les
envoyer tels quels à `--syntax-check` les fait échouer parce qu'il leur manque
un `hosts:` que la page n'a aucune raison d'écrire.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import doc_examples

EXTRAIT_DE_TACHES = """\
- name: These tags on this server, and nothing else
  stephrobert.scaleway.instance_server:
    zone: fr-par-1
    server_id: "abc"
    tags: [production, web]
"""

JEU_COMPLET = """\
- hosts: localhost
  tasks:
    - name: Une lecture
      stephrobert.scaleway.instance_server_info:
        zone: fr-par-1
"""


def _environnement() -> dict[str, str]:
    from generator.ansible.collection import load_collection

    return {
        **os.environ,
        "ANSIBLE_COLLECTIONS_PATH": str(load_collection().collections_root),
        "ANSIBLE_LOCALHOST_WARNING": "False",
        "ANSIBLE_INVENTORY_UNPARSED_WARNING": "False",
    }


def test_le_readme_publie_est_analyse() -> None:
    """Celui que `galaxy.yml` désigne, donc celui que Galaxy sert."""
    examines = {chemin.as_posix() for chemin, _, _ in doc_examples.sources()}
    assert "ansible_collections/stephrobert/scaleway/README.md" in examines
    assert "README.md" in examines


def test_un_extrait_de_taches_est_enveloppe_avant_analyse() -> None:
    """Sans enveloppe, l'extrait échoue faute d'un `hosts:` que la page n'écrit pas.

    C'est le cas des deux blocs les plus copiés de la collection, et refuser
    ceux-là reviendrait à ne contrôler que ce qui n'a pas besoin de l'être.
    """
    with tempfile.TemporaryDirectory() as dossier:
        erreur = doc_examples.check(EXTRAIT_DE_TACHES, _environnement(), Path(dossier), "extrait")
    assert erreur == "", erreur


def test_un_jeu_complet_nest_pas_enveloppe_une_seconde_fois(tmp_path: Path) -> None:
    """`- hosts:` porte un tiret de liste, et l'oublier emboîtait un jeu dans un jeu.

    Ansible répondait alors « conflicting action statements: hosts, tasks », sur
    un bloc parfaitement valide. Trouvé en lançant le contrôle élargi.
    """
    assert doc_examples.JEU.search(JEU_COMPLET)
    erreur = doc_examples.check(JEU_COMPLET, _environnement(), tmp_path, "jeu")
    assert erreur == "", erreur


def test_un_module_inexistant_est_refuse(tmp_path: Path) -> None:
    """Le contre-exemple : le contrôle doit encore mordre.

    Sans lui, l'enveloppe pourrait rendre tout acceptable, et le contrôle
    passerait au vert en ne mesurant plus rien.
    """
    faux = EXTRAIT_DE_TACHES.replace("instance_server:", "instance_serveur_qui_nexiste_pas:")
    erreur = doc_examples.check(faux, _environnement(), tmp_path, "faux")
    assert erreur != ""


def test_la_documentation_du_depot_sanalyse() -> None:
    """Le seul test du fichier qui regarde le dépôt, et c'est voulu."""
    playbooks = doc_examples.sources()
    assert playbooks, "aucun exemple trouvé : l'extraction est cassée"
    environnement = _environnement()
    echecs = []
    with tempfile.TemporaryDirectory() as dossier:
        for chemin, index, bloc in playbooks:
            erreur = doc_examples.check(
                bloc, environnement, Path(dossier), f"{chemin.stem}-{index}"
            )
            if erreur:
                echecs.append(f"{chemin} bloc {index}")
    assert echecs == [], "\n".join(echecs)
