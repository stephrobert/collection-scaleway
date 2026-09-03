"""Les trois providers, et la preuve que le cœur ne les connaît pas.

L'exigence est de montrer que l'architecture accueille Elastic Metal
et Apple Silicon **sans modifier le cœur du plugin**. Deux preuves, de nature
différente :

* une preuve de comportement : chaque provider normalise une réponse d'API en
  `InventoryHost`, et le même pipeline de décision travaille ensuite dessus
  sans savoir de quel produit il s'agit ;
* une preuve structurelle : aucun nom de produit n'apparaît dans le code des
  couches de décision. Un test de comportement seul laisserait passer un `if
  host.product == ...` glissé dans une branche non couverte.

Aucun de ces trois providers n'a besoin de réseau : ils reçoivent un objet
d'API. Elastic Metal et Apple Silicon ne sont d'ailleurs pas jouables contre
l'émulateur (feint#631, feint#632), et c'est exactement pour cela que la
frontière `API -> modèle normalisé` doit être testable seule.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory import (
    address,
    filtering,
    groups,
    hostname,
)
from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.errors import (
    PermissionDenied,
)
from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.network import (
    IpamAddress,
    PrivateNetworkInfo,
    build_index,
)
from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.providers import (
    apple_silicon,
    base,
    elastic_metal,
    instance,
)


class ApiFigee:
    """Un objet d'API qui rend des réponses figées et note ses appels."""

    def __init__(self, par_zone: dict[str, list], echecs: dict[str, Exception] | None = None):
        self.par_zone = par_zone
        self.echecs = echecs or {}
        self.appels: list[dict] = []

    def list_servers_all(self, **kwargs):
        self.appels.append(kwargs)
        zone = kwargs["zone"]
        if zone in self.echecs:
            raise self.echecs[zone]
        return self.par_zone.get(zone, [])


class EchecApi(Exception):
    def __init__(self, status_code: int, message: str = "") -> None:
        super().__init__(message or f"HTTP {status_code}")
        self.status_code = status_code


UNE_ZONE = base.DiscoveryContext(zones=("fr-par-1",))


# --------------------------------------------------------------------------
# Instance : deux champs singuliers, plus une liste moderne
# --------------------------------------------------------------------------


def _serveur_instance(**champs):
    defauts = dict(
        id="i-1",
        name="web01",
        zone="fr-par-1",
        state=SimpleNamespace(value="running"),
        tags=["env=prod"],
        organization="org-1",
        project="proj-1",
        commercial_type="DEV1-S",
        public_ips=[SimpleNamespace(address="51.15.1.1", family="inet")],
        private_nics=[],
    )
    defauts.update(champs)
    return SimpleNamespace(**defauts)


def test_instance_normalise_ce_que_lapi_rend() -> None:
    host = instance.normalize(_serveur_instance(), UNE_ZONE)
    assert (host.id, host.product, host.name) == ("i-1", "instance", "web01")
    assert (host.zone, host.region) == ("fr-par-1", "fr-par")
    assert (host.state, host.tags) == ("running", ("env=prod",))
    assert (host.organization_id, host.project_id) == ("org-1", "proj-1")
    assert host.metadata["commercial_type"] == "DEV1-S"


def test_instance_garde_toutes_les_adresses_publiques() -> None:
    """Le plugin officiel n'en lit qu'une par famille."""
    serveur = _serveur_instance(
        public_ips=[
            SimpleNamespace(address="51.15.1.1", family="inet"),
            SimpleNamespace(address="51.15.1.2", family="inet"),
            SimpleNamespace(address="2001:db8::1", family="inet6"),
        ]
    )
    host = instance.normalize(serveur, UNE_ZONE)
    assert host.public_ipv4 == ("51.15.1.1", "51.15.1.2")
    assert host.public_ipv6 == ("2001:db8::1",)


def test_instance_retombe_sur_les_champs_historiques() -> None:
    """Un SDK plus ancien ne rend pas `public_ips`."""
    serveur = _serveur_instance(
        public_ips=[],
        public_ip=SimpleNamespace(address="51.15.1.1"),
        ipv6=SimpleNamespace(address="2001:db8::1"),
    )
    host = instance.normalize(serveur, UNE_ZONE)
    assert host.public_ipv4 == ("51.15.1.1",)
    assert host.public_ipv6 == ("2001:db8::1",)


