"""Les règles de #252, sur des champs déjà traversés et lus par personne.

Chaque valeur employée ici est relevée dans la transcription réelle du
14 septembre 2026 (`transcriptions/kapsule-2026-09-14.jsonl`), pas déduite d'un
contrat. La distinction n'est pas théorique : `conditions` est rendu par l'API et
absent du contrat `scaleway.k8s.v1.Node`.
"""

from __future__ import annotations

import pytest

from ansible_collections.stephrobert.scaleway.plugins.filter.audit_findings import (
    audit_findings,
)
from ansible_collections.stephrobert.scaleway.plugins.filter.resource_facts import (
    resource_facts,
)

MAINTENANT = "2026-09-14T10:00:00Z"


def _juger(faits: list[dict], regles: dict) -> list[dict]:
    return audit_findings(faits, policy={"rules": regles}, now=MAINTENANT)


def _machine(**reste: object) -> dict:
    """Une charge utile Instance, telle que l'API la rend."""
    return {
        "id": "b20294e8-d0b9-471e-a78f-bbce79e7ca74",
        "name": "web-1",
        "zone": "fr-par-1",
        "state": "running",
        "tags": [],
        "maintenances": [],
        "end_of_service": False,
        "allowed_actions": ["poweroff", "reboot", "backup"],
        **reste,
    }


def _faits_instance(**reste: object) -> list[dict]:
    return resource_facts([_machine(**reste)], kind="instance")


# ---- Le moteur saute ce dont la règle ne parle pas ------------------------


def test_un_produit_qui_ne_porte_pas_le_champ_nest_pas_juge_conforme() -> None:
    """**Il n'est pas jugé du tout.**

    Un cluster n'a pas d'action permise. Le compter comme conforme gonflerait le
    `PASS` de ressources que personne n'a regardées.
    """
    grappes = resource_facts(
        [{"id": "c-1", "name": "prod", "region": "fr-par", "version": "1.37.0"}],
        kind="k8s_cluster",
    )

    constats = _juger(grappes, {"required_actions": {"severity": "warn", "actions": ["reboot"]}})

    assert constats == []


# ---- Maintenance planifiée ------------------------------------------------


def test_une_machine_sans_maintenance_ne_produit_rien() -> None:
    """Mesuré : le champ vaut `[]` sur une machine saine."""
    assert _juger(_faits_instance(), {"planned_maintenance": {"severity": "warn"}}) == []


def test_une_maintenance_prevue_ressort_avec_son_compte() -> None:
    faits = _faits_instance(maintenances=[{"reason": "hypervisor"}])

    constats = _juger(faits, {"planned_maintenance": {"severity": "warn"}})

    assert len(constats) == 1
    assert "1 planned maintenance window(s)" in constats[0]["detail"]


def test_une_fenetre_sans_date_nest_pas_une_fenetre_lointaine() -> None:
    """La taire la ferait passer pour absente."""
    faits = _faits_instance(maintenances=[{"reason": "hypervisor"}])

    constats = _juger(faits, {"planned_maintenance": {"severity": "warn", "within_days": 7}})

    assert "no start date" in constats[0]["detail"]


def test_une_maintenance_lointaine_nappelle_pas_la_meme_chose_quune_proche() -> None:
    faits = _faits_instance(maintenances=[{"start_date": "2027-01-01T00:00:00Z"}])

    assert _juger(faits, {"planned_maintenance": {"severity": "warn", "within_days": 7}}) == []


# ---- Fin de service -------------------------------------------------------


def test_un_type_commercial_en_fin_de_service_ressort() -> None:
    """La machine tourne et continuera ; elle ne se recrée plus."""
    faits = _faits_instance(end_of_service=True)

    constats = _juger(faits, {"end_of_service": {"severity": "warn"}})

    assert len(constats) == 1
    assert "end of service" in constats[0]["detail"]


def test_une_fin_de_service_non_lue_nest_pas_une_bonne_nouvelle() -> None:
    faits = _faits_instance()
    faits[0]["end_of_service"] = None

    constats = _juger(faits, {"end_of_service": {"severity": "warn"}})

    assert "was not read" in constats[0]["detail"]


# ---- Actions permises -----------------------------------------------------


def test_une_action_attendue_et_non_permise_ressort() -> None:
    """Mesuré : une machine arrêtée rend `["stop_in_place", "backup"]`."""
    faits = _faits_instance(state="stopped", allowed_actions=["stop_in_place", "backup"])

    constats = _juger(faits, {"required_actions": {"severity": "warn", "actions": ["poweron"]}})

    assert "cannot: poweron" in constats[0]["detail"]


def test_une_regle_dactions_sans_actions_est_refusee() -> None:
    """Sans elles, la règle supposerait ce qu'un parc attend de ses machines."""
    with pytest.raises(Exception, match="`actions`"):
        _juger(_faits_instance(), {"required_actions": {"severity": "warn"}})


