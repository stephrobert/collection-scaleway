"""Un produit connu d'une couture et inconnu des autres est un trou.

**Trois des six P0 d'un audit externe du 15 septembre 2026 étaient le même
défaut** : Kubernetes avait été ajouté à `fleet_audit` et à `resource_facts`, et
pas au reste. Rien ne le disait, parce que rien ne le regardait.

```text
#272  fleet_audit ne transmettait que les zones Instance,
      donc un constat Kapsule ne pouvait jamais devenir « résolu »
#273  le schéma parlait de `zones` là où Kapsule a des régions
#274  fleet_report ne lisait pas Kapsule, donc l'instantané l'ignorait
```

Une liste de contrôle dans un document n'aurait rien empêché : personne ne la
relit en ajoutant un produit. Ce fichier la rend exécutable, et il dérive la
liste des produits de `resource_facts`, seule source : ajouter un normaliseur
fait rougir tout ce qui ne suit pas.

ADR-023 porte la décision et sa date.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ansible_collections.stephrobert.scaleway.plugins.filter.resource_facts import (
    NORMALISEURS,
    SUPPLEMENTS,
)

COLLECTION = Path(__file__).resolve().parents[3] / "ansible_collections/stephrobert/scaleway"

#: Les produits qu'un consommateur a le droit d'ignorer, et pourquoi.
#:
#: **Une exemption, pas un oubli.** Chaque ligne dit ce qui la fermerait, comme
#: les exemptions de couverture d'exemple : c'est ce qui distingue une décision
#: d'un trou, et c'est la seule chose qui empêche cette garde de devenir une
#: case à cocher.
#:
#: Vide aujourd'hui, et c'est le but : chaque produit normalisé est connu de
#: tous les consommateurs. La table existe pour que la première exemption doive
#: s'écrire, pas pour qu'on la remplisse.
EXEMPTIONS: dict[tuple[str, str], str] = {}


def _produits() -> tuple[str, ...]:
    """Les produits que la collection sait normaliser, seule source de vérité."""
    return tuple(sorted(NORMALISEURS))


def test_chaque_produit_normalise_declare_ses_champs() -> None:
    """Un normaliseur sans supplément déclaré rend une forme que rien ne décrit.

    Les deux tables vivent côte à côte et se contrediraient : un produit ajouté
    à l'une et pas à l'autre rendrait des champs qu'aucune règle ne sait juger,
    ou en promettrait qu'il ne porte pas.
    """
    assert set(NORMALISEURS) == set(SUPPLEMENTS), sorted(set(NORMALISEURS) ^ set(SUPPLEMENTS))


@pytest.mark.parametrize("produit", _produits())
def test_chaque_produit_normalise_sait_se_selectionner(produit: str) -> None:
    """`select_resources` doit savoir ce qu'un critère nomme sur ce produit.

    Sans table, la sélection chercherait un champ qui n'existe pas, donc ne
    désignerait rien, donc se lirait comme un parc vide : la panne la plus
    silencieuse qu'une opération puisse avoir.
    """
    from ansible_collections.stephrobert.scaleway.plugins.filter.select_resources import (
        CHAMPS,
    )

    if raison := EXEMPTIONS.get(("select_resources", produit)):
        assert produit not in CHAMPS, (
            f"`{produit}` est exempté de `select_resources` avec cette raison : "
            f"{raison}. Il y figure désormais : retirer l'exemption."
        )
        return
    assert produit in CHAMPS, (
        f"`{produit}` est normalisé et `select_resources` ne sait pas ce qu'un "
        "critère y nomme. L'ajouter, ou l'exempter avec sa raison."
    )


@pytest.mark.parametrize("produit", _produits())
def test_chaque_champ_propre_est_compare_ou_declare_temoin(produit: str) -> None:
    """Un champ qu'un produit seul porte doit être comparé, ou nommé témoin.

    Sans ça, un cluster qui passe de 1.36 à 1.37 sortait en
    `changed_outside_this_shape` : le diff voyait que quelque chose avait bougé
    et ne disait pas quoi, sur le changement le plus important d'un cluster
    managé.
    """
    from ansible_collections.stephrobert.scaleway.plugins.filter.fleet_diff import (
        TEMOINS,
        _champs_a_comparer,
    )

    compares = set(_champs_a_comparer(produit))
    for champ in SUPPLEMENTS[produit]:
        assert champ in compares or champ in TEMOINS, (
            f"`{produit}.{champ}` n'est ni comparé ni déclaré témoin. Un "
            "changement dessus sortirait sans que rien ne dise lequel."
        )


def test_la_forme_commune_porte_une_portee_typee() -> None:
    """Une portée sans type ne se compare à rien.

    `fr-par` est une région et `fr-par-1` une zone : les deux chaînes se
    ressemblent assez pour qu'un rapport les confonde, et rien dans la chaîne ne
    permet de les distinguer (#273).
    """
    from ansible_collections.stephrobert.scaleway.plugins.filter.resource_facts import (
        CHAMPS,
    )

    assert "scope" in CHAMPS
    assert "scope_type" in CHAMPS
    assert "zone" not in CHAMPS, (
        "`zone` est le vocabulaire d'un produit, pas celui de la forme commune : "
        "un cluster vit dans une région."
    )


@pytest.mark.parametrize("produit", _produits())
def test_chaque_normaliseur_pose_une_portee_typee(produit: str) -> None:
    """Le type vient de ce qu'on a interrogé, jamais de la forme du nom.

    Deviner par la forme marcherait aujourd'hui sur Scaleway et casserait au
    premier produit dont le nommage diffère.
    """
    from ansible_collections.stephrobert.scaleway.plugins.filter import resource_facts

    source = ast.parse(Path(resource_facts.__file__).read_text(encoding="utf-8"))
    fonction = next(
        noeud
        for noeud in ast.walk(source)
        if isinstance(noeud, ast.FunctionDef) and noeud.name == f"_{produit}"
    )
    poses = {
        cle.value
        for noeud in ast.walk(fonction)
        if isinstance(noeud, ast.Dict)
        for cle in noeud.keys
        if isinstance(cle, ast.Constant)
    }

    assert {"scope", "scope_type"} <= poses, (
        f"le normaliseur `{produit}` ne pose pas sa portée typée : "
        f"{sorted({'scope', 'scope_type'} - poses)}"
    )


def test_les_roles_qui_lisent_un_produit_le_declarent() -> None:
    """Un rôle qui lit un produit sans option pour le demander décide de la facture.

    Chaque produit est une famille d'appels sur un compte facturé. `fleet_audit`
    et `fleet_report` portent donc tous deux une option `products`, et c'est ce
    qui empêche un rapport de sortir une région muette sur un compte sans
    cluster.
    """
    for role in ("fleet_audit", "fleet_report"):
        defauts = (COLLECTION / "roles" / role / "defaults" / "main.yml").read_text(
            encoding="utf-8"
        )
        assert f"scaleway_{role}_products:" in defauts, (
            f"`{role}` lit des produits sans option pour dire lesquels"
        )
