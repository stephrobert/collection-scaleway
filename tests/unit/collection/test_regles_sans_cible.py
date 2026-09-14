"""Une règle qui ne juge rien est un silence, pas une conformité.

Écrire `unhealthy_conditions` dans sa politique en ne lisant que des Instances
produit un rapport vert où personne n'a rien vérifié, et rien dans ce rapport ne
le dit. C'est le seul mode de défaillance qu'un audit ne peut pas se permettre :
un faux vert que son propre auteur a écrit.
"""

from __future__ import annotations

import pytest

from ansible_collections.stephrobert.scaleway.plugins.filter.audit_findings import (
    rules_without_target,
)


def test_une_regle_sans_produit_qui_la_porte_est_nommee() -> None:
    """Le refus dit la règle, le champ, et ce qu'il faudrait lire."""
    orphelines = rules_without_target(
        {"rules": {"unhealthy_conditions": {"severity": "warn"}}}, ["instance"]
    )

    assert len(orphelines) == 1
    assert "unhealthy_conditions" in orphelines[0]
    assert "k8s_node" in orphelines[0]
    assert "instance" in orphelines[0]


def test_une_regle_de_la_forme_commune_a_toujours_une_cible() -> None:
    """Tout produit lu porte `tags` : la règle juge dès qu'on lit quelque chose."""
    assert rules_without_target({"rules": {"required_tags": {"keys": ["owner"]}}}, ["lb"]) == []


def test_un_produit_qui_porte_le_champ_suffit() -> None:
    """`expires_within` vaut pour un certificat comme pour un cluster."""
    politique = {"rules": {"expires_within": {"severity": "warn", "days": 30}}}

    assert rules_without_target(politique, ["lb_certificate"]) == []
    assert rules_without_target(politique, ["k8s_cluster"]) == []
    assert rules_without_target(politique, ["instance"]) != []


def test_une_regle_inconnue_nest_pas_signalee_deux_fois() -> None:
    """`audit_findings` la refuse déjà, avec un message qui lui est propre."""
    assert rules_without_target({"rules": {"inventee": {"severity": "warn"}}}, ["instance"]) == []


def test_une_politique_sans_regle_na_rien_dorphelin() -> None:
    """Elle est refusée ailleurs, et pour une autre raison."""
    assert rules_without_target({}, ["instance"]) == []


def test_une_politique_qui_nen_est_pas_une_est_refusee() -> None:
    with pytest.raises(Exception, match="politique"):
        rules_without_target([], ["instance"])


def test_des_produits_qui_ne_sont_pas_une_liste_sont_refuses() -> None:
    """Une chaîne passerait le test d'appartenance caractère par caractère."""
    with pytest.raises(Exception, match="produits"):
        rules_without_target({"rules": {}}, "instance")
