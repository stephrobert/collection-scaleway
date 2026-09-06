#!/bin/bash -eu
# Construit les fuzzers du parser.
#
# **`pip install .` et non `--add-data`.** La première version copiait
# `generator/` comme des *données* : PyInstaller ne trace alors aucun import, et
# le binaire produit échouait au démarrage sur `ModuleNotFoundError: No module
# named 'json'` — il n'embarquait même pas la bibliothèque standard. Installé
# comme un paquet, `import generator` se résout normalement et l'analyse suit
# toute la chaîne.
#
# Les dépendances viennent du verrou du dépôt : un fuzzer qui tournerait sur
# d'autres versions que la CI ne mesurerait pas le même code.
pip3 install --no-cache-dir -r "$SRC/collection-scaleway/requirements-dev.lock"
pip3 install --no-cache-dir --no-deps "$SRC/collection-scaleway"

for cible in "$SRC"/collection-scaleway/tests/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$cible"
done
