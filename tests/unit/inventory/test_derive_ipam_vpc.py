"""La jointure lit-elle encore des champs que l'API déclare, par des méthodes que le SDK porte ?

L'inventaire dynamique appelle six APIs. Deux, `instance.v1` et `lb.v1`, ont un
contrat versionné, un golden et un rapport strict. Les quatre autres n'avaient
rien, et ce sont pourtant `ipam.v1` et `vpc.v2` qui portent la jointure donnant
son adresse privée à chaque machine.

Le défaut est silencieux par construction : `discovery.py` lit ces champs par
`getattr(objet, "nom", None)`, donc un champ renommé en amont ne lève pas, il
rend `None`. La jointure produit alors des machines avec un réseau, une adresse
MAC et **aucune adresse**, et l'inventaire un parc muet.

Trois contrôles, et le troisième est celui qui empêche les deux autres de
vieillir :

* chaque champ déclaré ici existe dans le contrat versionné, `suivis/` ;
* chaque méthode que la jointure appelle existe dans le SDK installé ;
* le code ne lit **rien** que cette déclaration n'ait prévu.

Sans le dernier, la déclaration serait une copie qui se décorrèle du code au
premier ajout, et les tests resteraient verts sur une jointure qu'ils ne
mesurent plus. Les noms de méthodes ne sont d'ailleurs pas écrits ici : ils sont
**lus dans le code**, parce qu'une liste recopiée à la main est exactement le
défaut que ce fichier existe pour empêcher.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SUIVIS = REPO_ROOT / "specs" / "scaleway" / "suivis"
DISCOVERY = (
    REPO_ROOT
    / "ansible_collections/stephrobert/scaleway/plugins/module_utils/inventory/discovery.py"
)

# Ce que la jointure lit, par contrat et par schéma. Le nom court est celui du
# suffixe : le contrat les préfixe tous par `scaleway.<produit>.<version>.`.
CHAMPS_LUS: dict[tuple[str, str], tuple[str, ...]] = {
    ("ipam.v1", "IP"): ("address", "is_ipv6", "resource", "source"),
    ("ipam.v1", "Resource"): ("id", "mac_address"),
    ("ipam.v1", "Source"): ("private_network_id", "vpc_id"),
    ("vpc.v2", "PrivateNetwork"): ("id", "name", "vpc_id"),
    ("vpc.v2", "VPC"): ("id", "name"),
}

# Les fonctions qui traduisent une réponse du SDK, et ce que chaque variable y
# désigne : un objet de réponse, dont le contrat déclare les champs, ou un client
# du SDK, dont c'est la classe qui porte les méthodes.
REPONSES: dict[str, dict[str, tuple[str, str]]] = {
    "_ipam_address": {
        "ip": ("ipam.v1", "IP"),
        "ressource": ("ipam.v1", "Resource"),
        "source": ("ipam.v1", "Source"),
    },
    "build_network_index": {
        "reseau": ("vpc.v2", "PrivateNetwork"),
        "item": ("vpc.v2", "VPC"),
    },
}

CLIENTS: dict[str, tuple[str, str]] = {
    "ipam": ("scaleway.ipam.v1", "IpamV1API"),
    "vpc": ("scaleway.vpc.v2", "VpcV2API"),
}

# Ce qui n'est ni une réponse d'API ni un client : accumulateurs locaux, rapport,
# exception. Nommé un par un plutôt que deviné par une heuristique : une variable
# non prévue doit faire rougir ce fichier, pas se ranger toute seule du bon côté.
HORS_CONTRAT = {"adresses", "categorie", "erreur", "index", "noms_vpc", "report", "reseaux"}


# --- ce que le code lit, lu dans le code ------------------------------------


def _fonction(nom: str) -> ast.FunctionDef:
    arbre = ast.parse(DISCOVERY.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef) and noeud.name == nom:
            return noeud
    raise AssertionError(f"`{nom}` a disparu de discovery.py : la jointure a été réécrite.")


def _champs_lus(fonction: ast.FunctionDef) -> set[tuple[str, str]]:
    """Les couples (variable, attribut) que la fonction lit, des deux façons.

    `getattr(objet, "champ", None)` **et** `objet.champ` : la jointure emploie
    les deux, et ne regarder que la première laisserait `reseau.id`, `item.id`
    et les appels au SDK hors de portée.
    """
    trouves: set[tuple[str, str]] = set()
    for noeud in ast.walk(fonction):
        if isinstance(noeud, ast.Attribute) and isinstance(noeud.value, ast.Name):
            trouves.add((noeud.value.id, noeud.attr))
            continue
        if not isinstance(noeud, ast.Call) or not isinstance(noeud.func, ast.Name):
            continue
        if noeud.func.id != "getattr" or len(noeud.args) < 2:
            continue
        objet, champ = noeud.args[0], noeud.args[1]
        if isinstance(objet, ast.Name) and isinstance(champ, ast.Constant):
            trouves.add((objet.id, str(champ.value)))
    return trouves


def _tout_ce_que_la_jointure_lit() -> set[tuple[str, str]]:
    lus: set[tuple[str, str]] = set()
    for nom in REPONSES:
        lus |= _champs_lus(_fonction(nom))
    return lus


# --- la dérive de l'API -----------------------------------------------------


def _proprietes(contrat: str, schema_court: str) -> set[str]:
    document = yaml.safe_load((SUIVIS / f"{contrat}.yml").read_text(encoding="utf-8"))
    schemas: dict[str, Any] = document["components"]["schemas"]
    cles = [nom for nom in schemas if nom.rsplit(".", 1)[-1] == schema_court]
    if len(cles) != 1:
        raise AssertionError(
            f"{contrat} ne déclare pas exactement un schéma `{schema_court}` : {cles}. "
            "Le schéma a été renommé ou dédoublé en amont."
        )
    return set((schemas[cles[0]] or {}).get("properties", {}))


@pytest.mark.parametrize(("cible", "champs"), sorted(CHAMPS_LUS.items()))
def test_chaque_champ_lu_par_la_jointure_existe_dans_le_contrat(
    cible: tuple[str, str], champs: tuple[str, ...]
) -> None:
    """La dérive amont, mesurée là où elle casserait la jointure en silence."""
    contrat, schema_court = cible
    manquants = sorted(set(champs) - _proprietes(contrat, schema_court))
    assert not manquants, (
        f"{contrat} `{schema_court}` ne déclare plus {manquants}. La jointure les lit par "
        "`getattr(..., None)` : elle ne lèvera pas, elle rendra des machines sans adresse."
    )


# --- la dérive du SDK -------------------------------------------------------


@pytest.mark.parametrize("variable", sorted(CLIENTS))
def test_le_sdk_installe_porte_les_methodes_que_la_jointure_appelle(variable: str) -> None:
    """L'autre moitié de la dérive, et la plus proche de la casse.

    Le contrat dit ce que l'API déclare ; le SDK est ce que la jointure appelle
    vraiment, et le verrou est `scaleway>=2.9.0`. Les noms sont déjà bizarres,
    `list_i_ps_all` et `list_vp_cs_all`, parce qu'ils sortent d'une
    dépluralisation automatique : c'est exactement le genre de nom qu'un
    générateur amont corrige un jour sans prévenir.

    Les méthodes attendues sont **lues dans le code**, pas recopiées ici.
    """
    module_nom, classe_nom = CLIENTS[variable]
    classe = getattr(importlib.import_module(module_nom), classe_nom)
    appelees = sorted(attr for nom, attr in _tout_ce_que_la_jointure_lit() if nom == variable)
    assert appelees, f"la jointure n'appelle plus rien sur `{variable}` : elle a été réécrite."
    absentes = [nom for nom in appelees if not hasattr(classe, nom)]
    assert not absentes, (
        f"{module_nom}.{classe_nom} ne porte plus {absentes}. La jointure appelle ces "
        "méthodes par leur nom : l'inventaire lèvera au premier hôte."
    )


# --- la garde de la garde ---------------------------------------------------


@pytest.mark.parametrize("fonction", sorted(REPONSES))
def test_la_declaration_couvre_tout_ce_que_le_code_lit(fonction: str) -> None:
    """Un champ lu sans être déclaré ici échapperait aux deux contrôles.

    Sans ce test, quelqu'un ajoute une lecture, les contrôles de dérive restent
    verts, et la nouvelle lecture n'est mesurée nulle part. Le fichier dirait
    alors qu'il couvre la jointure, et ce serait faux.
    """
    reponses = REPONSES[fonction]
    for variable, champ in sorted(_champs_lus(_fonction(fonction))):
        if variable in HORS_CONTRAT or variable in CLIENTS:
            continue
        assert variable in reponses, (
            f"`{fonction}` lit `{variable}.{champ}` sur un objet qu'aucun contrat ne couvre. "
            "Ajouter la variable à REPONSES, à CLIENTS, ou à HORS_CONTRAT si ce n'est ni une "
            "réponse d'API ni un client du SDK."
        )
        assert champ in CHAMPS_LUS[reponses[variable]], (
            f"`{fonction}` lit `{variable}.{champ}`, que CHAMPS_LUS ne déclare pas pour "
            f"{reponses[variable][0]} `{reponses[variable][1]}` : sa dérive n'est pas mesurée."
        )
