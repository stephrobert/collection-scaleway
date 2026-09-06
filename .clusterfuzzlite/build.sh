#!/bin/bash -eu
# Construit les fuzzers du parser.
#
# Trois façons de s'y prendre ont été essayées, et les deux premières ont
# échoué pour des raisons qui valent d'être écrites.
#
# **`--add-data "generator:generator"`** copiait l'arbre comme des *données* :
# PyInstaller ne trace alors aucun import, et le binaire échouait au démarrage
# sur `ModuleNotFoundError: No module named 'json'` — il n'embarquait même pas
# la bibliothèque standard.
#
# **`pip install .`** butait sur le plancher du projet : l'image de base
# d'OSS-Fuzz porte Python 3.11, et `pyproject.toml` déclare `>=3.12`. Le baisser
# pour satisfaire un fuzzer serait laisser l'outil décider du produit ; forcer
# l'installation avec `--ignore-requires-python` serait installer un paquet dont
# la contrainte n'est pas tenue.
#
# **`--paths`** résout les imports statiquement, sans pip et sans plancher.
# Mesuré avant de l'écrire : aucun module de `generator/` n'emploie de grammaire
# postérieure à 3.11, vérifié en les compilant tous avec
# `ast.parse(..., feature_version=(3, 11))`. Le plancher du dépôt reste 3.12
# pour ce qu'il décrit vraiment — l'environnement de développement et la cible
# de mypy.
racine="$SRC/collection-scaleway"
pyyaml=$(grep -m1 '^pyyaml==' "$racine/requirements-dev.lock" | cut -d' ' -f1)
if [ -z "$pyyaml" ]; then
  echo "pyyaml introuvable dans requirements-dev.lock" >&2
  exit 1
fi

# La version de PyYAML est tirée du verrou plutôt qu'écrite ici : un fuzzer qui
# lirait le YAML avec une autre version ne mesurerait pas le même code que la CI.
pip3 install --no-cache-dir "$pyyaml"

for cible in "$racine"/tests/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$cible" --paths "$racine"
done
