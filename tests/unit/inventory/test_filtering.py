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


def test_une_organisation_demandee_ecarte_les_autres() -> None:
    """L'option existait, traversait toute la chaîne, et ne filtrait rien.

    Elle entrait même dans la clé de cache. Une option documentée qui ne fait
    rien est pire qu'une option absente : quelqu'un construit dessus, et
    l'inventaire qu'il croit restreint ne l'est pas.
    """
    garde, raison = keep(_host(organization_id="org-1"), Filters(organizations=("org-2",)))
    assert not garde
    assert "org-1" in raison and "org-2" in raison

    assert keep(_host(organization_id="org-2"), Filters(organizations=("org-2",)))[0]


def test_sans_organisation_demandee_rien_nest_ecarte() -> None:
    """Le contre-exemple, sans lequel le test ci-dessus passerait aussi sur une
    fonction qui refuserait tout."""
    assert keep(_host(organization_id="org-1"), Filters())[0]
    assert keep(_host(), Filters())[0]


def test_en_mode_any_plusieurs_tags_ne_partent_pas_a_lapi() -> None:
    """L'API Instance applique un ET, pas un OU : trois sources concordantes.

    Demander deux tags à l'API en mode `any`, qui est le défaut, ne rendait que
    les machines portant les deux. Une machine ne portant que le premier
    n'était jamais téléchargée, et le filtrage local ne peut pas récupérer ce
    qu'il n'a pas reçu.
    """
    assert Filters(tags=("a", "b"), tags_match="any").api_tags() == ()


def test_un_seul_tag_part_toujours_a_lapi() -> None:
    """Avec un seul tag les deux modes coïncident : autant ne pas transférer."""
    assert Filters(tags=("a",), tags_match="any").api_tags() == ("a",)
    assert Filters(tags=("a",), tags_match="all").api_tags() == ("a",)


def test_en_mode_all_les_tags_partent_a_lapi() -> None:
    """Le ET de l'API est exactement ce que `all` demande."""
    assert Filters(tags=("a", "b"), tags_match="all").api_tags() == ("a", "b")
