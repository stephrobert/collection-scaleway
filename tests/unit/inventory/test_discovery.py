"""L'orchestration : combien d'appels, et que se passe-t-il quand ils échouent.

C'est la couche qui décide entre « on continue en le disant » et « on
s'arrête ». Le plugin officiel n'a pas cette couche : chaque appel avale son
échec sur place, et l'inventaire incomplet sort avec un code de retour 0.

Le SDK n'est jamais appelé ici : les classes d'API sont remplacées par des
objets qui rendent des réponses figées, ce qui rend ces tests exécutables sans
identifiants ni émulateur.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory import discovery
from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.errors import (
    AuthenticationFailed,
)
from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.providers.base import (
    SCALEWAY_ZONES,
    DiscoveryContext,
)

from .test_providers import ApiFigee, EchecApi, _serveur_apple, _serveur_instance, _serveur_metal


@pytest.fixture
def apis_figees(monkeypatch):
    """Remplace les classes d'API du SDK par des objets à réponses figées."""
    figees: dict[str, ApiFigee] = {}

    def fabrique(nom: str, par_zone: dict[str, list], echecs=None):
        api = ApiFigee(par_zone, echecs)
        figees[nom] = api
        monkeypatch.setattr(discovery, nom, lambda client, _api=api: _api)
        return api

    fabrique("InstanceV1API", {"fr-par-1": [_serveur_instance()]})
    fabrique("BaremetalV1API", {"fr-par-1": [_serveur_metal()]})
    fabrique("ApplesiliconV1Alpha1API", {"fr-par-1": [_serveur_apple()]})
    return figees


class ClientMuet:
    """Un client que le SDK accepte de valider, et qui n'appelle rien."""

    def validate(self) -> None:
        return None


def test_un_produit_inconnu_est_refuse_avant_tout_appel() -> None:
    """Sinon l'inventaire serait silencieusement partiel."""
    with pytest.raises(ValueError, match="kubernetes"):
        discovery.providers_for(ClientMuet(), ("instance", "kubernetes"))


def test_les_trois_produits_sont_connus_du_registre() -> None:
    """Étape 5 : le registre est le seul endroit du cœur qui nomme un produit."""
    assert discovery.HOST_PROVIDERS == ("instance", "elastic_metal", "apple_silicon")
    providers = discovery.providers_for(ClientMuet(), discovery.HOST_PROVIDERS)
    assert [p.name for p in providers] == list(discovery.HOST_PROVIDERS)


def test_la_decouverte_agrege_les_trois_produits(apis_figees) -> None:
    resultat, rapport = discovery.discover(
        object(), DiscoveryContext(zones=("fr-par-1",)), discovery.HOST_PROVIDERS
    )
    assert {h.product for h in resultat.hosts} == set(discovery.HOST_PROVIDERS)
    assert rapport.providers == {"instance": 1, "elastic_metal": 1, "apple_silicon": 1}
    assert rapport.api_calls == 3


def test_le_rapport_compte_ce_qui_a_ete_fait(apis_figees) -> None:
    """Le mode debug doit pouvoir répondre à « combien d'appels, pour quoi »."""
    _, rapport = discovery.discover(object(), DiscoveryContext(zones=("fr-par-1",)), ("instance",))
    lignes = "\n".join(rapport.lines())
    assert "appels d'API : 1" in lignes
    assert "instance=1" in lignes


def test_un_appel_qui_echoue_est_rapporte_et_non_avale(monkeypatch) -> None:
    """C'est le rapport qui porte l'échec ; le mode strict le transforme en refus."""

    class ApiCassee:
        def list_servers_all(self, **kwargs):
            raise RuntimeError("le SDK a changé de signature")

    monkeypatch.setattr(discovery, "InstanceV1API", lambda client: ApiCassee())
    resultat, rapport = discovery.discover(
        object(), DiscoveryContext(zones=("fr-par-1",)), ("instance",)
    )
    assert resultat.hosts == ()
    assert any("DiscoveryFailed" in texte for texte in rapport.errors)


