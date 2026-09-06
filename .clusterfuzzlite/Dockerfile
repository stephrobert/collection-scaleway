# Image de construction des fuzzers, au format qu'OSS-Fuzz impose.
#
# **Pourquoi ce dépôt fuzze.** Le parser lit un document que personne ici ne
# contrôle : `specs/scaleway/` est versionné, mais son contenu vient du portail
# de Scaleway, qui a ajouté 453 méthodes et en a retiré 26 en douze mois. Le
# parser traduit ce document sur des structures imbriquées, et chaque branche
# suppose une forme.
#
# Ce n'est pas une hypothèse : le harnais de `tests/fuzz/` a trouvé **douze**
# défauts réels au premier passage, tous du même genre — une clé YAML déclarée
# sans valeur, un `$ref` qui n'est pas une chaîne, un `type` qui est un objet.
# Aucun n'était théorique.
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:6b2b3a7e4a2da50de47f94925cffbe34747e1aae4f33d7f07ba6c681dd648b23

COPY . $SRC/collection-scaleway
WORKDIR $SRC/collection-scaleway
COPY .clusterfuzzlite/build.sh $SRC/build.sh
