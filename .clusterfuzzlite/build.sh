#!/bin/bash -eu
# Construit les fuzzers du parser.
#
# **`pip install .` et non `--add-data`.** La première version copiait
# `generator/` comme des *données* : PyInstaller ne trace alors aucun import, et
# le binaire échouait au démarrage sur `ModuleNotFoundError: No module named
# 'json'` — il n'embarquait même pas la bibliothèque standard.
#
# **Et pas le verrou entier.** La deuxième version l'installait, et l'image de
# base d'OSS-Fuzz porte un Python plus ancien que celui de ce dépôt :
# `ansible-core` y exige 3.12, et la construction s'arrêtait sur « No matching
# distribution found ». C'est cohérent plutôt que fâcheux : `ansible-core` est
# une dépendance de ce que le générateur **produit**, pas du générateur. Le
# parser ne lit que de l'OpenAPI.
#
# La version de PyYAML est tout de même **tirée du verrou** au lieu d'être
# écrite ici : un fuzzer qui lirait le YAML avec une autre version ne mesurerait
# pas le même code que la CI.
racine="$SRC/collection-scaleway"
pyyaml=$(grep -m1 '^pyyaml==' "$racine/requirements-dev.lock" | cut -d' ' -f1)
if [ -z "$pyyaml" ]; then
  echo "pyyaml introuvable dans requirements-dev.lock" >&2
  exit 1
fi

pip3 install --no-cache-dir "$pyyaml"
pip3 install --no-cache-dir --no-deps "$racine"

for cible in "$racine"/tests/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$cible"
done
