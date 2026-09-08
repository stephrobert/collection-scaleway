"""Ce que le déblocage retire, et surtout ce qu'il ne retire pas.

Un run réel a laissé des ressources facturées debout : `terraform destroy`
détruit `scaleway_instance_private_nic` avant le serveur, parce que la carte
porte le `server_id`, et l'API refuse une carte attachée. Retirer les cartes
par l'API puis relancer est la séquence qui aboutit. ADR-017 porte l'incident
et son compte.

Ces tests ne touchent aucun cloud : la seule chose vraiment dangereuse du
module est le **choix** de ce qu'on supprime, et ce choix est une fonction pure.
"""

from __future__ import annotations

from typing import Any

import deblocage
import pytest

SERVEURS: list[dict[str, Any]] = [
    {"id": "s1", "name": "acs-78365a817-bastion", "zone": "fr-par-1"},
    {"id": "s2", "name": "acs-78365a817-web-1", "zone": "fr-par-1"},
    {"id": "s3", "name": "postgres-de-production", "zone": "fr-par-1"},
    {"id": "s4", "name": "acs-autre-run-web", "zone": "fr-par-1"},
]


def test_seuls_les_serveurs_de_la_plateforme_sont_retenus() -> None:
    retenus = [s["name"] for s in deblocage.serveurs_du_run(SERVEURS, "acs-78365a817")]

    assert retenus == ["acs-78365a817-bastion", "acs-78365a817-web-1"]


def test_une_machine_du_compte_nest_jamais_touchee() -> None:
    """Le contre-exemple, et c'est lui qui compte.

    Une machine sans carte réseau n'est plus jointe à son réseau privé. Un
    filtre relâché ferait de ce module un outil de destruction du compte, pas
    un outil de nettoyage d'un exercice.
    """
    retenus = deblocage.serveurs_du_run(SERVEURS, "acs-78365a817")

    assert all(s["name"] != "postgres-de-production" for s in retenus)
    assert all(s["name"] != "acs-autre-run-web" for s in retenus), (
        "le préfixe porte le run, pas la famille d'exercices"
    )


def test_un_prefixe_vide_est_refuse() -> None:
    """Sans lui, le filtre porterait sur toutes les machines du compte.

    `startswith("")` est vrai pour tout : le cas le plus dangereux est aussi
    celui qui ressemble le plus à un fonctionnement normal.
    """
    with pytest.raises(deblocage.DeblocageError, match="préfixe vide"):
        deblocage.serveurs_du_run(SERVEURS, "")


def test_une_commande_qui_echoue_nest_pas_zero_carte(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un déblocage qui ne retire rien parce que `scw` a échoué laisserait la
    destruction échouer une seconde fois, sans que personne sache pourquoi."""

    class _Echec:
        returncode = 1
        stdout = ""
        stderr = "credentials manquants"

    monkeypatch.setattr(deblocage.subprocess, "run", lambda *a, **k: _Echec())

    with pytest.raises(deblocage.DeblocageError, match="a échoué"):
        deblocage.scw(("instance", "server", "list"))


def test_les_cartes_sont_celles_des_serveurs_retenus(monkeypatch: pytest.MonkeyPatch) -> None:
    """La jointure entre les deux appels, sans réseau."""
    appels: list[tuple[str, ...]] = []

    def _scw(arguments: tuple[str, ...]) -> list[dict[str, Any]]:
        appels.append(arguments)
        if arguments[:3] == ("instance", "server", "list"):
            return SERVEURS
        return [{"id": f"nic-{arguments[-1]}"}]

    monkeypatch.setattr(deblocage, "scw", _scw)
    trouvees = deblocage.cartes("acs-78365a817")

    assert [c.identifiant for c in trouvees] == ["nic-server-id=s1", "nic-server-id=s2"]
    assert [c.serveur_nom for c in trouvees] == [
        "acs-78365a817-bastion",
        "acs-78365a817-web-1",
    ]
    assert all("s3" not in "".join(a) for a in appels), "la machine du compte n'est pas interrogée"


def test_le_deverrouillage_rend_ce_quil_a_retire(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une destruction qui a demandé un déblocage doit dire lequel.

    Rendre un compte plutôt que la liste laisserait le défaut invisible d'un run
    à l'autre : c'est ce qui doit finir dans une issue, pas dans une habitude.
    """
    carte = deblocage.Carte(zone="fr-par-1", serveur="s1", serveur_nom="bastion", identifiant="n1")
    retirees: list[deblocage.Carte] = []
    monkeypatch.setattr(deblocage, "cartes", lambda _prefixe: [carte])
    monkeypatch.setattr(deblocage, "retirer", retirees.append)

    assert deblocage.deverrouiller("acs-78365a817") == [carte]
    assert retirees == [carte]
