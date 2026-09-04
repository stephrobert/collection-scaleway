# Le stockage, et trois leçons que seul le cloud réel a données.
#
# **`b_ssd` n'existe plus.** Le cloud le dit lui-même : « b_ssd volumes are no
# longer supported. Use Scaleway Block Storage (SBS) volumes instead. » Les
# disques de données passent donc par le produit Block Storage.
#
# **Un disque système moderne est un volume SBS**, que l'API `instance/v1` ne
# voit pas : lui demander un instantané répond « resource instance_volume …
# is not found ».
#
# **Un disque vide ne s'instantanée pas.** « cannot create a RO disk from an
# empty disk » : la première version taillait l'image d'or dans un volume
# `l_ssd` créé et jamais attaché, donc vide.
#
# Les trois passaient contre l'émulateur (feint#648, feint#650). C'est le run
# contre le vrai compte qui les a nommées, une par une.

resource "scaleway_block_volume" "donnees" {
  for_each = var.app_servers

  name       = "${local.prefixe}-${each.key}-donnees"
  size_in_gb = each.value.data_gb
  iops       = 5000
  tags       = local.tags
}

# L'image d'or, taillée dans le disque système du bastion, qui a du contenu
# parce qu'une machine y a démarré. L'instantané passe par l'API Block, la
# seule qui voie un volume SBS.
resource "scaleway_block_snapshot" "reference" {
  name      = "${local.prefixe}-reference"
  volume_id = scaleway_instance_server.bastion.root_volume[0].volume_id
  tags      = local.tags
}

# **L'image n'est bâtie que contre le cloud réel, et c'est écrit plutôt que
# sauté en silence.** `createImage` accepte un instantané Block comme volume
# racine sur le cloud réel, et le refusait sur l'émulateur, qui répondait
# « resource snapshot ... is not found ». Signalé en feint#651, corrigé chez
# eux.
#
# **Ce que ce commentaire a d'abord affirmé était faux, et la correction vaut
# d'être lue.** Il disait que le cloud réel résout l'identifiant par l'API
# Instance. Il ne le fait pas : `scw instance snapshot list` rend `[]` sur un
# vrai compte, et le GET unitaire y rend 404 exactement comme sur l'émulateur.
# C'est le contrat, pas un défaut. J'avais déduit un mécanisme d'un `apply` qui
# marchait, au lieu de mesurer le mécanisme, et c'est précisément ce que ce
# dépôt refuse partout ailleurs.
#
# Il y a donc deux objets, pas un identifiant partagé : un instantané Block,
# dont l'API Instance sait **tailler** une image sans jamais le **lister**.
#
# Le `count` porte la limite au lieu de la masquer : la sortie `image_doree`
# vaut la chaîne vide quand l'image n'a pas été bâtie, et le lanceur le dit. Le
# jour où la version corrigée de l'émulateur est celle qu'on installe, ce
# `count` disparaît et rien d'autre ne bouge.
resource "scaleway_instance_image" "reference" {
  count = var.endpoint == "" ? 1 : 0

  name           = "${local.prefixe}-reference"
  root_volume_id = scaleway_block_snapshot.reference.id
  architecture   = "x86_64"
  tags           = local.tags
}


# **Un volume que l'API `instance/v1` voit, et pourquoi il en faut un.**
#
# Tout le stockage ci-dessus passe par Block Storage, parce que c'est ce qu'un
# serveur moderne utilise. La conséquence, mesurée sur le compte réel, est que
# `ListVolumes` de l'API Instance rend une liste **vide** : le module
# `instance_volume` n'avait donc aucune cible, et il était livré sans que rien
# ne l'exerce.
#
# `l_ssd` est un volume local, et c'est le seul type que l'API Instance liste
# encore. 10 Go détaché, c'est le plus petit prix à payer pour que deux modules
# livrés cessent d'être des inconnues.
#
# Il reste **détaché**, et c'est délibéré : l'attacher demanderait de choisir un
# serveur, et un volume local suit le cycle de vie de sa machine. Détaché, la
# destruction l'emporte comme le reste.
resource "scaleway_instance_volume" "vu_par_instance" {
  name       = "${local.prefixe}-vu-par-instance"
  type       = "l_ssd"
  size_in_gb = 10
  tags       = local.tags
}
