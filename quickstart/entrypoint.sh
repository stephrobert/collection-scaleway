#!/bin/sh
# Écrire ce que l'émulateur accepte, puis servir.
#
# **Les identifiants ne s'inventent pas ici.** C'est la règle que le harnais
# d'intégration de ce dépôt applique déjà : les écrire à la main créerait une
# seconde source de ce que l'émulateur accepte, et les deux divergeraient le
# jour où feint changerait d'avis. `feint env` est cette source, et il répond
# sans qu'un serveur écoute, donc avant de servir.
set -eu

ENDPOINT="${FEINT_ENDPOINT:-http://emulateur:4599}"

if [ -d /env ]; then
  feint env scaleway --endpoint "${ENDPOINT}" > /env/scaleway.sh
fi

# `--expose-to-network` désarme la garde anti-rebinding, et feint refuse de
# quitter la boucle locale sans lui. Ici, cette boucle est celle du conteneur :
# sans le drapeau, aucun autre service de la composition ne joint l'émulateur.
# Ce que la composition publie vers l'hôte reste sur 127.0.0.1.
# **L'état est un fichier, pas seulement de la mémoire.** Sans `--state`, une
# flotte disparaît avec le conteneur qui la portait : un `docker compose up`
# après un redémarrage de docker rendrait un parc vide, et le parcours
# accuserait la collection. Mesuré : `feint serve --state` recharge ce qu'il a
# écrit.
exec feint serve --addr 0.0.0.0:4599 --expose-to-network --state /state/fleet.json "$@"
