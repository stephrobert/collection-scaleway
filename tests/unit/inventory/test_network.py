"""La jointure réseau : ce qu'elle produit, et ce qu'elle coûte.

Deux choses se prouvent ici, et la seconde est la raison d'être du module :

* la relation est **conservée** : quelle machine, sur quel réseau, dans quel
  VPC, avec quelle adresse ; le plugin officiel garde une adresse et jette le
  reste ;
* la jointure est **linéaire en cartes réseau**. Ce n'est pas une mesure de
  durée, qui dépendrait de la machine qui l'exécute : on compte les
  consultations d'index, et on exige qu'elles ne dépendent pas de la taille de
  l'index.
"""

from __future__ import annotations

from ansible_collections.local.scaleway.plugins.module_utils.inventory.network import (
    IpamAddress,
    NetworkIndex,
    NicRef,
    PrivateNetworkInfo,
    attach,
    build_index,
    flatten,
    strip_netmask,
)


class MappingCompteur(dict):
    """Un index qui compte ses consultations. Aucune horloge, donc aucun aléa."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.lectures = 0

    def get(self, key, default=None):  # type: ignore[override]
        self.lectures += 1
        return super().get(key, default)


def test_le_masque_est_retire_car_ansible_veut_une_adresse() -> None:
    assert strip_netmask("10.0.0.5/22") == "10.0.0.5"
    assert strip_netmask("10.0.0.5") == "10.0.0.5"


def test_une_adresse_sans_ressource_nentre_pas_dans_lindex() -> None:
    """Une IP libre existe dans IPAM et n'appartient à aucune machine."""
    index = build_index((IpamAddress("10.0.0.9", False, resource_id=None),))
    assert index.addresses_by_resource == {}
    assert index.address_count == 0


def test_la_jointure_conserve_le_reseau_et_le_vpc() -> None:
    index = build_index(
        addresses=(IpamAddress("10.10.0.5/22", False, "nic-1", "pn-1", "vpc-1", "02:00:00:aa"),),
        networks=(PrivateNetworkInfo("pn-1", "backend", "vpc-1"),),
        vpc_names={"vpc-1": "socle"},
    )
    (rattachement,) = attach((NicRef("nic-1", "pn-1", "02:00:00:aa"),), index)

    assert rattachement.private_network_id == "pn-1"
    assert rattachement.private_network_name == "backend"
    assert rattachement.vpc_id == "vpc-1"
    assert rattachement.vpc_name == "socle"
    assert rattachement.ipv4 == ("10.10.0.5",)
    assert rattachement.mac_address == "02:00:00:aa"


def test_une_machine_sur_deux_reseaux_garde_les_deux() -> None:
    """Le défaut central du plugin officiel : `vpc_ipv4` n'en garde qu'une."""
    index = build_index(
        addresses=(
            IpamAddress("10.10.0.5/22", False, "nic-1", "pn-1"),
            IpamAddress("10.20.0.7/22", False, "nic-2", "pn-2"),
        ),
        networks=(
            PrivateNetworkInfo("pn-1", "backend", "vpc-1"),
            PrivateNetworkInfo("pn-2", "monitoring", "vpc-1"),
        ),
    )
    rattachements = attach((NicRef("nic-1", "pn-1"), NicRef("nic-2", "pn-2")), index)

    assert [a.private_network_name for a in rattachements] == ["backend", "monitoring"]
    assert flatten(rattachements) == (("10.10.0.5", "10.20.0.7"), ())


def test_ipv4_et_ipv6_dun_meme_reseau_sont_separees() -> None:
    index = build_index(
        addresses=(
            IpamAddress("10.10.0.5/22", False, "nic-1", "pn-1"),
            IpamAddress("2001:db8::5/64", True, "nic-1", "pn-1"),
        ),
        networks=(PrivateNetworkInfo("pn-1", "backend"),),
    )
    (rattachement,) = attach((NicRef("nic-1", "pn-1"),), index)
    assert rattachement.ipv4 == ("10.10.0.5",)
    assert rattachement.ipv6 == ("2001:db8::5",)


