"""Ce que la dérive de l'API a fait au générateur, en un texte lisible.

Le workflow planifié télécharge les contrats, puis appelle ce script. Il ne
décide rien : il **dit** ce qui a bougé, et laisse l'arbitrage à un humain,
parce qu'une opération apparue en amont demande une décision de classification
que personne ne veut voir prise toute seule.

    python scripts/drift_report.py            # rien n'a bougé : sortie vide, code 0
                                              # quelque chose a bougé : rapport, code 3

Le code 3 est délibérément distinct des trois codes que la CI connaît déjà
(`0` succès, `1` erreur, `2` opération non triée ou override orphelin) : une
dérive n'est pas une erreur du dépôt, c'est une nouvelle du monde extérieur, et
le workflow doit pouvoir la distinguer d'une panne de son propre outillage.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs" / "scaleway"
GOLDEN = ROOT / "tests" / "fixtures"


def _git(*arguments: str) -> str:
    resultat = subprocess.run(
        ["git", *arguments],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if resultat.returncode not in (0, 1):
        raise SystemExit(f"git {' '.join(arguments)} a échoué :\n{resultat.stderr}")
    return resultat.stdout


def contrats_modifies() -> list[str]:
    sortie = _git("status", "--porcelain", "--", str(SPECS.relative_to(ROOT)))
    return [ligne[3:] for ligne in sortie.splitlines() if ligne.strip()]


def golden_modifie() -> str:
    """Ce que la dérive fait à l'IR, qui est la seule chose actionnable.

    Un contrat qui change de mise en forme sans changer une opération n'est pas
    une dérive du produit. Le golden le dit, et c'est pour ça qu'on le
    régénère ici plutôt que de comparer les octets du contrat.
    """
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "update_golden.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    return _git("diff", "--stat", "--", str(GOLDEN.relative_to(ROOT)))


def main() -> int:
    contrats = contrats_modifies()
    if not contrats:
        print("aucune dérive : les contrats téléchargés sont ceux qui sont versionnés")
        return 0

    lignes = [
        "Les contrats publiés par Scaleway ne sont plus ceux que ce dépôt",
        "versionne. C'est la nouvelle que ce mécanisme existe pour donner :",
        "toute opération apparue en amont doit finir **générée**, **écartée avec",
        "sa raison** dans les overrides, ou **UNKNOWN** avec la CI rouge. Jamais",
        "dans le silence.",
        "",
        "## Les contrats qui ont bougé",
        "",
        "```text",
        *contrats,
        "```",
        "",
        "## Ce que ça fait à la représentation intermédiaire",
        "",
        "Un contrat qui change de mise en forme sans changer une opération n'est",
        "pas une dérive du produit. C'est le golden qui tranche.",
        "",
    ]

    diff = golden_modifie().strip()
    if diff:
        lignes += ["```text", diff, "```", ""]
    else:
        lignes += [
            "Aucun changement dans l'IR : la dérive est de mise en forme ou porte",
            "sur ce que le parser ne lit pas. Le diff des contrats reste à lire.",
            "",
        ]

    lignes += [
        "## Ce qu'il reste à faire, et qu'aucune machine ne fera",
        "",
        "1. `mise run sync:api` en local, puis lire le diff des contrats ;",
        "2. `mise run check` : le rapport strict sort en 2 sur toute opération",
        "   non classée, et le golden échoue sur tout ce qui a bougé ;",
        "3. classer ce qui est apparu, ou l'écarter **avec sa raison** ;",
        "4. `mise run golden:update`, puis lire le diff avant de le commiter.",
    ]

    print("\n".join(lignes))
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
