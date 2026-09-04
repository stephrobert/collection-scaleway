# Ce que la stack rend, et ce qui en fait la valeur pour l'exemple Ansible.
#
# L'inventaire dynamique découvre les machines tout seul : ces sorties ne
# servent donc pas à les lister, ce serait doubler ce qu'on veut prouver. Elles
# donnent ce que l'inventaire ne peut pas connaître : par où entrer, et par où
# vérifier.

output "bastion_ip" {
  description = "La seule adresse publique de la plateforme. Point d'entrée SSH."
  value       = scaleway_instance_ip.bastion.address
}

output "application_url" {
  description = "L'adresse par laquelle une requête traverse toute la chaîne."
  value       = "http://${scaleway_lb_ip.public.ip_address}"
}

output "run_id" {
  description = "Le marqueur porté par chaque ressource, pour le contrôle de résidu."
  value       = var.run_id
}

output "reseau_web" {
  description = "Le réseau privé par lequel l'inventaire doit joindre le tier web."
  value       = scaleway_vpc_private_network.web.name
}

output "attendu" {
  description = "Ce que l'exemple doit trouver. Un compte, pas une liste : c'est l'inventaire qui liste."
  value = {
    bastion = 1
    web     = var.web_count
    app     = length(var.app_servers)
    total   = 1 + var.web_count + length(var.app_servers)
  }
}

output "image_doree" {
  description = "L'identifiant d'API de l'image d'or, ou la chaîne vide quand la cible ne sait pas la bâtir."
  # `try` plutôt qu'un index nu : la ressource porte un `count` conditionnel,
  # et une sortie qui casse quand la cible change ne rend service à personne.
  #
  # **Un identifiant Terraform n'est pas un identifiant d'API.** Le provider
  # préfixe les siens par la portée, `fr-par-1/<uuid>`, et le passer tel quel à
  # un module produit l'URL `/images/fr-par-1/<uuid>`, qui rend un 404
  # générique : pas celui de l'API, celui du serveur web devant elle. Le
  # message ne ressemble donc à rien de ce que le runtime sait interpréter.
  #
  # `reverse(split(...))[0]` plutôt qu'un index fixe : le jour où la portée
  # gagne un segment, prendre le dernier reste juste.
  value = try(reverse(split("/", scaleway_instance_image.reference[0].id))[0], "")
}


output "volume_instance" {
  description = "Le volume que l'API Instance voit, cible de `instance_volume`."
  value       = scaleway_instance_volume.vu_par_instance.id
}

output "route_lb" {
  description = "La route du frontend, cible de `lb_route`."
  value       = scaleway_lb_route.secondaire.id
}
