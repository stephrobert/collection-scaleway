# Le réseau : un VPC, trois réseaux privés, et une seule porte publique.
#
# **Un VPC et non deux, et c'est une correction plutôt qu'une simplification.**
# La première version copiait la stack de feint : deux VPC qui ne partagent
# aucun réseau, le bastion dans l'un, les tiers dans l'autre. Elle valide, elle
# s'applique, elle se détruit, et elle ne peut pas marcher : rien ne relie les
# deux, donc le bastion ne joint aucune machine.
#
# Ça ne se voit pas chez feint parce que leur stack déclare `mode: off` et ne
# démarre jamais rien : elle éprouve le plan de contrôle, ce qu'elle dit
# elle-même. Ici l'exemple doit **déployer une application**, donc la
# topologie doit porter du trafic, et une propriété qu'on ne peut pas prouver
# ne mérite pas d'être écrite.
#
# La séparation reste, mais là où elle se vérifie : trois réseaux privés
# distincts, et une liste de contrôle qui dit ce qui a le droit de traverser.

resource "scaleway_vpc" "plateforme" {
  name = "${local.prefixe}-plateforme"
  tags = local.tags

  # Le routage entre réseaux privés du même VPC. C'est **lui** qui permet au
  # bastion de joindre les tiers, et non une carte réseau dans chacun d'eux.
  #
  # La première version donnait trois cartes au bastion, une par réseau. Elle
  # marche contre l'émulateur et casse sur le cloud réel, de la pire façon :
  # deux de ces réseaux sont attachés à la passerelle publique avec
  # `push_default_route`, donc le bastion recevait par DHCP une route par
  # défaut vers la passerelle **une minute après son démarrage**, et ses
  # réponses au trafic public repartaient par là. SSH marchait à la première
  # minute puis mourait, sans qu'aucune API ne signale quoi que ce soit.
  #
  # Le symptôme, « Connection timed out », désigne le pare-feu ou le démon.
  # C'était le routage.
  enable_routing = true
}

resource "scaleway_vpc_private_network" "gestion" {
  name   = "${local.prefixe}-gestion"
  vpc_id = scaleway_vpc.plateforme.id
  tags   = local.tags

  ipv4_subnet {
    subnet = "10.10.0.0/24"
  }
}

resource "scaleway_vpc_private_network" "web" {
  name   = "${local.prefixe}-web"
  vpc_id = scaleway_vpc.plateforme.id
  tags   = local.tags

  ipv4_subnet {
    subnet = "10.20.0.0/24"
  }
}

resource "scaleway_vpc_private_network" "app" {
  name   = "${local.prefixe}-app"
  vpc_id = scaleway_vpc.plateforme.id
  tags   = local.tags

  ipv4_subnet {
    subnet = "10.30.0.0/24"
  }
}

# La liste de contrôle, écrite en refus par défaut : ce qui n'est pas nommé ne
# passe pas. C'est l'inverse de la posture par défaut d'un VPC, et la seule qui
# se relise.
locals {
  # Le complement de 10.0.0.0/8 dans 0.0.0.0/0, en huit prefixes.
  #
  # Une ACL de VPC n'a pas d'operateur de negation, et une regle de sortie
  # ecrite vers `0.0.0.0/0` couvre aussi le VPC : elle reautoriserait tout le
  # trafic interne que les regles precedentes viennent de restreindre.
  #
  # On pourrait esperer qu'un `drop` place avant elle la neutralise. Ce depot ne
  # construit rien sur une esperance : nommer le complement de 10.0.0.0/8 rend
  # la question sans objet, parce que la regle de sortie ne rencontre alors
  # jamais une adresse du VPC. C'est plus long a lire, et ca ne depend d'aucune
  # hypothese sur l'ordre d'evaluation.
  internet = [
    "0.0.0.0/5",
    "8.0.0.0/7",
    "11.0.0.0/8",
    "12.0.0.0/6",
    "16.0.0.0/4",
    "32.0.0.0/3",
    "64.0.0.0/2",
    "128.0.0.0/1",
  ]
}