def test_le_reseau_se_deduit_de_ladresse_quand_la_carte_ne_le_dit_pas() -> None:
    """Certaines réponses ne portent pas `private_network_id` sur la carte."""
    index = build_index(
        addresses=(IpamAddress("10.10.0.5", False, "nic-1", "pn-1", "vpc-1"),),
    )
    (rattachement,) = attach((NicRef("nic-1"),), index)
    assert rattachement.private_network_id == "pn-1"
    assert rattachement.vpc_id == "vpc-1"


def test_une_carte_sans_reseau_ni_adresse_est_ignoree() -> None:
    assert attach((NicRef("nic-orpheline"),), build_index(())) == ()


def test_un_reseau_inconnu_de_lindex_garde_son_identifiant() -> None:
    """Un droit manquant sur VPC ne doit pas faire disparaître l'adresse."""
    index = build_index((IpamAddress("10.10.0.5", False, "nic-1", "pn-1"),))
    (rattachement,) = attach((NicRef("nic-1", "pn-1"),), index)
    assert rattachement.private_network_id == "pn-1"
    assert rattachement.private_network_name is None
    assert rattachement.ipv4 == ("10.10.0.5",)


def test_lordre_des_rattachements_ne_depend_pas_de_lordre_des_cartes() -> None:
    """La sélection d'adresse s'appuie sur cet ordre : il doit être stable."""
    index = build_index(
        addresses=(
            IpamAddress("10.10.0.5", False, "nic-1", "pn-1"),
            IpamAddress("10.20.0.7", False, "nic-2", "pn-2"),
        ),
        networks=(
            PrivateNetworkInfo("pn-1", "backend"),
            PrivateNetworkInfo("pn-2", "monitoring"),
        ),
    )
    cartes = (NicRef("nic-1", "pn-1"), NicRef("nic-2", "pn-2"))
    a_lendroit = attach(cartes, index)
    a_lenvers = attach(tuple(reversed(cartes)), index)
    assert [a.private_network_name for a in a_lendroit] == ["backend", "monitoring"]
    assert a_lendroit == a_lenvers


def test_la_jointure_ne_parcourt_pas_lindex() -> None:
    """La preuve de complexité : deux cartes, deux consultations, sur 5 000 adresses.

    Si la jointure balayait l'index, ce nombre grandirait avec lui. Il ne
    bouge pas, donc le coût est en `O(cartes)`.
    """
    adresses = tuple(
        IpamAddress(f"10.0.{i // 256}.{i % 256}", False, f"nic-{i}", "pn-1") for i in range(5000)
    )
    construit = build_index(adresses, (PrivateNetworkInfo("pn-1", "backend"),))
    compteur = MappingCompteur(construit.addresses_by_resource)
    index = NetworkIndex(compteur, construit.networks, construit.vpc_names)

    attach((NicRef("nic-1", "pn-1"), NicRef("nic-2", "pn-1")), index)
    assert compteur.lectures == 2


def test_deux_mille_machines_se_joignent_sans_explosion_quadratique() -> None:
    """Un parc à l'échelle : 2 000 machines, deux cartes réseau chacune."""
    machines = 2000
    adresses = tuple(
        IpamAddress(f"10.{i // 256}.{i % 256}.1", False, f"nic-{i}-{c}", f"pn-{c}")
        for i in range(machines)
        for c in (0, 1)
    )
    construit = build_index(
        adresses,
        (PrivateNetworkInfo("pn-0", "backend"), PrivateNetworkInfo("pn-1", "monitoring")),
    )
    compteur = MappingCompteur(construit.addresses_by_resource)
    index = NetworkIndex(compteur, construit.networks, construit.vpc_names)

    for i in range(machines):
        rattachements = attach((NicRef(f"nic-{i}-0", "pn-0"), NicRef(f"nic-{i}-1", "pn-1")), index)
        assert len(rattachements) == 2

    # Une consultation par carte réseau, et pas une de plus : le coût total est
    # linéaire, là où une jointure naïve ferait machines x adresses.
    assert compteur.lectures == machines * 2