# ---- Mise à jour offerte --------------------------------------------------


def _grappe(**reste: object) -> list[dict]:
    charge = {
        "id": "c-1",
        "name": "prod",
        "region": "fr-par",
        "status": "ready",
        "version": "1.37.0",
        "upgrade_available": False,
        **reste,
    }
    return resource_facts([charge], kind="k8s_cluster")


def test_une_mise_a_jour_offerte_ressort_sans_etre_appliquee() -> None:
    """Détecter puis diagnostiquer, jamais détecter puis modifier."""
    constats = _juger(_grappe(upgrade_available=True), {"upgrade_available": {"severity": "warn"}})

    assert len(constats) == 1
    assert "an upgrade is available" in constats[0]["detail"]


def test_une_mise_a_jour_non_lue_nest_pas_une_absence_de_mise_a_jour() -> None:
    grappe = _grappe()
    grappe[0]["upgrade_available"] = None

    constats = _juger(grappe, {"upgrade_available": {"severity": "warn"}})

    assert "was not read" in constats[0]["detail"]


# ---- Échéance, pour deux objets et une seule règle ------------------------

#: Le catalogue tel que `ListVersions` le rend, relevé le 14 septembre 2026.
CATALOGUE = [
    {
        "name": "1.37.0",
        "deprecated_at": "2027-08-28T00:00:00Z",
        "end_of_life_at": "2027-10-28T00:00:00Z",
    },
    {
        "name": "1.36.4",
        "deprecated_at": "2027-07-07T00:00:00Z",
        "end_of_life_at": "2027-09-07T00:00:00Z",
    },
    {
        "name": "1.34.11",
        "deprecated_at": "2026-09-29T00:00:00Z",
        "end_of_life_at": "2026-11-29T00:00:00Z",
    },
]


def test_un_certificat_qui_expire_bientot_ressort() -> None:
    """Mesuré : `not_valid_after` valait le lendemain du run."""
    faits = resource_facts(
        [
            {
                "id": "cert-1",
                "name": "www",
                "lb": {"zone": "fr-par-1"},
                "status": "ready",
                "not_valid_after": "2026-09-15T10:55:24Z",
            }
        ],
        kind="lb_certificate",
    )

    constats = _juger(faits, {"expires_within": {"severity": "fail", "days": 30}})

    assert "expires in 1 day(s)" in constats[0]["detail"]


def test_un_cluster_porte_lecheance_de_la_version_quil_fait_tourner() -> None:
    """La même question posée à deux objets, et une seule règle pour y répondre."""
    faits = resource_facts(
        [{"id": "c-1", "name": "prod", "region": "fr-par", "version": "1.34.11"}],
        kind="k8s_cluster",
        context={"versions": CATALOGUE},
    )

    constats = _juger(faits, {"expires_within": {"severity": "warn", "days": 90}})

    assert "2026-11-29" in constats[0]["detail"]


def test_une_echeance_absente_nest_pas_une_echeance_lointaine() -> None:
    """Un cluster dont la version n'est pas au catalogue sort non jugeable."""
    faits = resource_facts(
        [{"id": "c-1", "name": "prod", "region": "fr-par", "version": "1.99.0"}],
        kind="k8s_cluster",
        context={"versions": CATALOGUE},
    )

    constats = _juger(faits, {"expires_within": {"severity": "warn", "days": 90}})

    assert "nothing says when this expires" in constats[0]["detail"]


def test_une_echeance_deja_passee_le_dit() -> None:
    faits = resource_facts(
        [
            {
                "id": "cert-1",
                "name": "vieux",
                "lb": {"zone": "fr-par-1"},
                "not_valid_after": "2026-09-01T00:00:00Z",
            }
        ],
        kind="lb_certificate",
    )

    constats = _juger(faits, {"expires_within": {"severity": "fail", "days": 30}})

    assert "expired 13 day(s) ago" in constats[0]["detail"]


# ---- Retard de version (#243) ---------------------------------------------


def test_le_retard_se_compte_depuis_le_catalogue() -> None:
    """Le retard se mesure, il ne s'estime pas."""
    faits = resource_facts(
        [{"id": "c-1", "name": "prod", "region": "fr-par", "version": "1.34.11"}],
        kind="k8s_cluster",
        context={"versions": CATALOGUE},
    )

    constats = _juger(faits, {"version_drift": {"severity": "warn", "max_minor_behind": 1}})

    assert "3 minor version(s) behind" in constats[0]["detail"]


def test_un_cluster_a_jour_ne_produit_rien() -> None:
    faits = resource_facts(
        [{"id": "c-1", "name": "prod", "region": "fr-par", "version": "1.37.0"}],
        kind="k8s_cluster",
        context={"versions": CATALOGUE},
    )

    assert _juger(faits, {"version_drift": {"severity": "warn", "max_minor_behind": 1}}) == []


