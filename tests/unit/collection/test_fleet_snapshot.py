"""L'instantané, et ce qu'il refuse de porter.

Comparer deux lectures demande une clé. Mesuré sur le compte réel le 13
septembre 2026 : deux machines peuvent porter le même nom dans la même zone, et
l'API rend alors deux identifiants distincts. Un instantané clé sur le nom
fusionnerait ces deux machines en une ressource qui « a changé », et le rapport
dirait le contraire de la vérité.

Ces tests tiennent la clé, le tri, et les quatre refus.
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
    / "fleet_snapshot.py"
)

MACHINE = {
    "kind": "instance",
    "id": "680a8f82-c837-4db7-8a57-baf55798fff6",
    "name": "sonde",
    "zone": "fr-par-1",
    "state": "running",
    "tags": [],
    "public_addresses": [],
    "last_change": "2026-09-13T06:10:13Z",
}

#: La seconde machine de la mesure : le **même nom**, un autre identifiant. C'est
#: le cas que le cloud réel a accepté, et celui qu'une clé sur le nom écraserait.
JUMELLE = {**MACHINE, "id": "30341ad6-6699-4114-ab46-d6a6efa4c3a4"}


def _module():
    spec = importlib.util.spec_from_file_location("fleet_snapshot", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["fleet_snapshot"] = module
    spec.loader.exec_module(module)
    return module


def _instantane(module, ressources, **reste):
    defauts = {
        "zones_measured": ["fr-par-1"],
        "captured_at": "2026-09-13T06:00:00Z",
        "collection_version": "0.8.0",
    }
    return module.fleet_snapshot(ressources, **(defauts | reste))


def test_deux_machines_du_meme_nom_restent_deux_ressources() -> None:
    """Le cas mesuré sur le compte réel, et la raison de la clé.

    Deux machines ont été créées avec le même nom dans la même zone, et l'API
    les a listées toutes les deux. Une clé sur le nom n'en garderait qu'une, ou
    les présenterait comme une seule qui a changé d'identifiant.
    """
    instantane = _instantane(_module(), [MACHINE, JUMELLE])

    assert len(instantane["resources"]) == 2
    assert {ressource["id"] for ressource in instantane["resources"]} == {
        MACHINE["id"],
        JUMELLE["id"],
    }


def test_le_meme_parc_produit_le_meme_instantane_deux_fois() -> None:
    """Sans tri, deux lectures du même parc ne se comparent pas.

    L'ordre dans lequel les zones répondent n'est pas une propriété du parc, et
    un instantané qui le porte fait apparaître des changements que personne n'a
    faits.
    """
    module = _module()

    un = _instantane(module, [MACHINE, JUMELLE])
    deux = _instantane(module, [JUMELLE, MACHINE])

    assert un == deux


def test_linstantane_porte_les_zones_muettes() -> None:
    """Rien n'a été mesuré n'est pas rien n'a été trouvé.

    Sans ce champ, un diff calculé sur une zone qui n'a pas répondu annoncerait
    la disparition de tout ce qu'elle porte.
    """
    instantane = _instantane(
        _module(), [MACHINE], zones_measured=["fr-par-1"], zones_unmeasured=["fr-par-2"]
    )

    assert instantane["zones_unmeasured"] == ["fr-par-2"]
    assert instantane["zones_measured"] == ["fr-par-1"]


def test_une_ressource_sans_cle_est_refusee() -> None:
    """Une ressource sans `kind` ou sans `id` n'est pas comparable.

    `resource_facts` refuse déjà ce cas : si une charge arrive ici sans
    identifiant, c'est qu'elle a contourné le normaliseur, et le dire vaut mieux
    que la porter.
    """
    module = _module()
    sans = {cle: valeur for cle, valeur in MACHINE.items() if cle != "id"}

    with pytest.raises(Exception, match="sans `kind` ou sans `id`"):
        _instantane(module, [sans])


def test_la_meme_ressource_lue_deux_fois_est_refusee() -> None:
    """Garder « la dernière » choisirait à la place de l'utilisateur.

    Deux ressources de même clé viennent d'une lecture répétée ou de deux
    lectures concaténées. Dans les deux cas le diff compterait faux, et un
    dédoublonnage silencieux cacherait la cause.
    """
    module = _module()

    with pytest.raises(Exception, match="deux fois"):
        _instantane(module, [MACHINE, dict(MACHINE)])


def test_deux_produits_peuvent_partager_un_identifiant() -> None:
    """Le voisin qui ne doit pas bouger : la clé est le couple, pas l'identifiant.

    Rien n'interdit à deux APIs de rendre le même identifiant, et les traiter
    comme un doublon refuserait un parc parfaitement valide.
    """
    module = _module()
    balanceur = {**MACHINE, "kind": "lb"}

    instantane = _instantane(module, [MACHINE, balanceur])

    assert len(instantane["resources"]) == 2


def test_un_instantane_dune_autre_version_est_refuse() -> None:
    """Un champ de plus d'un côté produirait des changements qui n'ont pas eu lieu."""
    module = _module()
    instantane = _instantane(module, [MACHINE]) | {"schema_version": 99}

    with pytest.raises(Exception, match="version 99"):
        module.snapshot_read(instantane)


def test_un_instantane_tronque_est_refuse() -> None:
    """Un fichier tronqué et un parc vide se ressemblent.

    Seul le second est une information, et les confondre ferait annoncer un
    parc disparu là où un fichier a été mal écrit.
    """
    module = _module()
    complet = _instantane(module, [MACHINE])
    tronque = {cle: valeur for cle, valeur in complet.items() if cle != "resources"}

    with pytest.raises(Exception, match="resources"):
        module.snapshot_read(tronque)


def test_un_instantane_relu_ressort_tel_quel() -> None:
    """Le voisin du refus : ce que la collection écrit, elle sait le relire."""
    module = _module()
    complet = _instantane(module, [MACHINE])

    assert module.snapshot_read(complet) == complet


def test_un_parc_vide_est_un_instantane_valide() -> None:
    """Zéro ressource mesurée dans une zone qui a répondu est une information.

    C'est la distinction que tout le dépôt tient : un compte vide n'est pas une
    mesure absente, et refuser l'un au nom de l'autre les confondrait.
    """
    module = _module()

    instantane = _instantane(module, [])

    assert instantane["resources"] == []
    assert module.snapshot_read(instantane) == instantane


def test_la_version_se_lit_dans_les_deux_dispositions(tmp_path, monkeypatch) -> None:
    """`galaxy.yml` dans le dépôt, `MANIFEST.json` dans une collection installée.

    `ansible-galaxy collection install` écrit le second et n'emporte pas le
    premier ; `ansible-test` et les tests du dépôt travaillent en place, où c'est
    l'inverse. Chercher un seul des deux marcherait chez celui qui l'a écrit et
    nulle part ailleurs.
    """
    module = _module()

    for nom, contenu, attendu in (
        ("galaxy.yml", "version: 1.2.3\n", "1.2.3"),
        ("MANIFEST.json", '{"collection_info": {"version": "4.5.6"}}', "4.5.6"),
    ):
        racine = tmp_path / nom.replace(".", "-")
        (racine / "plugins" / "filter").mkdir(parents=True)
        (racine / nom).write_text(contenu, encoding="utf-8")
        monkeypatch.setattr(
            module, "__file__", str(racine / "plugins" / "filter" / "fleet_snapshot.py")
        )
        assert module.collection_version() == attendu, nom


def test_une_version_introuvable_ne_sinvente_pas(tmp_path, monkeypatch) -> None:
    """`None` plutôt qu'une chaîne inventée.

    Un instantané qui mentirait sur son producteur serait pire qu'un instantané
    qui dit ne pas le savoir : la première forme se croit, la seconde se
    vérifie.
    """
    module = _module()
    (tmp_path / "plugins" / "filter").mkdir(parents=True)
    monkeypatch.setattr(
        module, "__file__", str(tmp_path / "plugins" / "filter" / "fleet_snapshot.py")
    )

    assert module.collection_version() is None


def test_un_manifeste_illisible_ne_masque_pas_lautre_source(tmp_path, monkeypatch) -> None:
    """Un fichier tronqué ne doit pas faire perdre la version qui est là.

    C'est le cas d'une installation interrompue : `MANIFEST.json` existe et n'est
    pas du JSON. Lever dessus rendrait l'instantané impossible alors que
    `galaxy.yml` répond.
    """
    module = _module()
    racine = tmp_path / "mixte"
    (racine / "plugins" / "filter").mkdir(parents=True)
    (racine / "MANIFEST.json").write_text("{ tronqu", encoding="utf-8")
    (racine / "galaxy.yml").write_text("version: 7.8.9\n", encoding="utf-8")
    monkeypatch.setattr(
        module, "__file__", str(racine / "plugins" / "filter" / "fleet_snapshot.py")
    )

    assert module.collection_version() == "7.8.9"
