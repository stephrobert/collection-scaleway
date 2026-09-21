# Un cluster Kubernetes managé, et le pool qui porte ses nœuds.
#
# **Pourquoi il est là.** Dix-neuf modules Kubernetes sont livrés, et aucun
# n'avait jamais appelé une API : chargés par Ansible, leurs paramètres
# construits, leur documentation publiée, et rien de plus. C'est l'étage « porté
# par un module », pas l'étage « éprouvé », et la collection publiait leur nom
# comme si de rien n'était (#249).
#
# **Pourquoi seulement sur le cloud réel.** Mesuré : feint rend
# `501 not_emulated` sur toute l'API `/k8s/v1`. Un cluster déclaré pour
# l'émulateur échouerait à l'application, et le déclarer quand même pour « faire
# comme si » produirait un plan que rien ne peut appliquer. Même condition que
# les certificats, écrite de la même façon.
#
# **Ce que ça coûte, et c'est assumé.** La création prend plusieurs minutes, et
# les nœuds sont facturés tant qu'ils vivent. Ils vivent le temps du run, comme
# les machines que cette stack crée déjà, et `terraform destroy` les emporte
# dans le même `finally`. `residue.py` inventorie désormais `k8s.cluster` : sans
# ça, « aucun résidu » aurait été un faux vert sur la ressource la plus chère de
# cette plateforme.

locals {
  # Une seule condition, écrite une fois : ce fichier vise le cloud réel.
  kapsule = var.endpoint == "" ? 1 : 0
}

resource "scaleway_k8s_cluster" "mesure" {
  count = local.kapsule

  name = "${local.prefixe}-mesure"
  tags = local.tags

  # **La version n'est pas écrite en dur ici non plus.** Les versions
  # disponibles changent tous les mois, et une version figée dans un fichier
  # versionné échoue un jour sans que rien ne l'ait annoncé. Le provider prend
  # la dernière que la région propose.
  version = data.scaleway_k8s_version.derniere[0].name
  cni     = "cilium"

  # **`delete_additional_resources` est ce qui tient la promesse de résidu
  # zéro.** Un cluster Kapsule crée pour son compte des volumes de PVC et des
  # load balancers de service ; sans cette option, `terraform destroy` détruit
  # le cluster et les laisse derrière, facturés et sans propriétaire visible.
  # C'est le piège le plus courant de ce produit, et il est exactement de la
  # même famille que le volume qui survit à un serveur supprimé.
  #
  # **Ce qu'elle n'emporte pas, mesuré le 14 septembre 2026 : le groupe de
  # sécurité que Kapsule crée pour le cluster.** `residue.py` l'a nommé après la
  # destruction, « Kapsule default security group ».
  #
  # La question posée au run précédent est tranchée : ce n'est pas un retard de
  # suppression asynchrone. Le groupe a été relevé trente secondes, une minute,
  # une minute et demie, deux minutes et trois minutes après la destruction du
  # cluster, et il était toujours là aux cinq relevés. C'est un orphelin par
  # conception, et `delete_additional_resources` ne le couvre pas.
  #
  # Il ne porte pas le préfixe de la plateforme, donc les gardes de compte qui
  # filtrent par préfixe l'ignorent ; c'est `residue.py`, qui compare le compte
  # entier à sa référence, qui l'attrape. La suppression reste manuelle tant que
  # rien ne la prend en charge.
  delete_additional_resources = true

  # **Son propre réseau privé, et pas celui du tier web.** Mesuré sur le compte
  # réel : attacher le cluster à `web` rend
  # `private_network_id does not respect constraint, Private Network subnets are
  # too short`. Les réseaux de la stack sont en /24, et Kapsule a besoin de plus
  # large pour ses nœuds et ses services.
  #
  # L'API sait en créer un toute seule quand on n'en donne aucun, et c'est
  # précisément ce qu'on ne veut pas : **ce que Terraform ne déclare pas,
  # Terraform ne détruit pas**. Un réseau créé implicitement survivrait au
  # `destroy` sans que rien ne le nomme, et c'est la définition d'un résidu.
  private_network_id = scaleway_vpc_private_network.kapsule[0].id

  # **Deux valeurs, et leur ordre est la mesure.** `k8s_cluster` compare cette
  # liste **dans l'ordre**, comme `admission_plugins` et `feature_gates`, et
  # personne n'a vérifié que l'API le conserve. `certificate_ids` a montré
  # qu'elle ne le garantit pas : écrit `[a, b]`, relu `[b, a]` le 8 septembre
  # 2026, conservé le 16, inversé à la création un tir plus tôt.
  #
  # Si l'ordre n'est pas tenu ici non plus, `k8s_cluster` rend `changed` sur une
  # écriture qui ne change rien, par intermittence, ce qui passe les contrôles
  # la plupart du temps (#290, #278).
  #
  # Des noms, pas des adresses : un SAN de certificat ne crée rien, ne coûte
  # rien et ne touche pas aux nœuds. C'est la seule des trois listes qu'on peut
  # déclarer sans redéployer le plan de contrôle.
  apiserver_cert_sans = ["premier.exemple.invalid", "second.exemple.invalid"]
}