def test_un_retard_inconnu_nest_pas_un_cluster_a_jour() -> None:
    """Sans catalogue lu, le compte n'existe pas ; il ne vaut pas zéro."""
    faits = resource_facts(
        [{"id": "c-1", "name": "prod", "region": "fr-par", "version": "1.34.11"}],
        kind="k8s_cluster",
    )

    constats = _juger(faits, {"version_drift": {"severity": "warn", "max_minor_behind": 1}})

    assert "nothing read says how far behind" in constats[0]["detail"]


def test_une_majeure_differente_ne_se_compte_pas_en_mineures() -> None:
    """**Une majeure d'écart n'est pas « quelques mineures de plus ».**

    C'est une autre question, et la compter dans le même nombre la ferait
    disparaître : un cluster en `2.1.0` face à un catalogue en `1.x` sortirait
    avec un retard négatif, donc « à jour », ce qui est exactement faux.
    """
    faits = resource_facts(
        [{"id": "c-1", "name": "prod", "region": "fr-par", "version": "2.1.0"}],
        kind="k8s_cluster",
        context={"versions": CATALOGUE},
    )

    constats = _juger(faits, {"version_drift": {"severity": "warn", "max_minor_behind": 1}})

    assert len(constats) == 1
    assert "nothing read says how far behind" in constats[0]["detail"]


def test_une_version_illisible_ne_produit_pas_un_retard_faux() -> None:
    """Lire `(0, 0)` ferait compter un retard énorme et parfaitement faux.

    La garde qui mord ici est celle de la majeure, éprouvée juste au-dessus :
    une version illisible ne partage sa majeure avec personne. Les deux replis
    de `_minorielle` sont des ceintures par-dessus cette bretelle, et
    `/falsify` l'a dit en laissant ce test vert quand on les neutralisait.
    """
    faits = resource_facts(
        [{"id": "c-1", "name": "prod", "region": "fr-par", "version": "stable"}],
        kind="k8s_cluster",
        context={"versions": CATALOGUE},
    )

    constats = _juger(faits, {"version_drift": {"severity": "warn", "max_minor_behind": 1}})

    assert "nothing read says how far behind" in constats[0]["detail"]


def test_une_regle_de_retard_sans_seuil_est_refusee() -> None:
    faits = resource_facts(
        [{"id": "c-1", "name": "prod", "region": "fr-par", "version": "1.37.0"}],
        kind="k8s_cluster",
    )

    with pytest.raises(Exception, match="max_minor_behind"):
        _juger(faits, {"version_drift": {"severity": "warn"}})


# ---- Conditions de santé, mesurées et non contractées ---------------------


def _noeud(**reste: object) -> list[dict]:
    charge = {
        "id": "n-1",
        "name": "scw-prod-default-1",
        "region": "fr-par",
        "status": "ready",
        "conditions": {
            "DiskPressure": "False",
            "MemoryPressure": "False",
            "NetworkUnavailable": "False",
            "PIDPressure": "False",
            "Ready": "True",
        },
        **reste,
    }
    return resource_facts([charge], kind="k8s_node")


def test_un_noeud_sain_ne_produit_rien() -> None:
    """Mesuré : l'API rend des chaînes `"True"` et `"False"`, pas des booléens."""
    assert _juger(_noeud(), {"unhealthy_conditions": {"severity": "warn"}}) == []


def test_une_condition_mauvaise_ressort_nommee() -> None:
    conditions = {"Ready": "True", "DiskPressure": "True", "MemoryPressure": "False"}

    constats = _juger(_noeud(conditions=conditions), {"unhealthy_conditions": {"severity": "fail"}})

    assert "unhealthy: DiskPressure=True" in constats[0]["detail"]


def test_des_conditions_absentes_ne_valent_pas_un_noeud_sain() -> None:
    """**Le refus central de cette règle.**

    `conditions` est rendu par l'API et absent du contrat. Le jour où l'amont
    cesserait de le rendre, aucun golden ne rougirait, et une règle qui lirait
    l'absence comme une bonne nouvelle annoncerait un parc sain sur zéro champ
    lu.
    """
    constats = _juger(_noeud(conditions=None), {"unhealthy_conditions": {"severity": "warn"}})

    assert len(constats) == 1
    assert "not the same as being healthy" in constats[0]["detail"]


def test_une_condition_que_lamont_retire_ne_fait_pas_rougir_un_parc_sain() -> None:
    """Le jeu de conditions varie d'une version à l'autre."""
    conditions = {"Ready": "True", "DiskPressure": "False"}

    politique = {"unhealthy_conditions": {"severity": "warn"}}

    assert _juger(_noeud(conditions=conditions), politique) == []


def test_les_attentes_de_sante_sont_une_donnee() -> None:
    """Un parc peut tolérer ce qu'un autre refuse."""
    conditions = {"Ready": "True", "DiskPressure": "True"}
    politique = {"unhealthy_conditions": {"severity": "warn", "conditions": {"Ready": "True"}}}

    assert _juger(_noeud(conditions=conditions), politique) == []
