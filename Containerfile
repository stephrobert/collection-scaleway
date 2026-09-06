# Environnement d'exécution Ansible portant la collection et ses dépendances.
#
# **Pourquoi une image, et pas seulement une archive Galaxy.** Un utilisateur
# d'AWX, d'`ansible-navigator` ou d'un runner de CI ne joue pas un playbook avec
# l'`ansible-core` de sa machine : il le joue dans un environnement d'exécution.
# Sans image, il doit en construire une, et donc redécouvrir que les modules
# échouent en `missing_required_lib` sans le SDK Scaleway.
#
# **Pourquoi un Containerfile écrit à la main et pas `ansible-builder`.**
# `ansible-builder` lirait `meta/execution-environment.yml` et générerait
# exactement ceci, au prix d'une trentaine de paquets Python de plus dans
# l'environnement de développement. Ce fichier installe depuis
# `meta/ee-requirements.txt`, **le fichier que `ansible-builder` lirait**, donc
# il n'y a qu'une source et les deux ne peuvent pas diverger sur les
# dépendances.
#
# L'image de base est épinglée par condensat, comme `.plumber.yaml` l'exige de
# toute image : un tag se réécrit, un condensat non.
FROM quay.io/ansible/awx-ee@sha256:eaab9b09f731e3561ee0d932123a9971c76095555520f71da7ff4f2d433b4c99

# Les métadonnées que l'écosystème lit : `ansible-navigator` les affiche, et un
# scanner de chaîne d'approvisionnement les rattache au dépôt qui a produit
# l'image.
LABEL org.opencontainers.image.title="stephrobert.scaleway execution environment"
LABEL org.opencontainers.image.description="Ansible execution environment carrying the stephrobert.scaleway Day-2 collection and the Scaleway SDK."
LABEL org.opencontainers.image.source="https://github.com/stephrobert/collection-scaleway"
LABEL org.opencontainers.image.licenses="GPL-3.0-or-later"

USER root

# **L'archive, et pas `ansible-galaxy install stephrobert.scaleway`.** Ce qui
# entre dans l'image est exactement ce que la construction vient de produire et
# de vérifier, pas ce que Galaxy servira au moment du build : les deux doivent
# coïncider, et c'est au tag de le garantir, pas au réseau.
COPY build/dist/*.tar.gz /tmp/collection.tar.gz
COPY ansible_collections/stephrobert/scaleway/meta/ee-requirements.txt /tmp/ee-requirements.txt

# **`pip3` et non `python3 -m pip`, et ce n'est pas un détail de style.** Dans
# `awx-ee`, `/usr/bin/python3` est un 3.9 sans `pip`, tandis qu'Ansible et
# `pip3` tournent tous deux sur 3.12. Installer avec `python3 -m pip` échoue, et
# vérifier avec `python3` échouerait **après une installation pourtant
# correcte** : deux interpréteurs, un seul qui compte.
RUN ansible-galaxy collection install /tmp/collection.tar.gz \
      --collections-path /usr/share/ansible/collections \
 && pip3 install --no-cache-dir -r /tmp/ee-requirements.txt \
 && rm -f /tmp/collection.tar.gz /tmp/ee-requirements.txt

# **La vérification fait partie de la construction.** Une image qui contient les
# fichiers n'est pas une image dans laquelle Ansible sait les charger : c'est la
# même distinction que `mise run package` fait sur l'archive, et elle a déjà
# attrapé un plugin d'inventaire dont le nom avait changé la veille.
RUN ansible-doc stephrobert.scaleway.instance_server_info >/dev/null \
 && ansible-doc -t inventory stephrobert.scaleway.compute >/dev/null \
 && /usr/bin/python3.12 -c 'import scaleway; print("SDK Scaleway importé")'

USER 1000
