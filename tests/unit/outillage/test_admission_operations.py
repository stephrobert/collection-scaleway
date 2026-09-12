"""« On peut le générer sûrement » et « ça sert à quelque chose » sont deux faits.

La porte d'admission répondait à la première question. Un produit dont aucun
enchaînement n'appelle les modules ajoute des noms à un README et rien à
personne, et la 0.6.0 a montré l'inverse en devenant utilisable sans un module
de plus (#213).

Ces tests portent sur la dérivation, mesurée sur des répertoires synthétiques
plutôt que sur l'état du dépôt : ce dernier est vert par construction, et un
contrôle qui le lirait passerait le jour où la dérivation cesserait de dériver.
"""

from __future__ import annotations

from pathlib import Path

import admission
import pytest

RACINE = Path(__file__).resolve().parents[3]


@pytest.fixture()
def operations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un jeu d'opérations de laboratoire, deux produits et un rôle."""
    roles = tmp_path / "roles" / "power_schedule" / "tasks"
    roles.mkdir(parents=True)
    (roles / "main.yml").write_text(
        "- name: Read\n  stephrobert.scaleway.instance_server_info:\n    zone: fr-par-1\n"
        "- name: Act\n  stephrobert.scaleway.instance_server_action:\n    zone: fr-par-1\n",
        encoding="utf-8",
    )

    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "fleet_report.yml").write_text(
        "- hosts: localhost\n  tasks:\n"
        "    - stephrobert.scaleway.instance_server_info:\n        zone: fr-par-1\n"
        "    - stephrobert.scaleway.lb_load_balancer_info:\n        zone: fr-par-1\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(admission, "OPERATIONS", (tmp_path / "roles", playbooks))
    return tmp_path


def test_une_operation_se_rattache_au_produit_quelle_appelle(operations: Path) -> None:
    """Un module nomme son produit par son préfixe, et c'est la convention du
    générateur : `lb_load_balancer_info` appartient à `lb`."""
    assert sorted(admission.operations_du_produit("instance")) == [
        "fleet_report",
        "power_schedule",
    ]
    assert sorted(admission.operations_du_produit("lb")) == ["fleet_report"]


def test_un_role_est_nomme_par_son_role_et_pas_par_son_fichier(operations: Path) -> None:
    """`tasks/main.yml` ne dit rien à personne ; `power_schedule` est ce qu'on tape."""
    assert "power_schedule" in admission.operations_du_produit("instance")
    assert "main" not in admission.operations_du_produit("instance")


def test_un_produit_sans_operation_est_admis_en_le_disant(operations: Path) -> None:
    """Refuser interdirait d'ajouter un contrat avant d'écrire l'enchaînement.

    C'est à dire interdire l'ordre dans lequel le travail se fait. Le rapport le
    dit plutôt que de le taire, et c'est la différence entre une mesure et une
    sanction.
    """
    etape = admission.etape_operations("rdb")

    assert etape.bloquante is False
    assert etape.tenue is False
    assert "aucune" in etape.detail


def test_le_depot_publie_ce_que_ses_produits_debloquent() -> None:
    """Et l'état du jour est lisible, sans être ce que les tests mesurent.

    `lb` porte des modules et ne débloque qu'un rapport qui le compte : c'est un
    constat utile, pas un défaut, et le publier est tout l'objet de l'étape.
    """
    assert admission.operations_du_produit("instance"), (
        "aucune opération pour instance : la dérivation ne dérive plus"
    )