def test_en_mode_strict_une_exception_qui_echappe_fait_echouer_linventaire(monkeypatch) -> None:
    """Un provider qui casse ailleurs que sur l'appel ne doit pas passer inaperçu."""

    class ProviderCasse:
        name = "instance"

        def __init__(self, api) -> None:
            pass

        def discover(self, context):
            raise RuntimeError("normalisation impossible")

    monkeypatch.setattr(discovery, "InstanceV1API", lambda client: object())
    monkeypatch.setattr(discovery, "InstanceProvider", ProviderCasse)

    with pytest.raises(RuntimeError):
        discovery.discover(object(), DiscoveryContext(zones=("fr-par-1",)), ("instance",))

    _, rapport = discovery.discover(
        object(), DiscoveryContext(zones=("fr-par-1",)), ("instance",), strict=False
    )
    assert any("normalisation impossible" in texte for texte in rapport.errors)


def test_hors_mode_strict_lechec_est_dit_et_la_decouverte_continue(monkeypatch) -> None:
    class ApiCassee:
        def list_servers_all(self, **kwargs):
            raise RuntimeError("le SDK a changé de signature")

    monkeypatch.setattr(discovery, "InstanceV1API", lambda client: ApiCassee())
    monkeypatch.setattr(
        discovery, "BaremetalV1API", lambda client: ApiFigee({"fr-par-1": [_serveur_metal()]})
    )
    resultat, rapport = discovery.discover(
        object(),
        DiscoveryContext(zones=("fr-par-1",)),
        ("instance", "elastic_metal"),
        strict=False,
    )
    assert [h.product for h in resultat.hosts] == ["elastic_metal"]
    assert any("instance" in texte for texte in rapport.errors)


def test_un_echec_dauthentification_arrete_tout_meme_hors_mode_strict(monkeypatch) -> None:
    """Continuer produirait un inventaire vide qui se présente comme complet."""

    api = ApiFigee({}, echecs=dict.fromkeys(SCALEWAY_ZONES, EchecApi(401)))
    monkeypatch.setattr(discovery, "InstanceV1API", lambda client: api)
    with pytest.raises(AuthenticationFailed):
        discovery.discover(object(), DiscoveryContext(), ("instance",), strict=False)

    # Et l'arrêt est immédiat : une seule zone interrogée sur les dix.
    assert len(api.appels) == 1


def test_une_authentification_refusee_arrete_aussi_lindex_reseau(monkeypatch) -> None:
    _brancher(monkeypatch, ApiReseau(echec=EchecApi(401)))
    with pytest.raises(AuthenticationFailed):
        discovery.build_network_index(object(), ("fr-par",), report=discovery.DiscoveryReport())


# --------------------------------------------------------------------------
# L'index réseau
# --------------------------------------------------------------------------


class ApiReseau:
    """IPAM et VPC, en réponses figées, avec le compte des appels."""

    def __init__(self, ips=(), reseaux=(), vpcs=(), echec: Exception | None = None) -> None:
        self.ips, self.reseaux, self.vpcs, self.echec = ips, reseaux, vpcs, echec
        self.appels = 0

    def list_i_ps_all(self, **kwargs):
        self.appels += 1
        if self.echec:
            raise self.echec
        return list(self.ips)

    def list_private_networks_all(self, **kwargs):
        self.appels += 1
        return list(self.reseaux)

    def list_vp_cs_all(self, **kwargs):
        self.appels += 1
        return list(self.vpcs)


def _brancher(monkeypatch, api: ApiReseau) -> None:
    monkeypatch.setattr(discovery, "IpamV1API", lambda client: api)
    monkeypatch.setattr(discovery, "VpcV2API", lambda client: api)


