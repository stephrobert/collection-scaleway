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
