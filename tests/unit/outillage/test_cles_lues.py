"""Ce que la porte des clés lues attrape, et ce qu'elle avoue ne pas savoir lire.

Un correctif du parser a renommé la clé rendue par les modules `*_type_info`,
de `result` vers `servers` et `volumes`. Le playbook affirmait toujours `types.result is
defined`. `mise run check` est resté vert, `mise run sanity` aussi, et c'est le
job `Plateforme d'exemple` qui a rougi, plusieurs minutes après la poussée
(#161).

Ces tests portent sur le cas exact qui est passé.
"""

from __future__ import annotations

from pathlib import Path

import cles_lues

PLAYBOOK_JUSTE = """\
- hosts: localhost
  tasks:
    - name: Les types offerts
      stephrobert.scaleway.instance_server_type_info:
        zone: fr-par-1
      register: types

    - name: Ce que le contrat nomme
      ansible.builtin.assert:
        that:
          - types.servers is defined
"""

PLAYBOOK_PERIME = PLAYBOOK_JUSTE.replace("types.servers", "types.result")


def _ecrire(dossier: Path, contenu: str) -> Path:
    chemin = dossier / "modules.yml"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_une_cle_que_le_module_ne_publie_pas_est_refusee(tmp_path: Path) -> None:
    """La régression exacte, rejouée.

    `instance_server_type_info` publie `servers` depuis que l'enveloppe en map
    est lue ; `types.result` n'existe plus.
    """
    fautives, _ = cles_lues.examiner(_ecrire(tmp_path, PLAYBOOK_PERIME))

    assert len(fautives) == 1
    assert "types.result" in fautives[0]
    assert "instance_server_type_info" in fautives[0]
    assert "servers" in fautives[0], "le refus doit dire ce que le module publie"


def test_la_cle_que_le_module_publie_passe(tmp_path: Path) -> None:
    """Le contre-exemple, sans lequel la porte refuserait tout playbook."""
    fautives, _ = cles_lues.examiner(_ecrire(tmp_path, PLAYBOOK_JUSTE))

    assert fautives == []


def test_les_cles_quansible_ajoute_ne_sont_pas_refusees(tmp_path: Path) -> None:
    """`resultat is changed` et `resultat.msg` ne viennent d'aucun `RETURN`.

    Les refuser ferait une porte qu'on désactive au premier playbook réel.
    """
    contenu = PLAYBOOK_JUSTE.replace(
        "          - types.servers is defined",
        "          - types.servers is defined\n"
        "          - types is not changed\n"
        "          - types.msg is not defined",
    )

    fautives, _ = cles_lues.examiner(_ecrire(tmp_path, contenu))

    assert fautives == []


def test_les_cles_derreur_du_runtime_ne_sont_pas_refusees(tmp_path: Path) -> None:
    """`resultat.api_type` vient de `ScalewayApiError.details()`, pas du `RETURN`.

    Elles sont lues dans le code du runtime, jamais recopiées ici : une seconde
    liste vieillirait, et la porte refuserait alors une lecture légitime.
    """
    contenu = PLAYBOOK_JUSTE.replace(
        "          - types.servers is defined",
        "          - types.servers is defined\n          - types.api_type is not defined",
    )

    fautives, _ = cles_lues.examiner(_ecrire(tmp_path, contenu))

    assert fautives == []
    assert "api_type" in cles_lues.erreur_du_runtime()


def test_un_index_calcule_est_compte_et_nomme(tmp_path: Path) -> None:
    """Ce que la porte n'a pas su lire ne compte pas comme vérifié.

    C'est la différence entre une porte et une décoration, et le dépôt a déjà
    payé pour l'apprendre.
    """
    contenu = PLAYBOOK_JUSTE.replace(
        "          - types.servers is defined",
        "          - types[nom_calcule] is defined",
    )

    fautives, illisibles = cles_lues.examiner(_ecrire(tmp_path, contenu))

    assert fautives == [], "une expression illisible n'est pas une faute"
    assert len(illisibles) == 1
    assert "types" in illisibles[0]


def test_une_variable_enregistree_hors_de_la_collection_est_ignoree(tmp_path: Path) -> None:
    """Ce contrôle ne sait rien des clés que `ansible.builtin.command` publie.

    Prétendre le contraire ferait un refus sur ce qu'il ne comprend pas, ce qui
    est la façon la plus sûre de le faire désactiver.
    """
    contenu = """\
- hosts: localhost
  tasks:
    - name: Autre chose
      ansible.builtin.command: /bin/true
      register: autre

    - name: Une clé que ce contrôle ne connaît pas
      ansible.builtin.assert:
        that:
          - autre.une_cle_inconnue is defined
"""

    fautives, _ = cles_lues.examiner(_ecrire(tmp_path, contenu))

    assert fautives == []


def test_lexemple_du_depot_ne_lit_que_des_cles_publiees() -> None:
    """Ce que la porte dit du dépôt aujourd'hui.

    Le seul test du fichier qui le regarde : les autres prouvent qu'elle sait
    refuser et laisser passer.
    """
    fichiers = cles_lues.playbooks()
    assert fichiers, "aucun playbook examiné : le contrôle ne mesure plus rien"

    fautives = [ligne for chemin in fichiers for ligne in cles_lues.examiner(chemin)[0]]

    assert fautives == [], "\n".join(fautives)