resource "scaleway_vpc_acl" "plateforme" {
  vpc_id         = scaleway_vpc.plateforme.id
  is_ipv6        = false
  default_policy = "drop"

  # **Toute regle porte ses ports source, et c'est ce qui la rend vivante.**
  #
  # Le provider envoie `src_port_low = 0, src_port_high = 0` quand on ne les
  # renseigne pas. Aucun paquet reel n'a le port source 0, donc la regle ne
  # correspond a rien et tout tombe dans `default_policy`. Les regles de cette
  # stack ont vecu ainsi : ecrites, stockees par l'API, et totalement inertes.
  # Le symptome etait un silence complet entre les tiers, que
  # `scw vpc rule get vpc-id=...` a explique en une ligne la ou trois playbooks
  # n'avaient rien dit.

  rules {
    protocol      = "TCP"
    source        = "10.0.0.0/8"
    destination   = "10.0.0.0/8"
    src_port_low  = 0
    src_port_high = 65535
    dst_port_low  = 22
    dst_port_high = 22
    action        = "accept"
    description   = "l administration par SSH a l interieur du VPC"
  }

  rules {
    protocol      = "TCP"
    source        = "10.0.0.0/8"
    destination   = "10.20.0.0/24"
    src_port_low  = 0
    src_port_high = 65535
    dst_port_low  = 80
    dst_port_high = 80
    action        = "accept"
    description   = "le load balancer joint le tier web"
  }

  rules {
    protocol      = "TCP"
    source        = "10.20.0.0/24"
    destination   = "10.30.0.0/24"
    src_port_low  = 0
    src_port_high = 65535
    dst_port_low  = 8080
    dst_port_high = 8080
    action        = "accept"
    description   = "le tier web joint le tier applicatif, et rien d autre"
  }

  # Le trafic de retour interne, et c'est **la** regle qu'on oublie : une ACL
  # de VPC est sans etat. Elle juge chaque paquet isolement, sans savoir qu'il
  # repond a une connexion deja autorisee. Mesure : avec les trois regles
  # ci-dessus seules, aucun rebond SSH n'aboutit.
  rules {
    protocol      = "TCP"
    source        = "10.0.0.0/8"
    destination   = "10.0.0.0/8"
    src_port_low  = 0
    src_port_high = 65535
    dst_port_low  = 1024
    dst_port_high = 65535
    action        = "accept"
    description   = "le trafic de retour interne, une ACL etant sans etat"
  }

  # La sortie vers l'internet, et son retour. Les tiers n'ont aucune adresse
  # publique et passent par la passerelle ; il leur faut quand meme installer
  # leurs paquets.
  dynamic "rules" {
    for_each = local.internet
    content {
      protocol      = "ANY"
      source        = "10.0.0.0/8"
      destination   = rules.value
      src_port_low  = 0
      src_port_high = 65535
      dst_port_low  = 0
      dst_port_high = 65535
      action        = "accept"
      description   = "sortie vers ${rules.value}"
    }
  }

  dynamic "rules" {
    for_each = local.internet
    content {
      protocol      = "ANY"
      source        = rules.value
      destination   = "10.0.0.0/8"
      src_port_low  = 0
      src_port_high = 65535
      dst_port_low  = 1024
      dst_port_high = 65535
      action        = "accept"
      description   = "retour depuis ${rules.value}"
    }
  }
}

# La passerelle publique porte la sortie du tier applicatif : ces machines
# n'ont aucune adresse publique, et c'est délibéré. Si un paquet s'y installe,
# c'est que la passerelle fonctionne.
# **L'IP est déclarée, et c'est une correction payée deux fois.** Elle avait été
# retirée le 14 septembre 2026, en croyant que l'IP flexible forçait un mode
# *Legacy* responsable d'une allocation bloquée. Les deux moitiés étaient
# fausses : la passerelle bloquée portait `is_legacy: false`, et elle n'était
# pas bloquée mais lente, passée en `running` après cinquante-six minutes.
#
# Le retrait a **créé un résidu** au run suivant : sans `ip_id`, la passerelle
# s'alloue une adresse que Terraform ne connaît pas, donc `destroy` emporte la
# passerelle et laisse l'IP derrière, facturée et sans propriétaire. C'est la
# règle que ce fichier énonce ailleurs, appliquée contre lui-même : ce que
# Terraform ne déclare pas, Terraform ne détruit pas.
resource "scaleway_vpc_public_gateway_ip" "sortie" {
  tags = local.tags
}

# **Le délai d'attente est allongé, et c'est la seule correction qui tienne.**
# Le mode *Legacy* n'était pas en cause, l'IP flexible non plus. Un abandon
# d'attente ne laisse pas une ressource à moitié créée : il laisse une ressource
# **entière et hors état**. Le `destroy` qui a suivi a emporté dix-huit
# ressources et ignoré celle-là, qui a survécu, facturée, et bloquée en
# `allocating` pendant que l'API refusait de la supprimer parce qu'un état
# transitoire ne se supprime pas.
#
# `residue.py` l'a nommée avec son identifiant, ce qui est son travail, mais la
# nommer après coup coûte une suppression à la main. Trente minutes laissent la
# place à une création lente sans changer ce qui est juste.
resource "scaleway_vpc_public_gateway" "sortie" {
  name  = "${local.prefixe}-sortie"
  type  = "VPC-GW-S"
  ip_id = scaleway_vpc_public_gateway_ip.sortie.id
  tags  = local.tags

  timeouts {
    # **Soixante minutes, et c'est une mesure et non une marge.** Le 14 septembre
    # 2026 sur le compte réel, une passerelle est passée en `running`
    # cinquante-six minutes après sa création. Le provider attend dix minutes
    # par défaut : il a abandonné, n'a jamais enregistré la ressource, et le
    # `destroy` qui a suivi a emporté dix-huit ressources en laissant celle-là,
    # facturée et hors état. Trente minutes n'auraient pas suffi non plus.
    create = "60m"
    delete = "60m"
  }
}

resource "scaleway_vpc_gateway_network" "app" {
  gateway_id         = scaleway_vpc_public_gateway.sortie.id
  private_network_id = scaleway_vpc_private_network.app.id
  enable_masquerade  = true

  ipam_config {
    push_default_route = true
  }
}

# Le tier web sort lui aussi par la passerelle : il doit pouvoir installer
# nginx, et il n'a pas plus d'adresse publique que le tier applicatif.
#
# Le bastion n'est **pas** sur ces réseaux : il ne doit jamais recevoir cette
# route par défaut, sous peine de perdre le chemin de retour de son trafic
# public.
resource "scaleway_vpc_gateway_network" "web" {
  gateway_id         = scaleway_vpc_public_gateway.sortie.id
  private_network_id = scaleway_vpc_private_network.web.id
  enable_masquerade  = true

  ipam_config {
    push_default_route = true
  }
}
