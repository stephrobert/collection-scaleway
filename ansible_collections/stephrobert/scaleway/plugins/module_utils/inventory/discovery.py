# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""L'orchestration : construire les index, lancer les providers, agréger.

C'est la seule couche qui importe le SDK. Les providers reçoivent des objets
d'API, la jointure reçoit des enregistrements normalisés, et le plugin reçoit
un résultat. Chacune se teste donc sans les autres.

L'index réseau est construit **une fois par région**, avant les providers, et
partagé par tous. C'est ce qui fait tomber la complexité de
`O(hosts x cartes)` à `O(régions)`.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from .errors import AuthenticationFailed, PermissionDenied, ProductUnavailable, classify
from .models import ProviderResult
from .network import IpamAddress, NetworkIndex, PrivateNetworkInfo, build_index
from .providers.apple_silicon import AppleSiliconProvider
from .providers.base import DiscoveryContext
from .providers.elastic_metal import ElasticMetalProvider
from .providers.instance import InstanceProvider

try:
    from scaleway.applesilicon.v1alpha1 import ApplesiliconV1Alpha1API
    from scaleway.baremetal.v1 import BaremetalV1API
    from scaleway.instance.v1 import InstanceV1API
    from scaleway.ipam.v1 import IpamV1API
    from scaleway.vpc.v2 import VpcV2API

    SDK_IMPORT_ERROR: str | None = None
    HAS_SDK = True
except ImportError:
    SDK_IMPORT_ERROR = traceback.format_exc()
    HAS_SDK = False

#: Les providers de hosts que cette version connaît. `products: all` désigne
#: cette table, et non toutes les APIs Scaleway existantes.
HOST_PROVIDERS: tuple[str, ...] = ("instance", "elastic_metal", "apple_silicon")


@dataclass
class DiscoveryReport:
    """Ce que la découverte a fait, pour le mode debug et le rapport d'échec."""

    api_calls: int = 0
    providers: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    network_addresses: int = 0

    def lines(self) -> list[str]:
        resume = ", ".join(f"{nom}={compte}" for nom, compte in sorted(self.providers.items()))
        return [
            f"appels d'API : {self.api_calls}",
            f"adresses IPAM indexées : {self.network_addresses}",
            f"hosts par provider : {resume or 'aucun'}",
            *(f"avertissement : {texte}" for texte in self.warnings),
            *(f"erreur : {texte}" for texte in self.errors),
        ]


def _ipam_address(ip: Any) -> IpamAddress:
    """Traduit une adresse IPAM du SDK en enregistrement de jointure."""
    ressource = getattr(ip, "resource", None)
    source = getattr(ip, "source", None)
    return IpamAddress(
        address=str(getattr(ip, "address", "")),
        is_ipv6=bool(getattr(ip, "is_ipv6", False)),
        resource_id=getattr(ressource, "id", None) if ressource else None,
        private_network_id=getattr(source, "private_network_id", None) if source else None,
        vpc_id=getattr(source, "vpc_id", None) if source else None,
        mac_address=getattr(ressource, "mac_address", None) if ressource else None,
    )


