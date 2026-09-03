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
# sauté en silence.** `scaleway_instance_image` résout son `root_volume_id` par
# l'API Instance ; l'émulateur crée bien l'instantané par l'API Block, puis rend
# 404 sur le même identifiant côté Instance, et sa liste d'instantanés Instance
# est vide. Mesuré, et signalé en feint#651.
#
# Le `count` porte donc la limite au lieu de la masquer : la sortie
# `image_doree` vaut la chaîne vide quand l'image n'a pas été bâtie, et le
# lanceur le dit. Le jour où feint#651 est corrigé, ce `count` disparaît et rien
# d'autre ne bouge.
resource "scaleway_instance_image" "reference" {
  count = var.endpoint == "" ? 1 : 0

  name           = "${local.prefixe}-reference"
  root_volume_id = scaleway_block_snapshot.reference.id
  architecture   = "x86_64"
  tags           = local.tags
}
