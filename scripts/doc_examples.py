"""Vérifie que les playbooks cités dans la documentation s'analysent encore.

Un exemple faux dans une documentation coûte plus cher qu'une documentation
absente : le lecteur le copie, il échoue, et il conclut que le produit est
cassé. Les `EXAMPLES` des modules sont déjà joués contre l'émulateur par
`mise run integration` ; ce script couvre l'autre moitié, les playbooks écrits
à la main dans les guides.

Il ne les **exécute** pas : ils désignent des machines qui n'existent pas ici.
Il les fait analyser par `ansible-playbook --syntax-check`, ce qui attrape la
classe de défauts qu'une documentation produit vraiment : un module renommé,
un paramètre disparu, une indentation cassée par une réécriture.

    python scripts/doc_examples.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from generator.ansible.collection import load_collection

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ROOT / "docs"

#: Un bloc ```yaml ... ``` dans un Markdown.
FENCE = re.compile(r"```ya?ml\n(.*?)```", re.DOTALL)

#: Ce qui distingue un playbook d'un extrait de configuration : une liste de
#: jeux, donc au moins un `hosts:` en tête d'élément. Un fichier d'inventaire
#: ou un fragment d'options n'a rien à faire ici, et `--syntax-check` le
#: refuserait pour de mauvaises raisons.
PLAYBOOK = re.compile(r"^-\s+(name|hosts):", re.MULTILINE)


class ExampleError(RuntimeError):
    """Un exemple de la documentation ne s'analyse pas, et il faut le dire."""


def extract(chemin: Path) -> list[str]:
    """Les blocs YAML d'un Markdown qui ressemblent à des playbooks."""
    texte = chemin.read_text(encoding="utf-8")
    return [bloc for bloc in FENCE.findall(texte) if PLAYBOOK.search(bloc)]


def sources() -> list[tuple[Path, int, str]]:
    """Tous les playbooks trouvés dans la documentation, avec leur origine."""
    trouves: list[tuple[Path, int, str]] = []
    for chemin in sorted(GUIDES.rglob("*.md")):
        for index, bloc in enumerate(extract(chemin), start=1):
            trouves.append((chemin.relative_to(ROOT), index, bloc))
    return trouves


def check(bloc: str, environnement: dict[str, str], workdir: Path, nom: str) -> str:
    """Fait analyser un playbook par Ansible. Rend le message d'erreur, ou ''."""
    fichier = workdir / f"{nom}.yml"
    fichier.write_text(bloc, encoding="utf-8")
    resultat = subprocess.run(
        [
            str(Path(sys.executable).parent / "ansible-playbook"),
            "--syntax-check",
            str(fichier),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environnement,
    )
    return "" if resultat.returncode == 0 else (resultat.stderr or resultat.stdout).strip()


def main() -> int:
    playbooks = sources()
    # Une documentation sans exemple analysable ne se distingue pas d'un
    # extracteur cassé : les deux rendent zéro, et les deux passent au vert.
    if not playbooks:
        raise ExampleError(
            f"aucun playbook trouvé dans {GUIDES.relative_to(ROOT)} : soit la "
            "documentation n'en porte plus, soit l'extraction est cassée. Les "
            "deux demandent un regard."
        )

    collection = load_collection()
    environnement = {
        **os.environ,
        "ANSIBLE_COLLECTIONS_PATH": str(collection.collections_root),
        "ANSIBLE_LOCALHOST_WARNING": "False",
        "ANSIBLE_INVENTORY_UNPARSED_WARNING": "False",
    }

    echecs: list[str] = []
    with tempfile.TemporaryDirectory(prefix="doc-examples-") as tmp:
        workdir = Path(tmp)
        for chemin, index, bloc in playbooks:
            erreur = check(bloc, environnement, workdir, f"{chemin.stem}-{index}")
            etat = "ok" if not erreur else "ÉCHEC"
            print(f"  {etat:<6} {chemin} bloc {index}")
            if erreur:
                echecs.append(f"{chemin} bloc {index} :\n{erreur}")

    if echecs:
        raise ExampleError(
            f"{len(echecs)} exemple(s) de la documentation ne s'analysent pas :\n\n"
            + "\n\n".join(echecs)
        )

    print(f"{len(playbooks)} playbook(s) de la documentation analysé(s) par Ansible")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExampleError as error:
        print(f"erreur : {error}", file=sys.stderr)
        raise SystemExit(1) from error
