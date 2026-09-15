"""Ce qui a changé, et surtout ce dont on ne peut rien dire.

Le défaut redouté n'est pas qu'un changement manque : c'est qu'un rapport
plausible annonce la disparition d'un parc parce qu'une zone n'a pas répondu.
La moitié de ces tests porte là-dessus.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]
FILTRES = RACINE / "ansible_collections" / "stephrobert" / "scaleway" / "plugins" / "filter"


def _module():
    """Charge le filtre avec son voisin, dont il importe le lecteur."""
    for nom in ("fleet_snapshot", "fleet_diff"):
        spec = importlib.util.spec_from_file_location(nom, FILTRES / f"{nom}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[nom] = module
        spec.loader.exec_module(module)
    return sys.modules["fleet_diff"]


def _ressource(identifiant, zone=None, **reste):
    """Une ressource normalisée. `zone=` reste le mot du test, il pose la portée."""
    base = {
        "kind": "instance",
        "id": identifiant,
        "name": f"machine-{identifiant}",
        "scope": zone or "fr-par-1",
        "scope_type": "zone",
        "state": "running",
        "tags": [],
        "public_addresses": [],
        "last_change": "2026-09-13T06:00:00Z",
    }
    return base | reste


def _instantane(ressources, mesurees=("fr-par-1",), muettes=(), quand="2026-09-13T06:00:00Z"):
    return {
        "schema_version": 1,
        "captured_at": quand,
        "collection_version": "0.8.0",
        "scopes_measured": [{"type": "zone", "name": z} for z in sorted(mesurees)],
        "scopes_unmeasured": [{"type": "zone", "name": z} for z in sorted(muettes)],
        "resources": list(ressources),
    }


def test_deux_lectures_identiques_ne_disent_rien() -> None:
    """Le cas le plus fréquent, et celui qui doit coûter le moins à lire.

    Un outil récurrent qui écrit quelque chose tous les matins finit ignoré :
    c'est la règle du jalon, et elle commence ici.
    """
    module = _module()
    parc = _instantane([_ressource("a"), _ressource("b")])

    diff = module.fleet_diff(parc, after=parc)

    assert diff["new"] == []
    assert diff["removed"] == []
    assert diff["changed"] == []
    assert diff["unchanged"] == 2
    assert module.diff_verdict(diff) == "quiet"


def test_une_machine_apparue_et_une_disparue() -> None:
    module = _module()
    avant = _instantane([_ressource("a"), _ressource("b")])
    apres = _instantane([_ressource("b"), _ressource("c")])

    diff = module.fleet_diff(avant, after=apres)

    assert [r["id"] for r in diff["new"]] == ["c"]
    assert [r["id"] for r in diff["removed"]] == ["a"]
    assert diff["unchanged"] == 1
    assert module.diff_verdict(diff) == "changed"


def test_un_changement_nomme_le_champ_et_ses_deux_valeurs() -> None:
    """Un diff qui dit « a changé » sans dire quoi oblige à relire les deux."""
    module = _module()
    avant = _instantane([_ressource("a", tags=["production"])])
    apres = _instantane([_ressource("a", tags=["production", "public"])])

    diff = module.fleet_diff(avant, after=apres)

    assert diff["changed"] == [
        {
            "kind": "instance",
            "id": "a",
            "name": "machine-a",
            "fields": {
                "tags": {
                    "before": ["production"],
                    "after": ["production", "public"],
                }
            },
        }
    ]


def test_une_machine_remplacee_est_un_depart_et_une_arrivee() -> None:
    """C'est la vérité, et c'est ce que la clé de l'ADR-021 produit.

    Deux machines peuvent porter le même nom : les présenter comme une seule qui
    a changé d'identifiant ferait disparaître le remplacement du rapport.
    """
    module = _module()
    avant = _instantane([_ressource("ancienne", name="web-01")])
    apres = _instantane([_ressource("neuve", name="web-01")])

    diff = module.fleet_diff(avant, after=apres)

    assert [r["id"] for r in diff["new"]] == ["neuve"]
    assert [r["id"] for r in diff["removed"]] == ["ancienne"]
    assert diff["changed"] == []


def test_une_zone_muette_ne_fait_disparaitre_personne() -> None:
    """Le défaut que ce filtre existe pour ne pas commettre.

    Sans cette règle, un rapport parfaitement plausible annoncerait la
    disparition de tout ce que la zone porte, le matin où l'API ne répond pas.
    """
    module = _module()
    avant = _instantane(
        [_ressource("a"), _ressource("b", zone="nl-ams-1")],
        mesurees=("fr-par-1", "nl-ams-1"),
    )
    apres = _instantane([_ressource("a")], mesurees=("fr-par-1",), muettes=("nl-ams-1",))

    diff = module.fleet_diff(avant, after=apres)

    assert diff["removed"] == []
    assert diff["scopes_not_compared"] == {"zone/nl-ams-1": "did not answer in the later snapshot"}
    assert diff["resources_not_compared"] == 1
    assert module.diff_verdict(diff) == "action_required"


def test_une_zone_quon_a_cesse_de_lire_ne_fait_disparaitre_personne() -> None:
    """Le cas qui se voit le moins, et qui produit le même faux rapport.

    Elle n'apparaît dans aucun `scopes_unmeasured`, puisque personne n'a échoué à
    la lire : on ne l'a simplement pas demandée. Sans cette règle, tout ce
    qu'elle porte passerait pour supprimé.
    """
    module = _module()
    avant = _instantane(
        [_ressource("a"), _ressource("b", zone="nl-ams-1")],
        mesurees=("fr-par-1", "nl-ams-1"),
    )
    apres = _instantane([_ressource("a")], mesurees=("fr-par-1",))

    diff = module.fleet_diff(avant, after=apres)

    assert diff["removed"] == []
    assert diff["scopes_not_compared"] == {"zone/nl-ams-1": "not read in the later snapshot"}


def test_une_zone_lue_seulement_aujourdhui_ne_cree_personne() -> None:
    """Le symétrique : élargir la lecture n'est pas une vague de créations."""
    module = _module()
    avant = _instantane([_ressource("a")], mesurees=("fr-par-1",))
    apres = _instantane(
        [_ressource("a"), _ressource("b", zone="nl-ams-1")],
        mesurees=("fr-par-1", "nl-ams-1"),
    )

    diff = module.fleet_diff(avant, after=apres)

    assert diff["new"] == []
    assert diff["scopes_not_compared"] == {"zone/nl-ams-1": "not read in the earlier snapshot"}


