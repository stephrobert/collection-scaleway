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
