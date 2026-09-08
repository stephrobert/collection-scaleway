# Deux certificats et un frontend TLS, et trois raisons de les écrire.
#
# **`lb_certificate` n'avait aucune cible.** Il fait partie des modules que
# l'exemple n'appelait jamais, et un module que rien n'exerce est un module dont
# on ignore s'il marche. La règle du dépôt le dit : une issue close sans que
# l'exemple ait bougé ne prouve rien.
#
# **`lb_frontend.certificate_ids` est la seule liste de références restée sans
# mesure** (#119). L'API pourrait la rendre triée, dédoublonnée, ou dans l'ordre
# demandé ; tant que personne ne l'a observée, le repli `ordered_list` est une
# hypothèse. Deux certificats suffisent à ce que l'ordre veuille dire quelque
# chose.
#
# **Un certificat ne coûte rien.** C'est de la configuration dans le load
# balancer déjà facturé, pas une ressource de plus.
#
# ## Pourquoi ce fichier ne s'applique qu'au cloud réel
#
# feint décline `CreateCertificate`, et sa raison est écrite : rien n'y termine
# TLS, donc un certificat servi par l'émulateur serait un identifiant posé sur
# du matériel cryptographique qui ne signe rien. C'est une décision juste, et
# elle rend cette mesure impossible ailleurs que sur le vrai compte.
#
# Le `count` n'est donc pas un contournement : c'est la seule chose que
# l'émulateur ne peut pas servir, isolée et nommée, dans une stack qui reste
# une pour deux cibles.

locals {
  # Une seule condition, écrite une fois : ce fichier vise le cloud réel.
  certificats = var.endpoint == "" ? 1 : 0
}

# Le matériel cryptographique est produit à l'application, jamais versionné.
# Un certificat écrit dans le dépôt expirerait, et un dépôt qui porte une clé
# privée est un dépôt qu'on ne peut plus rendre public.
resource "tls_private_key" "mesure" {
  count = local.certificats

  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_self_signed_cert" "mesure" {
  count = local.certificats * 2

  private_key_pem = tls_private_key.mesure[0].private_key_pem

  # Deux certificats qui se distinguent par leur nom commun : sans ça, le load
  # balancer les verrait identiques et l'ordre ne prouverait rien.
  subject {
    common_name  = "mesure-${count.index + 1}.exemple.invalid"
    organization = "collection-scaleway"
  }

  # **Scaleway exige des noms DNS, et le `common_name` n'en est pas un.**
  # Mesuré sur le compte réel le 8 septembre 2026 : un certificat qui n'en porte
  # aucun est refusé à la création, avec
  #
  #     certificate_chain does not respect constraint, this certificate chain
  #     is invalid (DNS Names of public key certificate is empty)
  #
  # `.invalid` est le domaine que la RFC 2606 réserve précisément pour ça :
  # il ne résout nulle part, donc ce certificat ne peut pas être pris pour un
  # certificat de production égaré.
  dns_names = ["mesure-${count.index + 1}.exemple.invalid"]

  validity_period_hours = 24
  allowed_uses          = ["key_encipherment", "digital_signature", "server_auth"]
}

resource "scaleway_lb_certificate" "mesure" {
  count = local.certificats * 2

  lb_id = scaleway_lb.web.id
  name  = "${local.prefixe}-mesure-${count.index + 1}"

  custom_certificate {
    certificate_chain = join(
      "",
      [
        tls_self_signed_cert.mesure[count.index].cert_pem,
        tls_private_key.mesure[0].private_key_pem,
      ]
    )
  }
}

# Le frontend TLS qui les porte.
#
# Un frontend HTTP n'a rien à faire d'un certificat : le lier à un port 80
# serait une configuration que personne n'écrit, et l'API pourrait la refuser au
# milieu du run. Le port 443 est ce qu'un vrai projet fait, et c'est ce qui rend
# la mesure défendable.
#
# L'ordre déclaré ici est celui que la mesure compare : `[1, 2]` à la création,
# et le playbook demandera `[2, 1]` pour voir ce que l'API en fait.
resource "scaleway_lb_frontend" "tls" {
  count = local.certificats

  lb_id           = scaleway_lb.web.id
  backend_id      = scaleway_lb_backend.web.id
  name            = "${local.prefixe}-tls"
  inbound_port    = 443
  certificate_ids = [for c in scaleway_lb_certificate.mesure : c.id]
}
