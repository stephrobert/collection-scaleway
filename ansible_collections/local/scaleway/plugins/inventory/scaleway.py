# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
name: scaleway
short_description: Scaleway dynamic inventory
version_added: 0.1.0
author:
  - Stéphane Robert (@stephrobert)
requirements:
  - scaleway >= 2.9.0
description:
  - Builds an Ansible inventory from a Scaleway account.
  - >-
    Discovers hosts product by product, then enriches them with their private
    networks and VPCs by listing IPAM once per region rather than once per
    network interface.
  - Uses a configuration file whose name ends with C(scaleway.yml) or C(scw.yml).
extends_documentation_fragment:
  - constructed
  - inventory_cache
notes:
  - >-
    The credential options are declared here rather than inherited from the
    module documentation fragment. A module option carries no C(env) key, so
    its default would silently win over the environment, and a run meant for a
    local emulator would reach the real Scaleway API instead.
options:
  plugin:
    description: The name of this plugin.
    required: true
    choices: ['local.scaleway.scaleway']
    type: str
  profile:
    description: Name of the profile to read in the Scaleway configuration file.
    type: str
    env:
      - name: SCW_PROFILE
  config_file:
    description: Path to the Scaleway configuration file.
    type: path
    env:
      - name: SCW_CONFIG_PATH
  access_key:
    description: Scaleway API access key.
    type: str
    env:
      - name: SCW_ACCESS_KEY
  secret_key:
    description: Scaleway API secret key.
    type: str
    env:
      - name: SCW_SECRET_KEY
  api_url:
    description:
      - URL of the Scaleway API endpoint.
      - Point it at a local emulator to build an inventory without credentials.
      - >-
        Falls back to the Scaleway configuration file, then to
        C(https://api.scaleway.com). It carries no default on purpose: a
        default is never unset, so it would always override the profile.
    type: str
    env:
      - name: SCW_API_URL
  api_allow_insecure:
    description: Reach the endpoint without verifying its TLS certificate.
    type: bool
  user_agent:
    description: Value of the User-Agent header sent to the API.
    type: str
  organization_id:
    description: Default Organization ID.
    type: str
    env:
      - name: SCW_DEFAULT_ORGANIZATION_ID
  project_id:
    description: Default Project ID.
    type: str
    env:
      - name: SCW_DEFAULT_PROJECT_ID
  products:
    description:
      - Products to discover hosts from.
      - C(all) means every host product this plugin version supports.
    type: list
    elements: str
    default: [all]
  zones:
    description:
      - Zones to query. Empty means every zone the product declares.
    type: list
    elements: str
    default: []
  regions:
    description:
      - Regions used to build the network index. Derived from the zones when empty.
    type: list
    elements: str
    default: []
  projects:
    description:
      - Project IDs to restrict discovery to. Empty means the profile default.
    type: list
    elements: str
    default: []
  organizations:
    description:
      - Organization IDs to restrict discovery to.
    type: list
    elements: str
    default: []
  hostnames:
    description:
      - Sources for C(inventory_hostname), in order of precedence.
      - >-
        Accepts C(name), C(id), C(public_ipv4), C(public_ipv6),
        C(private_ipv4), C(private_ipv6) and C(tag:KEY), which reads a
        C(KEY=value) tag.
      - >-
        The names C(hostname), C(vpc_ipv4) and C(vpc_ipv6) used by the official
        collection are accepted as aliases.
      - Collisions are resolved by appending the zone, then the resource ID.
    type: list
    elements: str
    default: [name, id]
  address_priority:
    description:
      - Address families to try, in order, when setting C(ansible_host).
    type: list
    elements: str
    default: [private_ipv4, public_ipv4, private_ipv6, public_ipv6]
  address:
    description:
      - Restrict C(ansible_host) to one private network.
      - Accepts C(private_network), a name or an ID, or C(private_network_id).
    type: dict
    default: {}
  require_address:
    description:
      - Drop hosts for which no address could be selected.
      - >-
        False keeps them without C(ansible_host), which is still useful for
        tasks delegated to localhost that act through the Scaleway API.
    type: bool
    default: false
  tags:
    description: Only keep hosts carrying these tags.
    type: list
    elements: str
    default: []
  tags_match:
    description: Whether a host must carry any or all of the requested tags.
    type: str
    choices: [any, all]
    default: any
  states:
    description: Only keep hosts in these states.
    type: list
    elements: str
    default: []
  exclude:
    description:
      - Drop hosts matching these tags or states, after every other filter.
    type: dict
    default: {}
  group_by:
    description:
      - Axes used to build the native C(scw_*) groups.
    type: list
    elements: str
    choices: [product, project, region, zone, state, tags, vpc, private_network]
    default: [product, project, region, zone]
  include_raw:
    description:
      - Expose the raw API object as C(scaleway_raw). Off by default.
    type: bool
    default: false
  strict:
    description:
      - Fail the inventory when a provider fails, instead of warning.
    type: bool
    default: true
"""

EXAMPLES = r"""
# Le cas minimal : le profil Scaleway habituel décide du reste.
plugin: local.scaleway.scaleway

# Production : un projet, une région, les machines qui tournent.
# plugin: local.scaleway.scaleway
# projects:
#   - 11111111-1111-1111-1111-111111111111
# products:
#   - instance
# regions:
#   - fr-par
# states:
#   - running
# tags:
#   - production
# address_priority:
#   - private_ipv4
#   - public_ipv4
# group_by:
#   - product
#   - project
#   - zone
#   - tags
# cache: true

# Joindre les machines par un réseau privé précis.
# plugin: local.scaleway.scaleway
# address:
#   private_network: production
# require_address: true

# Groupes et variables construits par Ansible lui-même.
# plugin: local.scaleway.scaleway
# compose:
#   ansible_user: "'ubuntu'"
# keyed_groups:
#   - prefix: scw_type
#     key: scaleway_instance.commercial_type
"""

import traceback

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils.basic import missing_required_lib
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

from ansible_collections.local.scaleway.plugins.module_utils.inventory import (
    config as configuration,
)
from ansible_collections.local.scaleway.plugins.module_utils.inventory import (
    discovery,
    filtering,
)
from ansible_collections.local.scaleway.plugins.module_utils.inventory.address import (
    select_ansible_host,
)
from ansible_collections.local.scaleway.plugins.module_utils.inventory.groups import group_names
from ansible_collections.local.scaleway.plugins.module_utils.inventory.hostname import (
    assign_hostnames,
)
from ansible_collections.local.scaleway.plugins.module_utils.inventory.models import (
    InventoryHost,
    NetworkAttachment,
)
from ansible_collections.local.scaleway.plugins.module_utils.inventory.providers.base import (
    SCALEWAY_ZONES,
    DiscoveryContext,
    region_of,
)
from ansible_collections.local.scaleway.plugins.module_utils.inventory.providers.instance import (
    ZONES as INSTANCE_ZONES,
)

try:
    from ansible_collections.local.scaleway.plugins.module_utils.scaleway import (
        build_client_from_values,
    )

    SDK_IMPORT_ERROR = None
except ImportError:
    SDK_IMPORT_ERROR = traceback.format_exc()

#: Les suffixes que le plugin officiel accepte, conservés tels quels pour
#: qu'une configuration existante continue d'être reconnue.
ALLOWED_SUFFIXES = ("scaleway.yaml", "scaleway.yml", "scw.yaml", "scw.yml")

#: Les paramètres communs que le fragment de documentation apporte, et que la
#: construction du client attend.
CLIENT_OPTIONS = (
    "profile",
    "config_file",
    "access_key",
    "secret_key",
    "api_url",
    "api_allow_insecure",
    "user_agent",
    "organization_id",
    "project_id",
)


def _plain(valeur):
    """Réduit un objet du SDK à des structures qu'un cache sait écrire.

    Un cache `jsonfile` ne sait pas écrire une dataclass du SDK, ni un enum,
    ni une date. Ce qui n'a pas d'équivalent JSON devient sa représentation
    textuelle plutôt que de faire échouer l'écriture : le champ est un confort
    de diagnostic, il n'a pas à casser un inventaire.
    """
    if valeur is None or isinstance(valeur, (str, int, float, bool)):
        return valeur
    if isinstance(valeur, dict):
        return {str(cle): _plain(item) for cle, item in valeur.items()}
    if isinstance(valeur, (list, tuple, set)):
        return [_plain(item) for item in valeur]
    interne = getattr(valeur, "__dict__", None)
    if interne:
        return {str(cle): _plain(item) for cle, item in interne.items()}
    return str(valeur)


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    """Le dialogue avec Ansible, et rien d'autre.

    Toutes les décisions vivent dans `module_utils/inventory/`, en couches qui
    se testent seules. Ce fichier lit les options, appelle le moteur, et pose
    le résultat dans l'inventaire.
    """

    NAME = "local.scaleway.scaleway"

    def verify_file(self, path):
        if not super(InventoryModule, self).verify_file(path):
            return False
        if not path.endswith(ALLOWED_SUFFIXES):
            self.display.vvv(
                "Skipping due to inventory source file name mismatch. "
                "The file name has to end with one of: " + ", ".join(ALLOWED_SUFFIXES)
            )
            return False
        return True

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)

        if not discovery.HAS_SDK:
            raise AnsibleError(missing_required_lib("scaleway"))

        try:
            settings = configuration.from_options(
                self.get_option, discovery.HOST_PROVIDERS, SCALEWAY_ZONES
            )
        except configuration.ConfigError as erreur:
            raise AnsibleParserError(str(erreur)) from erreur

        self.load_cache_plugin()
        empreinte = settings.cache_fingerprint(
            self.get_option("profile"),
            self.get_option("api_url"),
            self.get_option("access_key"),
        )
        cache_key = "%s_%s" % (self.get_cache_key(path), empreinte)

        demande = self.get_option("cache")
        lire = demande and cache
        ecrire = demande and not cache

        materiel = None
        if lire:
            try:
                materiel = self._cache[cache_key]
                self.display.vvv("scaleway: cache hit (%s)" % cache_key)
            except KeyError:
                ecrire = True

        if materiel is None:
            materiel = self._collect(settings)
            self.display.vvv("scaleway: cache miss, découverte effectuée")

        if ecrire:
            self._cache[cache_key] = materiel

        self._populate(materiel, settings)

    def _collect(self, settings):
        """Découvre, enrichit, et rend une structure que n'importe quel cache accepte.

        Le plugin officiel met en cache des objets `Host` d'ansible-core, ce
        qui lie le format du cache à une version d'Ansible. Ici le cache ne
        reçoit que des dictionnaires.
        """
        client = build_client_from_values(
            dict((nom, self.get_option(nom)) for nom in CLIENT_OPTIONS)
        )

        regions = settings.regions or self._regions(settings)
        report = discovery.DiscoveryReport()

        # L'index réseau coûte trois appels par région et par projet, et il ne
        # sert qu'aux produits qui portent des cartes réseau privées. Le payer
        # pour un inventaire qui n'en demande aucun revenait à facturer douze
        # appels à personne.
        #
        # Le filtrage n'est volontairement pas plus fin que ça : couper aussi
        # quand `address_priority` ne cite que du public viderait en silence
        # `scaleway_private_ipv4` et `scaleway_private_networks`, dont un
        # `compose` peut dépendre. Ne pas appeler et ne rien rendre ne sont pas
        # la même chose.
        index = None
        if discovery.needs_network_index(settings.products):
            index = discovery.build_network_index(client, regions, settings.project_ids, report)
        else:
            self.display.vvv(
                "scaleway: aucun produit demandé ne joint de réseau privé, "
                "index IPAM et VPC non construit"
            )

        context = DiscoveryContext(
            zones=settings.zones,
            regions=regions,
            project_ids=settings.project_ids,
            organization_ids=settings.organization_ids,
            tags=settings.filters.api_tags(),
            states=settings.filters.states,
            include_raw=settings.include_raw,
            network=index,
        )

        resultat, decouverte = discovery.discover(
            client, context, settings.products, strict=settings.strict
        )
        report.api_calls += decouverte.api_calls
        report.providers.update(decouverte.providers)
        report.warnings.extend(decouverte.warnings)
        report.errors.extend(decouverte.errors)

        if settings.strict and report.errors:
            raise AnsibleError("la découverte a échoué : " + " ; ".join(report.errors))

        gardes, ecartes = filtering.apply(resultat.hosts, settings.filters)
        return {
            "hosts": [self._serialise(host) for host in gardes],
            "report": report.lines() + ["écartée : " + raison for raison in ecartes],
        }

    @staticmethod
    def _regions(settings):
        """Les régions à indexer, déduites des zones demandées ou déclarées."""
        zones = settings.zones or INSTANCE_ZONES
        return tuple(sorted(set(region_of(zone) for zone in zones if region_of(zone))))

    @staticmethod
    def _serialise(host):
        """Le modèle normalisé, en structures sérialisables."""
        return {
            "id": host.id,
            "product": host.product,
            "name": host.name,
            "organization_id": host.organization_id,
            "project_id": host.project_id,
            "region": host.region,
            "zone": host.zone,
            "state": host.state,
            "tags": list(host.tags),
            "public_ipv4": list(host.public_ipv4),
            "public_ipv6": list(host.public_ipv6),
            "private_ipv4": list(host.private_ipv4),
            "private_ipv6": list(host.private_ipv6),
            "private_networks": [a.to_variable() for a in host.private_networks],
            "metadata": dict(host.metadata),
            # `raw` traverse le cache comme le reste, converti en structures
            # simples. Sans ce passage, l'option `include_raw` était
            # entièrement inerte : documentée, comptée dans la clé de cache,
            # testée côté provider, et sans le moindre effet observable, parce
            # que tout run passe par cette sérialisation.
            "raw": _plain(host.raw),
        }

    @staticmethod
    def _deserialise(donnees):
        return InventoryHost(
            id=donnees["id"],
            product=donnees["product"],
            name=donnees.get("name"),
            organization_id=donnees.get("organization_id"),
            project_id=donnees.get("project_id"),
            region=donnees.get("region"),
            zone=donnees.get("zone"),
            state=donnees.get("state"),
            tags=tuple(donnees.get("tags") or ()),
            public_ipv4=tuple(donnees.get("public_ipv4") or ()),
            public_ipv6=tuple(donnees.get("public_ipv6") or ()),
            private_ipv4=tuple(donnees.get("private_ipv4") or ()),
            private_ipv6=tuple(donnees.get("private_ipv6") or ()),
            private_networks=tuple(
                NetworkAttachment(
                    private_network_id=reseau["id"],
                    private_network_name=reseau.get("name"),
                    vpc_id=reseau.get("vpc_id"),
                    vpc_name=reseau.get("vpc_name"),
                    ipv4=tuple(reseau.get("ipv4") or ()),
                    ipv6=tuple(reseau.get("ipv6") or ()),
                    mac_address=reseau.get("mac_address"),
                )
                for reseau in donnees.get("private_networks") or ()
            ),
            metadata=donnees.get("metadata") or {},
            raw=donnees.get("raw"),
        )

    def _populate(self, materiel, settings):
        """Pose les hosts, leurs variables et leurs groupes dans l'inventaire."""
        for ligne in materiel["report"]:
            self.display.vvv("scaleway: " + ligne)

        hosts = tuple(self._deserialise(donnees) for donnees in materiel["hosts"])
        attribues, collisions = assign_hostnames(hosts, settings.hostnames)
        for avertissement in collisions:
            self.display.warning("scaleway: " + avertissement)

        strict = settings.strict

        for host, nom in attribues:
            selection = select_ansible_host(host, settings.address)
            self.display.vvvv("scaleway: " + selection.explain(nom))

            if not selection.found and settings.require_address:
                self.display.warning("scaleway: %s écartée, %s" % (nom, selection.source))
                continue

            self.inventory.add_host(nom)
            if selection.found:
                self.inventory.set_variable(nom, "ansible_host", selection.address)

            variables = self._host_variables(host, selection)
            for cle, valeur in variables.items():
                self.inventory.set_variable(nom, cle, valeur)

            for groupe in group_names(host, settings.group_by):
                self.inventory.add_group(groupe)
                self.inventory.add_child(groupe, nom)

            # Les mécanismes natifs d'Ansible, appelés et non seulement hérités.
            # Le plugin officiel en hérite, les documente, et ne les appelle
            # jamais : `compose`, `groups` et `keyed_groups` y sont sans effet.
            self._set_composite_vars(self.get_option("compose"), variables, nom, strict)
            self._add_host_to_composed_groups(self.get_option("groups"), variables, nom, strict)
            self._add_host_to_keyed_groups(self.get_option("keyed_groups"), variables, nom, strict)

    @staticmethod
    def _host_variables(host, selection):
        """Les hostvars stables, celles sur lesquelles un playbook peut compter.

        `scaleway_id`, `scaleway_zone` et `scaleway_product` sont ce qui permet
        d'enchaîner sur les modules Day-2 sans lookup supplémentaire.
        """
        variables = {
            "scaleway_id": host.id,
            "scaleway_product": host.product,
            "scaleway_name": host.name,
            "scaleway_project_id": host.project_id,
            "scaleway_organization_id": host.organization_id,
            "scaleway_region": host.region,
            "scaleway_zone": host.zone,
            "scaleway_state": host.state,
            "scaleway_tags": list(host.tags),
            "scaleway_public_ipv4": list(host.public_ipv4),
            "scaleway_public_ipv6": list(host.public_ipv6),
            "scaleway_private_ipv4": list(host.private_ipv4),
            "scaleway_private_ipv6": list(host.private_ipv6),
            "scaleway_private_networks": [a.to_variable() for a in host.private_networks],
            "scaleway_address_source": selection.source,
        }
        if host.metadata:
            variables["scaleway_" + host.product] = dict(host.metadata)
        if host.raw is not None:
            variables["scaleway_raw"] = host.raw
        return variables
