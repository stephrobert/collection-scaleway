"""Un audit se lance tous les jours, et c'est ce qui le rend cher quand il ment.

`rolling_reboot` sert quand on en a besoin. Un audit qui rendrait `PASS` sur un
parc qu'il n'a pas lu serait pire que pas d'audit, parce qu'il serait crédible
(#209).

Ces tests portent sur ce que l'évaluation **refuse** : une règle qu'aucun fait
ne peut trancher, une sévérité qui n'en est pas une, et une politique vide. Le
chemin le plus court vers un rapport vert ne doit pas être de vider le fichier.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]
PLUGIN = (
    RACINE
    / "ansible_collections"
    / "stephrobert"
    / "scaleway"
    / "plugins"
    / "filter"
    / "audit_findings.py"
)

MAINTENANT = "2026-09-12T12:00:00Z"

#: Un parc de laboratoire **dans la forme commune**, celle que les règles lisent.
#:
#: Elles ne connaissent aucun nom de champ d'Instance : `last_change` et pas
#: `modification_date`, `public_addresses` et pas `public_ips`. C'est ce qui
#: leur permet de valoir pour un produit qu'elles ne connaissent pas, et c'est
#: `resource_facts` qui fait la traduction (#210).
PARC = [
    {
        "kind": "instance",
        "name": "web-1",
        "zone": "fr-par-1",
        "state": "running",
        "tags": ["owner=sre", "environment=prod"],
        "public_addresses": ["51.0.0.1"],
        "last_change": "2026-09-12T11:00:00Z",
    },
    {
        "kind": "instance",
        "name": "oubliee",
        "zone": "pl-waw-1",
        "state": "stopped",
        "tags": ["role=test"],
        "public_addresses": [],
        "last_change": "2026-01-01T00:00:00Z",
    },
]


def _module():
    spec = importlib.util.spec_from_file_location("audit_findings", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["audit_findings"] = module
    spec.loader.exec_module(module)
    return module


def _juger(regles, machines=None):
    return _module().audit_findings(
        PARC if machines is None else machines,
        policy={"rules": regles},
        now=MAINTENANT,
    )


# --- ce que chaque règle voit ---------------------------------------------


def test_une_etiquette_obligatoire_manquante_est_constatee() -> None:
    """Les clés sont cherchées comme `clé=valeur`, la forme que ce parc emploie.

    La règle dit quelle clé elle cherche plutôt que de deviner une convention :
    une convention devinée est une règle que personne n'a écrite.
    """
    constats = _juger({"required_tags": {"severity": "fail", "keys": ["owner", "environment"]}})

    assert len(constats) == 1
    assert constats[0]["name"] == "instance/oubliee"
    assert constats[0]["detail"] == "missing tag: environment, owner"


def test_une_zone_hors_des_zones_permises_est_constatee() -> None:
    constats = _juger({"allowed_zones": {"severity": "fail", "zones": ["fr-par-1"]}})

    assert [constat["name"] for constat in constats] == ["instance/oubliee"]
    assert constats[0]["detail"] == "zone: pl-waw-1"


def test_une_adresse_publique_est_constatee_avec_la_severite_de_la_politique() -> None:
    """Une adresse publique n'est pas un défaut : c'est une chose à regarder.

    C'est pour ça que la sévérité est une donnée. Un bastion en a une par
    construction, une base de données pas.
    """
    constats = _juger({"public_ip": {"severity": "warn"}})

    assert len(constats) == 1
    assert constats[0]["severity"] == "warn"
    assert "51.0.0.1" in constats[0]["detail"]


def test_une_machine_arretee_depuis_longtemps_est_constatee() -> None:
    constats = _juger({"stopped_since": {"severity": "warn", "days": 30}})

    assert [constat["name"] for constat in constats] == ["instance/oubliee"]
    assert constats[0]["detail"] == "stopped for 254 day(s)"


def test_une_machine_arretee_sans_date_ressort_comme_non_jugeable() -> None:
    """Ne pas savoir n'est pas savoir que ça va.

    La machine ressort avec un constat qui dit l'absence de date, plutôt que de
    passer pour conforme parce qu'on n'a pas pu la mesurer.
    """
    constats = _juger(
        {"stopped_since": {"severity": "warn", "days": 30}},
        machines=[{"kind": "instance", "name": "sans-date", "state": "stopped", "tags": []}],
    )

    assert constats[0]["detail"] == "stopped, and no date to measure it from"


# --- ce que l'évaluation refuse -------------------------------------------


def test_une_politique_sans_regle_est_refusee() -> None:
    """Sinon le chemin le plus court vers un rapport vert est de vider le fichier."""
    with pytest.raises(Exception) as erreur:
        _module().audit_findings(PARC, policy={"rules": {}}, now=MAINTENANT)

    assert "vert sur rien" in str(erreur.value)


def test_une_regle_quaucun_fait_ne_tranche_est_refusee() -> None:
    """Une règle non évaluée rendrait « conforme » faute d'être regardée.

    Et le message nomme celles que l'issue proposait mais qui ne sont pas
    écrites, avec la raison : leur source n'a été mesurée sur aucune cible.
    """
    with pytest.raises(Exception) as erreur:
        _juger({"healthy_backend": {"severity": "fail"}})

    message = str(erreur.value)
    assert "healthy_backend" in message
    assert "aucun load balancer" in message


def test_une_severite_inconnue_est_refusee() -> None:
    with pytest.raises(Exception) as erreur:
        _juger({"public_ip": {"severity": "peut-etre"}})

    assert "ni warn ni fail" in str(erreur.value)


def test_une_regle_sans_son_parametre_est_refusee() -> None:
    """`required_tags` sans `keys` ne cherche rien, et trouverait donc tout bon."""
    with pytest.raises(Exception) as erreur:
        _juger({"required_tags": {"severity": "fail"}})

    assert "attend `keys`" in str(erreur.value)


# --- la forme du rapport ---------------------------------------------------


def test_les_constats_sont_tries() -> None:
    """Deux exécutions sur le même parc doivent produire les mêmes octets.

    Un rapport qu'on ne peut pas comparer d'un jour à l'autre ne sert pas à
    surveiller quoi que ce soit.
    """
    regles = {
        "required_tags": {"severity": "fail", "keys": ["owner"]},
        "allowed_zones": {"severity": "fail", "zones": ["fr-par-1"]},
    }
    cles = [(constat["name"], constat["rule"]) for constat in _juger(regles)]

    assert cles == sorted(cles)


def test_le_filtre_est_publie_sous_son_nom() -> None:
    assert "audit_findings" in _module().FilterModule().filters()


# --- le refus que le contrat de résultat reçoit ---------------------------


def test_un_refus_par_machine_et_pas_par_constat() -> None:
    """Le contrat compte des ressources examinées, pas des constats.

    `examined` y vaut la somme de ce qui a changé, de ce qui était conforme et
    de ce qui est refusé : passer les constats ferait compter deux fois une
    machine qui enfreint deux règles. Sur un parc où chacune n'en enfreint
    qu'une, le total tombe juste par coïncidence, et c'est la forme même d'un
    faux vert.
    """
    constats = _juger(
        {
            "required_tags": {"severity": "fail", "keys": ["owner"]},
            "allowed_zones": {"severity": "fail", "zones": ["fr-par-1"]},
        }
    )
    assert len(constats) == 2, "la machine doit enfreindre deux règles pour que ça mesure"

    refus = _module().audit_refusals(constats)
    assert len(refus) == 1, "deux constats sur une machine font un refus, pas deux"
    assert refus[0]["name"] == "instance/oubliee"
    assert refus[0]["reason"] == "allowed_zones, required_tags"