def build_network_index(
    client: Any,
    regions: tuple[str, ...],
    project_ids: tuple[str, ...] = (),
    report: DiscoveryReport | None = None,
) -> NetworkIndex:
    """Liste IPAM, les réseaux privés et les VPC, puis indexe.

    Une liste par région et par projet demandé, pas une par machine. Une région
    qui ne sert pas IPAM ou VPC n'est pas une panne : c'est un enrichissement
    qui n'aura pas lieu, et le rapport le dit.
    """
    ipam = IpamV1API(client)
    vpc = VpcV2API(client)

    adresses: list[IpamAddress] = []
    reseaux: list[PrivateNetworkInfo] = []
    noms_vpc: dict[str, str] = {}
    projets: tuple[str | None, ...] = project_ids or (None,)

    def collecte(label: str, region: str, appel: Any) -> Any | None:
        """Un appel de liste, classé s'il échoue. Aucune fermeture sur la boucle."""
        if report is not None:
            report.api_calls += 1
        try:
            return appel()
        except Exception as erreur:
            categorie = classify(getattr(erreur, "status_code", None), str(erreur))
            if categorie is AuthenticationFailed:
                raise AuthenticationFailed(str(erreur)) from erreur
            if report is None:
                return None
            if categorie in (ProductUnavailable, PermissionDenied):
                # Un jeton sans droit IPAM ou VPC peut parfaitement construire
                # un inventaire de machines publiques. Classer ce refus en
                # erreur faisait échouer tout l'inventaire en mode strict, pour
                # un enrichissement dont personne n'avait besoin. C'est un
                # enrichissement qui n'aura pas lieu, pas une panne.
                report.warnings.append(
                    f"enrichissement réseau indisponible dans {region} ({label}) : "
                    f"{categorie.__name__}"
                )
            else:
                report.errors.append(f"{categorie.__name__} sur {label} dans {region} : {erreur}")
            return None

    for region in regions:
        for projet in projets:
            trouves = collecte(
                "ipam",
                region,
                # Pas de filtre `attached`, et la raison a changé de nature.
                #
                # Elle était d'abord un contournement : l'émulateur rendait une
                # liste vide pour `attached=True`, l'orthographe que le SDK
                # Python envoie. C'est corrigé en amont (feint#630), et mesuré :
                # `true`, `True`, `1`, `t`, `TRUE` rendent le même compte, et
                # une valeur illisible est refusée en 400 au lieu de passer pour
                # un parc vide.
                #
                # Elle reste une décision de conception. La jointure ignore déjà
                # une adresse sans ressource, donc le filtre ne changerait pas
                # le résultat ; et c'est l'appel dont l'échec est le plus
                # invisible, parce qu'un index vide rend des machines avec un
                # réseau, une adresse MAC et aucune adresse. Un résultat correct
                # par construction vaut mieux qu'un résultat correct par
                # confiance dans l'analyse d'un booléen.
                partial(ipam.list_i_ps_all, region=region, project_id=projet),
            )
            if trouves is not None:
                adresses.extend(_ipam_address(ip) for ip in trouves)

            trouves = collecte(
                "networks",
                region,
                partial(vpc.list_private_networks_all, region=region, project_id=projet),
            )
            if trouves is not None:
                reseaux.extend(
                    PrivateNetworkInfo(
                        id=str(reseau.id),
                        name=getattr(reseau, "name", None),
                        vpc_id=getattr(reseau, "vpc_id", None),
                    )
                    for reseau in trouves
                )

            trouves = collecte(
                "vpcs",
                region,
                partial(vpc.list_vp_cs_all, region=region, project_id=projet),
            )
            if trouves is not None:
                noms_vpc.update(
                    {str(item.id): getattr(item, "name", None) or str(item.id) for item in trouves}
                )

    index = build_index(tuple(adresses), tuple(reseaux), noms_vpc)
    if report is not None:
        report.network_addresses = index.address_count
    return index


def providers_for(client: Any, products: tuple[str, ...]) -> tuple[Any, ...]:
    """Instancie les providers demandés, et refuse un produit inconnu.

    Un nom de produit qui ne correspond à rien est une faute de configuration.
    L'ignorer produirait un inventaire silencieusement partiel.
    """
    inconnus = sorted(set(products) - set(HOST_PROVIDERS))
    if inconnus:
        raise ValueError(f"produit(s) inconnu(s) : {inconnus}. Connus : {list(HOST_PROVIDERS)}")

    # Ajouter un produit, c'est ajouter une ligne ici et un fichier de
    # provider. Aucune autre couche ne connaît le nom d'un produit.
    fabriques = {
        "instance": lambda: InstanceProvider(InstanceV1API(client)),
        "elastic_metal": lambda: ElasticMetalProvider(BaremetalV1API(client)),
        "apple_silicon": lambda: AppleSiliconProvider(ApplesiliconV1Alpha1API(client)),
    }
    return tuple(fabriques[nom]() for nom in products)


def needs_network_index(products: tuple[str, ...]) -> bool:
    """Faut-il payer l'index réseau pour les produits demandés ?

    Douze appels d'API étaient émis quels que soient les produits, y compris
    pour un inventaire qui ne demandait qu'Apple Silicon et n'avait donc
    aucune carte réseau privée à joindre. Le coût était payé pour personne.

    La question est posée aux providers : le cœur ne connaît aucun produit, et
    trancher ici ramènerait la connaissance qu'on vient d'en sortir.
    """
    return any(CAPACITES.get(nom, False) for nom in products)


#: Ce que chaque provider déclare de lui-même, lu une fois pour éviter de les
#: instancier avant d'avoir un client.
CAPACITES: dict[str, bool] = {
    "instance": InstanceProvider.joins_private_networks,
    "elastic_metal": ElasticMetalProvider.joins_private_networks,
    "apple_silicon": AppleSiliconProvider.joins_private_networks,
}


def discover(
    client: Any,
    context: DiscoveryContext,
    products: tuple[str, ...],
    strict: bool = True,
) -> tuple[ProviderResult, DiscoveryReport]:
    """Lance les providers et agrège leurs résultats.

    En mode strict, l'échec d'un provider fait échouer l'inventaire. Sinon il
    devient un avertissement, et le rapport nomme le provider fautif. Dans les
    deux cas, l'échec est **dit** : c'est ce qui manque au plugin officiel.
    """
    resultat = ProviderResult()
    report = DiscoveryReport()

    for provider in providers_for(client, products):
        try:
            partiel = provider.discover(context)
        except AuthenticationFailed:
            raise
        except Exception as erreur:
            message = f"{provider.name} : {erreur}"
            if strict:
                raise
            report.errors.append(message)
            continue

        resultat = resultat.merge(partiel)
        report.api_calls += partiel.api_calls
        report.providers[provider.name] = len(partiel.hosts)
        report.warnings.extend(partiel.warnings)
        report.errors.extend(partiel.errors)

    return resultat, report
