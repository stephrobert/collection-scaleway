"""Les scanners de workflows jugent-ils avec la version que la CI installe ?

`mise run security` a rendu **12/12 vert** sur un arbre que la CI a refusé. La
cause n'était pas le code : zizmor local était en 1.28.0, la CI en 1.30.0, et
l'audit qui a rougi est né avec la 1.30.0. Une porte qui juge avec un autre
outil que celui qu'elle prétend rejouer produit un vert qui ne vaut rien, et
c'est le pire résultat possible pour une porte d'avant-poussée.

**La version n'est déclarée qu'à un endroit** : les variables d'environnement de
`.github/workflows/workflow-security.yml`, là où la CI les lit pour installer.
Ce script les relit et compare avec ce qui est installé sur le poste.

    python scripts/scanners.py            compare, et refuse un écart
    python scripts/scanners.py --montrer  dit seulement ce qu'il voit

**Ce qu'il ne fait pas : installer.** L'installation vérifie une somme ou une
provenance, et la recopier ici en donnerait une seconde version qui divergerait.
Le script dit quelle commande la CI lance, et cette commande vit dans le
workflow.

Codes de sortie : `0` aligné, `1` erreur, `2` un scanner juge autrement que la CI.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Le fichier qui déclare les versions, et le seul.
SECURITE = ROOT / ".github" / "workflows" / "workflow-security.yml"
CONFIANCE = ROOT / ".github" / "workflows" / "plumber.yml"


@dataclass(frozen=True)
class Scanner:
    """Un scanner de workflows, et comment lire sa version des deux côtés."""

    nom: str
    #: La variable d'environnement du workflow qui porte la version.
    variable: str
    #: Le workflow qui la déclare.
    declaration: Path
    #: La commande qui dit la version installée, et le motif qui l'y lit.
    commande: tuple[str, ...]
    motif: str


SCANNERS: tuple[Scanner, ...] = (
    Scanner(
        nom="actionlint",
        variable="ACTIONLINT_VERSION",
        declaration=SECURITE,
        commande=("actionlint", "--version"),
        motif=r"^([0-9]+\.[0-9]+\.[0-9]+)",
    ),
    Scanner(
        nom="zizmor",
        variable="ZIZMOR_VERSION",
        declaration=SECURITE,
        commande=("zizmor", "--version"),
        motif=r"zizmor\s+([0-9]+\.[0-9]+\.[0-9]+)",
    ),
    Scanner(
        nom="poutine",
        variable="POUTINE_VERSION",
        declaration=SECURITE,
        commande=("poutine", "version"),
        motif=r"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)",
    ),
    Scanner(
        nom="plumber",
        variable="PLUMBER_VERSION",
        declaration=CONFIANCE,
        commande=("plumber", "version"),
        motif=r"([0-9]+\.[0-9]+\.[0-9]+)",
    ),
)


class ScannerError(RuntimeError):
    """On ne peut pas comparer, et il faut le dire plutôt que de conclure."""


def version_declaree(scanner: Scanner) -> str:
    """Ce que le workflow installe, lu dans le workflow."""
    if not scanner.declaration.is_file():
        raise ScannerError(f"{scanner.declaration} est absent : rien à comparer")
    texte = scanner.declaration.read_text(encoding="utf-8")
    trouve = re.search(rf'{scanner.variable}:\s*"([^"]+)"', texte)
    if trouve is None:
        raise ScannerError(
            f"{scanner.declaration.name} ne déclare plus {scanner.variable} : "
            "cette comparaison ne mesurerait rien et passerait quand même."
        )
    return trouve.group(1)


def version_installee(scanner: Scanner) -> str | None:
    """Ce que le poste a sous la main, ou `None` s'il n'a rien."""
    try:
        resultat = subprocess.run(
            list(scanner.commande), capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return None
    if resultat.returncode != 0:
        return None
    trouve = re.search(scanner.motif, resultat.stdout, re.M)
    return trouve.group(1) if trouve else None


def main(argv: list[str]) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument(
        "--montrer", action="store_true", help="dire ce qui est vu, sans refuser"
    )
    options = analyseur.parse_args(argv)

    ecarts = []
    for scanner in SCANNERS:
        try:
            attendue = version_declaree(scanner)
        except ScannerError as erreur:
            print(f"erreur : {erreur}", file=sys.stderr)
            return 1
        installee = version_installee(scanner)
        etat = "aligné" if installee == attendue else "ÉCART"
        print(f"  {scanner.nom:<11} CI={attendue:<9} poste={installee or 'absent':<9} {etat}")
        if installee != attendue:
            ecarts.append((scanner, attendue, installee))

    if not ecarts:
        print(f"\n{len(SCANNERS)} scanner(s) : le poste juge avec les versions de la CI.")
        return 0
    if options.montrer:
        return 0

    print(
        "\nUn scanner d'une autre version que la CI rend un vert qui ne vaut rien.\n"
        "C'est arrivé : zizmor 1.28.0 en local contre 1.30.0 en CI, et l'audit qui\n"
        "a rougi la pull request est né avec la 1.30.0.\n",
        file=sys.stderr,
    )
    for scanner, attendue, installee in ecarts:
        print(
            f"  {scanner.nom} : la CI installe {attendue}, le poste a "
            f"{installee or 'rien'}. La commande d'installation est dans "
            f"{scanner.declaration.relative_to(ROOT)}.",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
