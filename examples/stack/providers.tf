# Le fournisseur, et la seule chose qui change entre l'émulateur et le cloud.
#
# Une stack, deux cibles. `endpoint` vide vise le vrai Scaleway et laisse le
# fournisseur lire les identifiants de l'environnement, comme n'importe quel
# projet ; `endpoint` renseigné vise l'émulateur et fournit les identifiants
# factices qu'il accepte. Écrire deux stacks pour deux cibles reviendrait à ne
# prouver ni l'une ni l'autre : ce qui tourne contre l'émulateur ne serait plus
# ce qui tourne contre le cloud.

terraform {
  required_version = ">= 1.7.0"
  required_providers {
    scaleway = {
      source = "scaleway/scaleway"
      # Version exacte, et pas une contrainte flottante. feint a mesuré ce que
      # coûte l'alternative : une CI rouge à l'heure où 2.81.0 est sortie, sans
      # un seul changement de leur côté.
      version = "2.81.0"
    }
  }
}

provider "scaleway" {
  # Contre l'émulateur, tout est fourni ici. Contre le cloud réel, `null`
  # laisse le fournisseur lire `SCW_ACCESS_KEY`, `SCW_SECRET_KEY`,
  # `SCW_DEFAULT_PROJECT_ID` et le fichier de configuration, dans cet ordre.
  api_url         = var.endpoint != "" ? var.endpoint : null
  access_key      = var.endpoint != "" ? "SCWXXXXXXXXXXXXXXXXX" : null
  secret_key      = var.endpoint != "" ? "11111111-1111-1111-1111-111111111111" : null
  project_id      = var.endpoint != "" ? "11111111-1111-1111-1111-111111111111" : var.project_id
  organization_id = var.endpoint != "" ? "11111111-1111-1111-1111-111111111111" : null
  region          = var.region
  zone            = var.zone
}
