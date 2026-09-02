"""Le filtrage côté client, et la raison rendue avec chaque écart.

Ce module ne traite que ce que l'API ne sait pas exprimer. Chaque test dit
lequel de ces cas il couvre, pour qu'on ne le confonde pas avec un filtrage
que le provider aurait dû déléguer à l'API.
"""

from __future__ import annotations

from ansible_collections.local.scaleway.plugins.module_utils.inventory.filtering import (
    Filters,
    apply,
    keep,
)
from ansible_collections.local.scaleway.plugins.module_utils.inventory.models import InventoryHost


def _host(**champs) -> InventoryHost:
    return InventoryHost(id="i-1", product="instance", name="web01", **champs)


def test_sans_filtre_tout_est_garde() -> None:
    garde, raison = keep(_host(), Filters())
    assert garde and raison == "retenue"


def test_tags_match_any_suffit_dun_tag() -> None:
    host = _host(tags=("env=prod",))
    assert keep(host, Filters(tags=("env=prod", "role=db")))[0]


def test_tags_match_all_les_exige_tous() -> None:
    """Ce que l'API ne sait pas faire : elle applique un OU."""
    host = _host(tags=("env=prod",))
    garde, raison = keep(host, Filters(tags=("env=prod", "role=db"), tags_match="all"))
    assert not garde
    assert "role=db" in raison


def test_tags_match_all_passe_quand_tous_sont_la() -> None:
    host = _host(tags=("env=prod", "role=db", "autre"))
    assert keep(host, Filters(tags=("env=prod", "role=db"), tags_match="all"))[0]


def test_une_exclusion_par_tag_prime_sur_une_inclusion() -> None:
    """Sinon `tags: [env=prod]` et `exclude.tags: [canary]` se contrediraient."""
    host = _host(tags=("env=prod", "canary"))
    garde, raison = keep(host, Filters(tags=("env=prod",), exclude_tags=("canary",)))
    assert not garde
    assert "canary" in raison


def test_une_exclusion_par_etat_ecarte_la_machine() -> None:
    garde, raison = keep(_host(state="stopped"), Filters(exclude_states=("stopped",)))
    assert not garde
    assert "stopped" in raison


def test_un_etat_demande_ecarte_les_autres() -> None:
    assert not keep(_host(state="stopped"), Filters(states=("running",)))[0]
    assert keep(_host(state="running"), Filters(states=("running",)))[0]


def test_une_machine_sans_etat_ne_passe_pas_un_filtre_detat() -> None:
    """Filtrer sur `running` ne doit pas laisser passer un état inconnu."""
    assert not keep(_host(), Filters(states=("running",)))[0]


def test_les_ecarts_sont_nommes_avec_leur_raison() -> None:
    hosts = (
        _host(tags=("env=prod",)),
        InventoryHost(id="i-2", product="instance", name="db01", tags=("canary",)),
    )
    gardes, raisons = apply(hosts, Filters(exclude_tags=("canary",)))
    assert [h.id for h in gardes] == ["i-1"]
    assert len(raisons) == 1
    assert "db01" in raisons[0] and "canary" in raisons[0]


def test_les_tags_demandes_partent_bien_vers_lapi() -> None:
    """Même en mode `all` : cela réduit déjà le transfert, l'affinage suit."""
    assert Filters(tags=("a", "b"), tags_match="all").api_tags() == ("a", "b")