# Le réseau du cluster, déclaré ici pour que la destruction l'emporte.
resource "scaleway_vpc_private_network" "kapsule" {
  count = local.kapsule

  name   = "${local.prefixe}-kapsule"
  vpc_id = scaleway_vpc.plateforme.id
  tags   = local.tags

  ipv4_subnet {
    # Un /22 là où les autres réseaux sont en /24 : c'est la contrainte que
    # l'API a nommée, et la plage est hors de 10.10, 10.20 et 10.30 que la
    # stack occupe déjà.
    subnet = "10.40.0.0/22"
  }
}

# La dernière version que la région propose, lue plutôt que supposée.
data "scaleway_k8s_version" "derniere" {
  count = local.kapsule

  name   = "latest"
  region = var.region
}

resource "scaleway_k8s_pool" "mesure" {
  count = local.kapsule

  cluster_id = scaleway_k8s_cluster.mesure[0].id
  name       = "${local.prefixe}-pool"

  # **Les étiquettes du pool, sans `exemple`, et c'est délibéré.** Les nœuds d'un
  # pool Kapsule sont des Instances ; le plugin d'inventaire déclare
  # `products: instance` et ne retient que ce qui porte `exemple`. Si Kapsule
  # propage les étiquettes du pool à ses nœuds, l'inventaire les remonterait, et
  # la garde qui compare ce qu'il trouve à ce que la stack déclare refuserait
  # sept machines là où la stack en annonce cinq.
  #
  # Je n'ai pas mesuré si Kapsule propage. Retirer `exemple` rend la réponse
  # inutile : dans les deux cas l'inventaire ignore ces nœuds, ce qui est le
  # comportement voulu. Un nœud est maintenu par la plateforme, personne ne s'y
  # connecte par cet inventaire.
  #
  # Les deux autres étiquettes restent : ce sont elles qui disent quoi supprimer
  # à la main le jour où la destruction échoue.
  tags = ["ansible-collection-scaleway", var.run_id]

  # **Deux nœuds et non un.** `rolling_reboot` redémarre par vagues, et une
  # vague sur un parc d'un seul nœud ne prouve pas qu'elle enchaîne. Deux est le
  # plus petit nombre qui distingue « par vagues » de « tout d'un coup ».
  size = 2

  # **`DEV1-M` et non le type des Instances.** Kapsule refuse les types les plus
  # petits pour un nœud : il lui faut de quoi faire tourner le kubelet et les
  # composants du plan de données. Le type est donc déclaré ici plutôt que
  # réutilisé de `var.instance_type`, qui vise des machines ordinaires.
  node_type = "DEV1-M"

  # Pas de redimensionnement automatique : un pool qui bouge tout seul ferait
  # bouger le parc sous les mesures, et un redémarrage par vagues ne se
  # distinguerait plus d'un remplacement décidé par la plateforme.
  autoscaling = false

  # Le pool vit et meurt avec le cluster ; le déclarer ici le rend visible dans
  # le plan plutôt que caché dans une option du cluster.
  wait_for_pool_ready = true
}
