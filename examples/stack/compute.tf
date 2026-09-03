# Les machines, et la seule porte publique.
#
# Trois étages : un bastion qui porte la seule adresse publique de la
# plateforme, un tier web sans adresse publique que le load balancer expose, et
# un tier applicatif sans adresse publique du tout, qui sort par la passerelle.
#
# Ce choix n'est pas décoratif pour ce dépôt : c'est lui qui fait de l'exemple
# une preuve du plugin d'inventaire. Un parc où toutes les machines ont une IP
# publique ne prouve rien de la sélection d'adresse par réseau privé, qui est
# précisément ce que ce plugin fait mieux que l'officiel.

resource "scaleway_iam_ssh_key" "exemple" {
  name       = "${local.prefixe}-cle"
  public_key = var.ssh_public_key
  # IAM est à l'échelle de l'organisation, pas du projet : cette clé est la
  # seule ressource de la stack qui sorte du projet dédié. Le contrôle de
  # résidu la surveille comme les autres, et c'est le différentiel qui décide.
}

# --- ce que chaque étage accepte ------------------------------------------

resource "scaleway_instance_security_group" "bastion" {
  name                   = "${local.prefixe}-bastion"
  description            = "SSH depuis Internet, et rien d'autre"
  tags                   = local.tags
  inbound_default_policy = "drop"
  # Sortie ouverte : le bastion doit pouvoir installer ses paquets.
  outbound_default_policy = "accept"

  inbound_rule {
    action = "accept"
    port   = 22
  }
}

resource "scaleway_instance_security_group" "web" {
  name                    = "${local.prefixe}-web"
  description             = "HTTP depuis le load balancer, SSH depuis le bastion"
  tags                    = local.tags
  inbound_default_policy  = "drop"
  outbound_default_policy = "accept"

  inbound_rule {
    action = "accept"
    port   = 80
  }

  inbound_rule {
    action = "accept"
    port   = 22
  }
}

resource "scaleway_instance_security_group" "app" {
  name                    = "${local.prefixe}-app"
  description             = "le port applicatif et SSH, depuis les réseaux privés"
  tags                    = local.tags
  inbound_default_policy  = "drop"
  outbound_default_policy = "accept"

  inbound_rule {
    action = "accept"
    port   = 8080
  }

  inbound_rule {
    action = "accept"
    port   = 22
  }
}

# --- le bastion, seule adresse publique -----------------------------------

resource "scaleway_instance_ip" "bastion" {
  tags = local.tags
}

resource "scaleway_instance_server" "bastion" {
  name              = "${local.prefixe}-bastion"
  type              = var.instance_type
  image             = "ubuntu_jammy"
  ip_id             = scaleway_instance_ip.bastion.id
  security_group_id = scaleway_instance_security_group.bastion.id
  tags              = concat(local.tags, ["role=bastion", "etage=gestion"])

  # `delete_on_termination` explicite, et c'est la correction d'un défaut
  # mesuré : le projet dédié portait déjà un volume de démarrage de 10 Go
  # orphelin, zéro référence, survivant à un serveur disparu. Supprimer un
  # serveur Scaleway ne supprime pas son volume si personne ne le demande.
  root_volume {
    size_in_gb            = 10
    delete_on_termination = true
  }
}

# **Une seule carte**, sur le réseau de gestion. Le bastion joint les autres
# tiers par le routage du VPC (`enable_routing`), pas en ayant un pied partout.
#
# La version à trois cartes se détruisait elle-même sur le cloud réel : les
# réseaux web et applicatif sont attachés à la passerelle publique avec
# `push_default_route`, donc le bastion recevait par DHCP une route par défaut
# vers la passerelle, et le chemin de retour de son trafic public disparaissait.
# Il répondait pendant une minute, puis plus jamais.
resource "scaleway_instance_private_nic" "bastion" {
  server_id          = scaleway_instance_server.bastion.id
  private_network_id = scaleway_vpc_private_network.gestion.id
}

# --- le tier web, exposé par le load balancer seulement --------------------

resource "scaleway_instance_server" "web" {
  count = var.web_count

  name              = "${local.prefixe}-web-${count.index + 1}"
  type              = var.instance_type
  image             = "ubuntu_jammy"
  security_group_id = scaleway_instance_security_group.web.id
  tags              = concat(local.tags, ["role=web", "etage=charge"])

  root_volume {
    size_in_gb            = 10
    delete_on_termination = true
  }
}

# L'adresse est réservée dans IPAM avant que la machine la porte. C'est ce qui
# permet au load balancer de nommer ses cibles : il attend des adresses, et une
# carte réseau n'expose que des identifiants IPAM.
resource "scaleway_ipam_ip" "web" {
  count = var.web_count

  tags = local.tags

  source {
    private_network_id = scaleway_vpc_private_network.web.id
  }
}

resource "scaleway_instance_private_nic" "web" {
  count = var.web_count

  server_id          = scaleway_instance_server.web[count.index].id
  private_network_id = scaleway_vpc_private_network.web.id
  ipam_ip_ids        = [scaleway_ipam_ip.web[count.index].id]
}

# --- le tier applicatif, sans aucune sortie directe ------------------------

# Le groupe de placement étale les machines applicatives sur des hyperviseurs
# distincts : perdre une lame ne doit pas emporter le tier entier.
resource "scaleway_instance_placement_group" "app" {
  name        = "${local.prefixe}-app"
  policy_type = "max_availability"
  tags        = local.tags
}

resource "scaleway_instance_server" "app" {
  for_each = var.app_servers

  name               = "${local.prefixe}-${each.key}"
  type               = var.instance_type
  image              = "ubuntu_jammy"
  security_group_id  = scaleway_instance_security_group.app.id
  placement_group_id = scaleway_instance_placement_group.app.id
  tags               = concat(local.tags, ["role=app", "etage=charge"])

  root_volume {
    size_in_gb            = 10
    delete_on_termination = true
  }

  additional_volume_ids = [scaleway_block_volume.donnees[each.key].id]
}

resource "scaleway_instance_private_nic" "app" {
  for_each = var.app_servers

  server_id          = scaleway_instance_server.app[each.key].id
  private_network_id = scaleway_vpc_private_network.app.id
}