def test_lindex_se_construit_en_trois_appels_par_region(monkeypatch) -> None:
    """La propriété qui fait tomber la complexité : par région, pas par machine."""
    api = ApiReseau()
    _brancher(monkeypatch, api)
    rapport = discovery.DiscoveryReport()

    discovery.build_network_index(object(), ("fr-par", "nl-ams"), report=rapport)

    assert api.appels == 6
    assert rapport.api_calls == 6


def test_lindex_traduit_ce_que_lipam_rend(monkeypatch) -> None:
    api = ApiReseau(
        ips=[
            SimpleNamespace(
                address="10.10.0.5/22",
                is_ipv6=False,
                resource=SimpleNamespace(id="nic-1", mac_address="02:00:00:aa"),
                source=SimpleNamespace(private_network_id="pn-1", vpc_id="vpc-1"),
            )
        ],
        reseaux=[SimpleNamespace(id="pn-1", name="backend", vpc_id="vpc-1")],
        vpcs=[SimpleNamespace(id="vpc-1", name="socle")],
    )
    _brancher(monkeypatch, api)

    index = discovery.build_network_index(object(), ("fr-par",))

    assert index.address_count == 1
    assert index.networks["pn-1"].name == "backend"
    assert index.vpc_names["vpc-1"] == "socle"


def test_une_region_sans_ipam_nest_pas_une_panne(monkeypatch) -> None:
    """L'enrichissement n'aura pas lieu, et le rapport le dit."""
    _brancher(monkeypatch, ApiReseau(echec=EchecApi(404)))
    rapport = discovery.DiscoveryReport()

    index = discovery.build_network_index(object(), ("fr-par",), report=rapport)

    assert index.address_count == 0
    assert rapport.errors == []
    assert any("indisponible" in texte for texte in rapport.warnings)


# --- ce que l'index réseau coûte, et à qui -------------------------------


def test_lindex_reseau_nest_paye_que_par_les_produits_qui_le_joignent() -> None:
    """Douze appels étaient émis quels que soient les produits demandés.

    Pour un inventaire qui ne demande qu'Apple Silicon, aucune carte réseau
    privée n'existe : le coût était payé pour personne.
    """
    assert discovery.needs_network_index(("instance",)) is True
    assert discovery.needs_network_index(("instance", "apple_silicon")) is True
    assert discovery.needs_network_index(("apple_silicon",)) is False
    assert discovery.needs_network_index(("elastic_metal", "apple_silicon")) is False
    assert discovery.needs_network_index(()) is False


def test_la_capacite_vient_des_providers_et_non_du_coeur() -> None:
    """Le cœur ne connaît aucun produit : trancher ici ramènerait la
    connaissance qu'on vient d'en sortir."""
    from ansible_collections.stephrobert.scaleway.plugins.module_utils.inventory.providers import (
        apple_silicon,
        elastic_metal,
        instance,
    )

    assert instance.InstanceProvider.joins_private_networks is True
    assert elastic_metal.ElasticMetalProvider.joins_private_networks is False
    assert apple_silicon.AppleSiliconProvider.joins_private_networks is False
    assert set(discovery.CAPACITES) == set(discovery.HOST_PROVIDERS)


def test_un_droit_manquant_sur_ipam_nempeche_pas_un_inventaire_public(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un jeton sans droit IPAM construit très bien un inventaire de machines
    publiques. Classer ce refus en erreur faisait échouer tout l'inventaire en
    mode strict, pour un enrichissement dont personne n'avait besoin."""
    _brancher(monkeypatch, ApiReseau(echec=EchecApi(403)))
    rapport = discovery.DiscoveryReport()

    index = discovery.build_network_index(object(), ("fr-par",), report=rapport)

    assert index.address_count == 0
    assert rapport.errors == [], "un droit manquant sur IPAM n'est pas une panne"
    assert any("PermissionDenied" in texte for texte in rapport.warnings), (
        "et il doit quand même être dit"
    )
