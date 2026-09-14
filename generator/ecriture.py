"""Écrire un artefact versionné sans jamais le laisser à moitié écrit.

`Path.write_text` tronque le fichier, puis écrit. Entre les deux, le fichier
existe et il est vide.

**Mesuré le 14 septembre 2026**, en guettant la taille d'un module pendant sa
régénération : cinquante-six lectures hors taille finale, toutes tronquées, aux
tailles `0`, `4096`, `8192` et `12288` pour un fichier de 12809 octets. La
fenêtre dure un dixième de milliseconde par fichier, et `mise run check`
réécrit toute la collection et les golden à chaque passage, pendant que la
suite de tests lit ces mêmes fichiers.

Deux choses en dépendent, et aucune n'est théorique :

* **un lecteur concurrent peut voir un artefact vide.** `mise run check` lance
  `test` dans le même graphe que `generate` et `golden:update` ; pytest, `git
  status` et un éditeur ouvert lisent les fichiers que ces tâches réécrivent ;
* **une génération interrompue laisse un fichier tronqué sur le disque.** Un
  `Ctrl-C` au mauvais moment, et l'artefact versionné est à moitié écrit ;
  `check:generated` le dirait, mais le contenu serait perdu.

Le remède est l'écriture atomique : écrire à côté, puis renommer. `os.replace`
est atomique sur un même système de fichiers, donc un lecteur voit soit
l'ancien contenu, soit le nouveau, jamais un entre-deux.

Le fichier temporaire vit **dans le répertoire de destination** et non dans
`/tmp` : un renommage entre systèmes de fichiers n'est pas atomique, il copie,
et on retrouverait la fenêtre qu'on cherche à fermer.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

#: Le préfixe des fichiers temporaires, pour qu'un reliquat se reconnaisse.
#: Un run tué entre l'écriture et le renommage en laisse un, et quelqu'un doit
#: pouvoir dire d'où il vient plutôt que de le prendre pour un artefact.
PREFIXE = ".ecriture-"


def ecrire(chemin: Path, contenu: str, *, encoding: str = "utf-8") -> None:
    """Écrit `contenu` dans `chemin`, sans jamais le laisser à moitié écrit.

    Le fichier temporaire est créé dans le répertoire de destination, rempli,
    poussé sur le disque, puis renommé. `os.replace` écrase la cible en une
    seule opération.

    Le `fsync` n'est pas là pour la performance : sans lui, le renommage peut
    précéder l'arrivée des octets sur le disque, et une coupure d'alimentation
    laisserait un fichier renommé mais vide. C'est le même défaut, déplacé d'un
    cran.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    descripteur, provisoire = tempfile.mkstemp(
        dir=str(chemin.parent), prefix=PREFIXE, suffix=chemin.suffix
    )
    try:
        with os.fdopen(descripteur, "w", encoding=encoding) as fichier:
            fichier.write(contenu)
            fichier.flush()
            os.fsync(fichier.fileno())
        os.replace(provisoire, chemin)
    except BaseException:
        # **`BaseException` et non `Exception`** : un `Ctrl-C` lève
        # `KeyboardInterrupt`, qui n'en dérive pas, et c'est exactement le cas
        # qu'on cherche à couvrir. Sans ça, l'interruption laisserait le
        # fichier provisoire derrière elle.
        Path(provisoire).unlink(missing_ok=True)
        raise
