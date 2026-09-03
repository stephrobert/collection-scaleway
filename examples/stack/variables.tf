# Ce que la stack accepte, et pourquoi chaque valeur existe.

variable "endpoint" {
  description = "URL de l'émulateur. Vide pour viser le vrai Scaleway."
  type        = string
  default     = ""
}

variable "project_id" {
  description = "Projet Scaleway visé. Ignoré quand `endpoint` est renseigné."
  type        = string
  default     = null
}

variable "region" {
  type    = string
  default = "fr-par"
}

variable "zone" {
  type    = string
  default = "fr-par-1"
}

# Le marqueur qui rend chaque ressource attribuable à une exécution précise.
#
# Il ne sert pas à faire joli : le contrôle de résidu compare l'état du compte
# avant et après, et ce marqueur est ce qui permet de dire, devant une
# ressource survivante, de quelle exécution elle vient. Sans lui, un résidu est
# une énigme.
variable "run_id" {
  description = "Marqueur unique de l'exécution, porté par le nom et les tags."
  type        = string
}

variable "web_count" {
  description = "Machines du tier web, derrière le load balancer."
  type        = number
  default     = 2
}

variable "app_servers" {
  description = "Le tier applicatif, une entrée par machine nommée."
  type = map(object({
    data_gb = optional(number, 10)
  }))
  default = {
    worker-a = {}
    worker-b = { data_gb = 20 }
  }
}

variable "instance_type" {
  description = "Type commercial des machines. DEV1-S est le moins cher qui tienne."
  type        = string
  default     = "DEV1-S"
}

variable "ssh_public_key" {
  description = "Clé publique poussée dans le projet, pour que l'exemple puisse se connecter."
  type        = string
}

locals {
  # Chaque ressource porte ces tags. `terraform destroy` les emporte toutes,
  # et quand il échoue, ce sont eux qui disent quoi supprimer à la main.
  tags = ["ansible-collection-scaleway", "exemple", var.run_id]

  # Un préfixe court : Scaleway limite la longueur de certains noms, et un nom
  # tronqué n'est plus attribuable.
  prefixe = "acs-${var.run_id}"
}