def test_instance_joint_ses_cartes_sans_appel_supplementaire() -> None:
    index = build_index(
        addresses=(IpamAddress("10.10.0.5/22", False, "nic-1", "pn-1", "vpc-1"),),
        networks=(PrivateNetworkInfo("pn-1", "backend", "vpc-1"),),
        vpc_names={"vpc-1": "socle"},
    )
    contexte = base.DiscoveryContext(zones=("fr-par-1",), network=index)
    serveur = _serveur_instance(
        private_nics=[SimpleNamespace(id="nic-1", private_network_id="pn-1", mac_address=None)]
    )
    host = instance.normalize(serveur, contexte)

    assert host.private_ipv4 == ("10.10.0.5",)
    assert host.private_networks[0].private_network_name == "backend"
    assert host.private_networks[0].vpc_name == "socle"


def test_instance_ninterroge_que_les_zones_demandees() -> None:
    api = ApiFigee({"fr-par-1": [_serveur_instance()]})
    resultat = instance.InstanceProvider(api).discover(UNE_ZONE)
    assert [appel["zone"] for appel in api.appels] == ["fr-par-1"]
    assert resultat.api_calls == 1
    assert len(resultat.hosts) == 1


def test_instance_interroge_les_dix_zones_par_defaut() -> None:
    """Le plugin officiel en code sept en dur, et en oublie trois."""
    api = ApiFigee({})
    instance.InstanceProvider(api).discover(base.DiscoveryContext())
    assert [appel["zone"] for appel in api.appels] == list(base.SCALEWAY_ZONES)
    assert len(base.SCALEWAY_ZONES) == 10


def test_instance_demande_un_appel_par_etat() -> None:
    """`state` est un enum côté API : plusieurs états, plusieurs requêtes."""
    api = ApiFigee({})
    contexte = base.DiscoveryContext(zones=("fr-par-1",), states=("running", "stopped"))
    instance.InstanceProvider(api).discover(contexte)
    assert [appel["state"] for appel in api.appels] == ["running", "stopped"]


def test_une_zone_qui_ne_sert_pas_le_produit_est_un_avertissement() -> None:
    api = ApiFigee({}, echecs={"fr-par-1": EchecApi(404)})
    resultat = instance.InstanceProvider(api).discover(UNE_ZONE)
    assert resultat.errors == ()
    assert "n'est pas servi" in resultat.warnings[0]


def test_un_droit_refuse_est_une_erreur_pas_un_silence() -> None:
    """Le défaut central du plugin officiel : `except: pass`."""
    api = ApiFigee({}, echecs={"fr-par-1": EchecApi(403)})
    resultat = instance.InstanceProvider(api).discover(UNE_ZONE)
    assert resultat.warnings == ()
    assert PermissionDenied.__name__ in resultat.errors[0]


def test_les_hosts_sortent_tries_pour_que_linventaire_soit_stable() -> None:
    api = ApiFigee({"fr-par-1": [_serveur_instance(id="i-9"), _serveur_instance(id="i-2")]})
    resultat = instance.InstanceProvider(api).discover(UNE_ZONE)
    assert [h.id for h in resultat.hosts] == ["i-2", "i-9"]


def test_la_reponse_brute_nest_gardee_que_si_on_la_demande() -> None:
    serveur = _serveur_instance()
    assert instance.normalize(serveur, UNE_ZONE).raw is None
    avec = base.DiscoveryContext(zones=("fr-par-1",), include_raw=True)
    assert instance.normalize(serveur, avec).raw is serveur


# --------------------------------------------------------------------------
# Elastic Metal : une liste, chaque entrée porte sa famille
# --------------------------------------------------------------------------


