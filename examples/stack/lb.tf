# Le load balancer devant le tier web.
#
# C'est la seule façon d'atteindre l'application depuis Internet : les machines
# web n'ont pas d'adresse publique, et c'est ce qui fait de la vérification de
# bout en bout une vraie preuve. Une requête qui aboutit a réellement traversé
# le load balancer, le réseau privé et le serveur web.

resource "scaleway_lb_ip" "public" {
  tags = local.tags
}

resource "scaleway_lb" "web" {
  name   = "${local.prefixe}-web"
  type   = "LB-S"
  ip_ids = [scaleway_lb_ip.public.id]
  tags   = local.tags

  private_network {
    private_network_id = scaleway_vpc_private_network.web.id
  }
}

resource "scaleway_lb_backend" "web" {
  lb_id            = scaleway_lb.web.id
  name             = "${local.prefixe}-web"
  forward_protocol = "http"
  forward_port     = 80

  # Les cibles sont les adresses réservées dans IPAM, pas des identifiants :
  # le load balancer joint le tier web par le réseau privé qu'il a rejoint.
  server_ips = [for ip in scaleway_ipam_ip.web : ip.address]

  health_check_http {
    uri = "/"
  }
}

resource "scaleway_lb_frontend" "web" {
  lb_id        = scaleway_lb.web.id
  backend_id   = scaleway_lb_backend.web.id
  name         = "${local.prefixe}-web"
  inbound_port = 80
}

# Une liste de contrôle sur le frontend, et deux raisons de l'écrire.
#
# **Elle rend la plateforme réaliste.** Un load balancer public sans aucune
# règle est une porte ouverte ; un vrai projet en pose une, ne serait-ce que
# pour dire ce qui a le droit d'entrer.
#
# **Elle donne une cible aux modules `lb_acl` et `lb_acl_info`.** Sans elle, ces
# deux-là ne pouvaient être exercés par aucun playbook, et un module que rien
# n'appelle est un module dont on ignore s'il marche. La règle du dépôt le dit :
# une issue close sans que l'exemple ait bougé ne prouve rien.
resource "scaleway_lb_acl" "web" {
  frontend_id = scaleway_lb_frontend.web.id
  name        = "${local.prefixe}-web"
  index       = 0

  action {
    type = "allow"
  }

  match {
    ip_subnet = ["0.0.0.0/0"]
  }
}


# **Un second backend et une route, pour que `lb_route` ait une cible.**
#
# Un backend ne coûte rien : c'est de la configuration dans le load balancer
# déjà facturé, pas une ressource de plus. Il pointe sur les mêmes serveurs web
# et sur le même port : ce qu'on veut prouver est qu'un module sait relire et
# réécrire une route, pas qu'un second service existe.
#
# La route se déclenche sur l'en-tête `Host`, ce que le frontend HTTP de cette
# stack permet. `match_sni` demanderait du TLS, donc un certificat, donc un
# domaine.
resource "scaleway_lb_backend" "secondaire" {
  lb_id            = scaleway_lb.web.id
  name             = "${local.prefixe}-secondaire"
  forward_protocol = "http"
  forward_port     = 80
  server_ips       = [for ip in scaleway_ipam_ip.web : ip.address]
}

resource "scaleway_lb_route" "secondaire" {
  frontend_id       = scaleway_lb_frontend.web.id
  backend_id        = scaleway_lb_backend.secondaire.id
  match_host_header = "secondaire.exemple.invalid"
}
