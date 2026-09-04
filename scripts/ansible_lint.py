"""Lance `ansible-lint` en profil production sur la collection livrée.

**Ce que ce contrôle voit et qu'aucun autre ne voit.** `ansible-test sanity`
juge les modules, `antsibull-docs` juge leur documentation, et ni l'un ni
l'autre ne regarde les playbooks livrés, le fichier d'environnement d'exécution
ou la configuration du changelog. Lancé pour la première fois, `ansible-lint` a
refusé quatre choses :

* une variable nommée `action` dans un playbook livré, qui est un nom réservé
  d'Ansible et le mot-clé de tâche du même nom ;
* `meta/execution-environment.yml` sans son `version`, pourtant exigé par le
  format. Personne ne le voyait, parce qu'`ansible-builder` n'est lancé nulle
  part ici ;
* deux indentations de liste dans `changelogs/config.yaml`.

**La collection doit être atteignable**, sinon les trois playbooks livrés
échouent en `syntax-check[unknown-module]` : le lint cherche
`stephrobert.scaleway.instance_server_info` et ne trouve rien. C'est un faux
négatif spectaculaire, trois refus fatals pour une variable d'environnement
manquante, et c'est la raison d'être de ce script plutôt qu'une ligne de
commande.

    python scripts/ansible_lint.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    collection = load_collection()
    commande = ["ansible-lint", "--profile", "production"]
    print(f"$ {' '.join(commande)}\n  dans {collection.path.relative_to(ROOT)}\n", flush=True)
    resultat = subprocess.run(
        commande,
        cwd=collection.path,
        # Sans ça, le lint ne résout aucun module de la collection qu'il juge,
        # et rend trois refus fatals qui ne disent rien du code.
        env={**os.environ, "ANSIBLE_COLLECTIONS_PATH": str(ROOT)},
        check=False,
    )
    return resultat.returncode


if __name__ == "__main__":
    raise SystemExit(main())