def _serveur_metal(**champs):
    defauts = dict(
        id="bm-1",
        name="metal01",
        zone="fr-par-2",
        status=SimpleNamespace(value="ready"),
        tags=["env=prod"],
        organization_id="org-1",
        project_id="proj-1",
        offer_name="EM-A210R",
        ips=[
            SimpleNamespace(address="51.15.2.1", version=SimpleNamespace(value="i_pv4")),
            SimpleNamespace(address="2001:db8::2", version=SimpleNamespace(value="i_pv6")),
        ],
    )
    defauts.update(champs)
    return SimpleNamespace(**defauts)


def test_elastic_metal_separe_les_familles_dune_liste() -> None:
    """La forme d'adresse qui aurait fait diverger un plugin monolithique."""
    host = elastic_metal.normalize(_serveur_metal(), UNE_ZONE)
    assert host.product == "elastic_metal"
    assert host.public_ipv4 == ("51.15.2.1",)
    assert host.public_ipv6 == ("2001:db8::2",)
    assert host.region == "fr-par"
    assert host.state == "ready"
    assert host.metadata["offer_name"] == "EM-A210R"


def test_elastic_metal_garde_plusieurs_adresses_de_la_meme_famille() -> None:
    """Le plugin officiel ne retient que la dernière de chaque famille."""
    serveur = _serveur_metal(
        ips=[
            SimpleNamespace(address="51.15.2.1", version="i_pv4"),
            SimpleNamespace(address="51.15.2.2", version="i_pv4"),
        ]
    )
    assert elastic_metal.normalize(serveur, UNE_ZONE).public_ipv4 == ("51.15.2.1", "51.15.2.2")


def test_elastic_metal_ignore_une_entree_sans_adresse() -> None:
    serveur = _serveur_metal(ips=[SimpleNamespace(address=None, version="i_pv4")])
    host = elastic_metal.normalize(serveur, UNE_ZONE)
    assert host.public_ipv4 == () and host.public_ipv6 == ()


def test_elastic_metal_filtre_les_tags_cote_api() -> None:
    api = ApiFigee({"fr-par-1": []})
    contexte = base.DiscoveryContext(zones=("fr-par-1",), tags=("env=prod",))
    elastic_metal.ElasticMetalProvider(api).discover(contexte)
    assert api.appels[0]["tags"] == ["env=prod"]


# --------------------------------------------------------------------------
# Apple Silicon : un seul champ, une seule adresse
# --------------------------------------------------------------------------


def _serveur_apple(**champs):
    defauts = dict(
        id="as-1",
        name="mac01",
        zone="fr-par-3",
        status=SimpleNamespace(value="ready"),
        tags=["env=build"],
        organization_id="org-1",
        project_id="proj-1",
        ip="51.15.3.1",
        ssh_username="m1",
        vpc_status="enabled",
    )
    defauts.update(champs)
    return SimpleNamespace(**defauts)


def test_apple_silicon_normalise_son_adresse_unique() -> None:
    host = apple_silicon.normalize(_serveur_apple(), UNE_ZONE)
    assert host.product == "apple_silicon"
    assert host.public_ipv4 == ("51.15.3.1",)
    assert host.region == "fr-par"


def test_apple_silicon_expose_le_compte_de_connexion() -> None:
    """Aucun autre produit Scaleway ne dit avec quel compte se connecter."""
    host = apple_silicon.normalize(_serveur_apple(), UNE_ZONE)
    assert host.metadata["ssh_username"] == "m1"


def test_apple_silicon_garde_les_vrais_tags() -> None:
    """Le plugin officiel écrit `apple_sillicon` en dur et jette les vrais."""
    host = apple_silicon.normalize(_serveur_apple(), UNE_ZONE)
    assert host.tags == ("env=build",)


def test_apple_silicon_sans_adresse_reste_un_host() -> None:
    """Une machine sans route SSH reste pilotable en `delegate_to: localhost`."""
    host = apple_silicon.normalize(_serveur_apple(ip=None), UNE_ZONE)
    assert host.public_ipv4 == ()
    assert host.id == "as-1"


