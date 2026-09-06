"""Le parser lit un document que ce dépôt ne contrôle pas.

`specs/scaleway/` est versionné, mais son contenu vient du portail de Scaleway,
qui a ajouté 453 méthodes et en a retiré 26 en douze mois. Le parser traduit ce
document en IR, et il le fait sur des structures imbriquées : `oneOf`, `$ref`,
`items`, `enum`, des enveloppes de réponse. Chacune de ces branches suppose une
forme, et une forme supposée est une forme qui peut manquer.

**Ce que ce fuzzer cherche.** Pas un plantage sur du bruit : n'importe quel
document invalide doit lever `ParseError` ou une erreur YAML, et c'est le
comportement voulu. Ce qu'il cherche est le `TypeError`, l'`AttributeError` ou
le `KeyError` qui sort d'une branche du parser sur un document **presque**
valide, parce que celui-là traverserait la CI le jour où l'amont produit la même
forme.

Les erreurs déclarées sont donc attrapées, et **elles seules** : tout le reste
remonte, ce qui est exactement ce qu'un fuzzer doit faire.

Le même point d'entrée sert à ClusterFuzzLite, par `atheris`, et à
`mise run fuzz:smoke`, qui le rejoue sur des cas dérivés du contrat réel sans
demander qu'`atheris` soit installé. Un harnais qui ne tourne que dans le
conteneur d'OSS-Fuzz est un harnais que personne ne relit.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

RACINE = Path(__file__).resolve().parents[2]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from generator.ansible.mapping import UnmappedType  # noqa: E402
from generator.parser.openapi import ParseError, parse_document  # noqa: E402
from generator.source.base import SpecDocument  # noqa: E402

#: Ce que le parser a le droit de lever sur une entrée qu'il refuse.
#:
#: `ParseError` est son refus explicite ; `UnmappedType` celui du mapping ;
#: `yaml.YAMLError` vient d'un document qui n'est pas du YAML. Tout autre type
#: est un défaut : le parser aurait supposé une forme sans la vérifier.
REFUS_LEGITIMES = (ParseError, UnmappedType, yaml.YAMLError, RecursionError)


def examiner(document: Any) -> None:
    """Passe un document au parser, et laisse remonter ce qui n'est pas un refus."""
    if not isinstance(document, dict):
        return
    spec = SpecDocument(product="fuzz", version="v1", path=Path("fuzz.v1.yml"), document=document)
    try:
        parse_document(spec)
    except REFUS_LEGITIMES:
        return


def TestOneInput(data: bytes) -> None:
    """Le point d'entrée d'`atheris`."""
    try:
        document = yaml.safe_load(data)
    except yaml.YAMLError:
        return
    except RecursionError:
        # Un document profondément imbriqué épuise la pile de PyYAML avant
        # d'atteindre le parser. C'est une limite de la bibliothèque, pas un
        # défaut de ce dépôt.
        return
    examiner(document)


def main() -> None:
    import atheris  # importé ici : il n'existe que dans le conteneur de fuzzing

    atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