def test_un_horodatage_qui_bouge_seul_est_compte_a_part() -> None:
    """Ni un changement sur lequel agir, ni une absence de changement.

    Mesuré sur le compte réel : la date ne bouge pas d'elle-même sur une machine
    stable. Qu'elle ait bougé dit donc que quelque chose a changé hors de ce que
    cette forme observe, et le noyer dans les inchangées perdrait l'information.
    """
    module = _module()
    avant = _instantane([_ressource("a", last_change="2026-09-13T06:00:00Z")])
    apres = _instantane([_ressource("a", last_change="2026-09-13T09:00:00Z")])

    diff = module.fleet_diff(avant, after=apres)

    assert diff["changed"] == []
    assert diff["unchanged"] == 0
    assert diff["changed_outside_this_shape"] == 1
    # Il ne suffit pas à rendre le rapport intéressant : rien n'est actionnable.
    assert module.diff_verdict(diff) == "quiet"


def test_comparer_deux_formes_differentes_est_refuse() -> None:
    """Un champ de plus d'un côté produirait des changements qui n'ont pas eu lieu."""
    module = _module()
    parc = _instantane([_ressource("a")])

    with pytest.raises(Exception, match="version 2"):
        module.fleet_diff(parc, after=parc | {"schema_version": 2})


def test_comparer_un_instantane_tronque_est_refuse() -> None:
    """Un fichier tronqué et un parc vide se ressemblent."""
    module = _module()
    parc = _instantane([_ressource("a")])
    tronque = {cle: valeur for cle, valeur in parc.items() if cle != "scopes_measured"}

    with pytest.raises(Exception, match="scopes_measured"):
        module.fleet_diff(tronque, after=parc)


def test_un_parc_vide_des_deux_cotes_est_calme_et_non_muet() -> None:
    """Zéro ressource dans une zone qui a répondu est une information.

    C'est le voisin du refus : rien n'a changé, et rien n'a manqué non plus.
    """
    module = _module()
    vide = _instantane([])

    diff = module.fleet_diff(vide, after=vide)

    assert diff["unchanged"] == 0
    assert diff["scopes_not_compared"] == {}
    assert module.diff_verdict(diff) == "quiet"