def test_apple_silicon_ne_demande_pas_de_filtre_que_son_api_ignore() -> None:
    """Son `list_servers_all` n'accepte ni `tags` ni `state` : mesuré sur le SDK.

    Il accepte en revanche `organization_id`, comme les deux autres.
    """
    api = ApiFigee({"fr-par-1": []})
    contexte = base.DiscoveryContext(zones=("fr-par-1",), tags=("env=prod",), states=("ready",))
    apple_silicon.AppleSiliconProvider(api).discover(contexte)
    assert set(api.appels[0]) == {"zone", "project_id", "organization_id"}


# --------------------------------------------------------------------------
# Étape 5 : le cœur ne connaît aucun produit
# --------------------------------------------------------------------------

TROIS_PRODUITS = (
    (instance, _serveur_instance()),
    (elastic_metal, _serveur_metal()),
    (apple_silicon, _serveur_apple()),
)

IDS = ("instance", "elastic_metal", "apple_silicon")


@pytest.mark.parametrize(("module", "serveur"), TROIS_PRODUITS, ids=IDS)
def test_le_meme_pipeline_traite_les_trois_produits(module, serveur) -> None:
    """Filtrage, nom d'hôte, groupes et adresse : aucun cas particulier."""
    host = module.normalize(serveur, UNE_ZONE)

    garde, _ = filtering.keep(host, filtering.Filters(tags=host.tags[:1]))
    attribues, _ = hostname.assign_hostnames((host,), ("name", "id"))
    noms = groups.group_names(host, ("product", "region", "zone"))
    choix = address.select_ansible_host(host, address.AddressPolicy())

    assert garde
    assert attribues[0][1] == host.name
    assert f"scw_product_{host.product}" in noms
    assert choix.found


def test_les_trois_produits_cohabitent_dans_un_meme_inventaire() -> None:
    hosts = tuple(module.normalize(serveur, UNE_ZONE) for module, serveur in TROIS_PRODUITS)
    attribues, avertissements = hostname.assign_hostnames(hosts, ("name",))
    assert len({nom for _, nom in attribues}) == 3
    assert avertissements == ()


#: Les couches que l'ajout d'un produit ne doit pas toucher.
COEUR = (
    "models.py",
    "address.py",
    "groups.py",
    "hostname.py",
    "network.py",
    "filtering.py",
    "errors.py",
    "config.py",
    "providers/base.py",
)


PORTEURS_DE_DOCSTRING = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _code_sans_prose(chemin: Path) -> str:
    """Le code seul : ni commentaire, ni docstring, mais toutes les chaînes.

    La prose de ce dépôt nomme les produits pour expliquer ses décisions, et
    c'est très bien. Ce qui est interdit, c'est qu'une **instruction** les
    nomme, et un `if host.product == "instance"` est une instruction : garder
    les chaînes littérales est donc ce qui donne sa force au contrôle.

    `ast.unparse` supprime les commentaires ; les docstrings se retirent une à
    une, parce qu'elles sont des instructions comme les autres.
    """
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, PORTEURS_DE_DOCSTRING):
            continue
        corps = noeud.body
        if (
            corps
            and isinstance(corps[0], ast.Expr)
            and isinstance(corps[0].value, ast.Constant)
            and isinstance(corps[0].value.value, str)
        ):
            noeud.body = corps[1:] or [ast.Pass()]
    return ast.unparse(ast.fix_missing_locations(arbre))


@pytest.mark.parametrize("fichier", COEUR)
def test_aucune_couche_du_coeur_ne_nomme_un_produit(fichier: str, collection_importable) -> None:
    """La preuve structurelle de l'étape 5.

    Si cette assertion tombe un jour, c'est qu'un produit a fuité hors de son
    provider, et que le suivant coûtera une modification du cœur.
    """
    racine = collection_importable / "ansible_collections/stephrobert/scaleway"
    code = _code_sans_prose(racine / "plugins/module_utils/inventory" / fichier)

    # Les frontières de mot comptent : `isinstance` n'est pas le produit
    # Instance, et une recherche par sous-chaîne confondrait les deux.
    for produit in ("instance", "elastic_metal", "apple_silicon", "baremetal", "applesilicon"):
        trouve = re.search(rf"\b{produit}\b", code)
        assert trouve is None, f"{fichier} nomme le produit '{produit}' dans son code"
