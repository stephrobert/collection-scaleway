#!/bin/bash -eu
# Construit les fuzzers du parser.
#
# Les dépendances viennent du verrou du dépôt, comme partout ailleurs ici : un
# fuzzer qui tournerait sur d'autres versions que la CI ne mesurerait pas le
# même code.
pip3 install --no-cache-dir -r "$SRC/collection-scaleway/requirements-dev.lock" || \
  pip3 install --no-cache-dir pyyaml

for cible in "$SRC"/collection-scaleway/tests/fuzz/fuzz_*.py; do
  nom=$(basename "$cible" .py)
  compile_python_fuzzer "$cible" --add-data "$SRC/collection-scaleway/generator:generator"
  echo "fuzzer construit : $nom"
done
