"""L'outillage de la CI n'est déclaré qu'à un endroit.

`mise` épingle les versions de `python`, `ruff`, `uv` et `terraform`, chacune
avec la raison de son épingle. Sa propre version, elle, était recopiée dans neuf
étapes réparties sur quatre workflows, avec le condensat de l'action qui
l'installe.

Dependabot rattrape le condensat, parce que c'est une dépendance pour lui. Il ne
rattrape **pas** `version:`, qui n'en est pas une : une des neuf pouvait donc
partir seule, et rien ne l'aurait vu. C'est la règle d'ADR-007 appliquée à
l'outillage, une valeur vraie recopiée en neuf endroits divergeant un jour.

Ce contrôle refuse qu'une seconde déclaration réapparaisse. Il ne juge pas la
version : la juger demanderait de la recalculer, donc une seconde source, ce qui
est le défaut lui-même.

## Ce qu'il ne voit pas, et qui reste à la relecture

Il connaît une liste d'outils installés par action, tenue à la main dans
`SOUS_SURVEILLANCE`. Un outil ajouté demain à un workflow sans être ajouté ici
passera. La liste est courte, chaque entrée nomme l'action et l'endroit unique
qui doit la déclarer, et l'ajouter est le geste qui accompagne l'ajout d'un
outil. Aucun motif ne dirait tout seul qu'une action installe quelque chose.

    python scripts/outillage_ci.py

Codes de sortie : `0` conforme, `1` erreur, `2` déclaration en double.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ACTIONS = ROOT / ".github" / "actions"


@dataclass(frozen=True)
class Outil:
    """Un outil que la CI installe, et l'endroit unique qui doit le déclarer."""

    nom: str
    action: str
    enveloppe: str


#: Les outils installés par une action tierce, et l'action composite qui les
#: enveloppe. `uses:` pointe sur l'enveloppe partout ailleurs.
SOUS_SURVEILLANCE: tuple[Outil, ...] = (
    Outil(nom="mise", action="jdx/mise-action@", enveloppe="./.github/actions/mise"),
)


def _etapes(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Toutes les étapes d'un document de workflow ou d'action composite."""
    trouvees: list[dict[str, Any]] = []
    for job in (document.get("jobs") or {}).values():
        trouvees.extend(job.get("steps") or [])
    runs = document.get("runs") or {}
    trouvees.extend(runs.get("steps") or [])
    return [etape for etape in trouvees if isinstance(etape, dict)]


def declarations(outil: Outil) -> list[str]:
    """Les endroits qui appellent l'action tierce directement."""
    fichiers = sorted(WORKFLOWS.glob("*.yml")) + sorted(ACTIONS.glob("*/action.yml"))
    trouvees = []
    for chemin in fichiers:
        document = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
        for etape in _etapes(document):
            if outil.action in str(etape.get("uses", "")):
                trouvees.append(str(chemin.relative_to(ROOT)))
    return trouvees


def version_epinglee(outil: Outil) -> str | None:
    """La version que l'enveloppe installe, lue dans l'enveloppe."""
    chemin = ACTIONS / Path(outil.enveloppe).name / "action.yml"
    if not chemin.is_file():
        return None
    document = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    for etape in _etapes(document):
        if outil.action in str(etape.get("uses", "")):
            version = (etape.get("with") or {}).get("version")
            return str(version) if version is not None else None
    return None


def plancher() -> str | None:
    """Le `min_version` de `mise.toml`, celui qu'un poste doit tenir."""
    import tomllib

    chemin = ROOT / "mise.toml"
    if not chemin.is_file():
        return None
    valeur = tomllib.loads(chemin.read_text(encoding="utf-8")).get("min_version")
    return str(valeur) if valeur is not None else None


def main(argv: list[str]) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)

    if not sorted(WORKFLOWS.glob("*.yml")):
        print(
            f"aucun workflow sous {WORKFLOWS.relative_to(ROOT)} : "
            "un contrôle qui ne regarde rien passe toujours.",
            file=sys.stderr,
        )
        return 1

    refus = []
    for outil in SOUS_SURVEILLANCE:
        endroits = declarations(outil)
        attendu = f".github/actions/{Path(outil.enveloppe).name}/action.yml"
        superflus = [endroit for endroit in endroits if endroit != attendu]
        if not endroits:
            refus.append(
                f"{outil.nom} : {outil.action} n'est appelé nulle part, pas même {attendu}"
            )
        elif superflus:
            refus.append(
                f"{outil.nom} : {outil.action} est appelé hors de {attendu} : "
                f"{sorted(set(superflus))}. Utiliser `uses: {outil.enveloppe}`."
            )
        else:
            print(f"{outil.nom} : une seule déclaration, dans {attendu}.")

    # **Le plancher du poste et l'épingle de la CI disent la même version.**
    #
    # Ce n'est pas une redondance, c'est ce qui empêche le gel de revenir.
    # L'épingle a été posée le 2 septembre 2026 sur la version installée du
    # poste, et rien ne pouvait la lever : Dependabot suit le condensat de
    # l'action, pas son entrée `version:`. `dependabot.yml` écrit pourtant qu'une
    # épingle que personne ne rafraîchit vieillit jusqu'à la première CVE.
    #
    # Lier les deux fait qu'on ne peut plus monter l'une sans l'autre. Ce que ça
    # ne fait pas : dire qu'une version plus récente existe. Ça demande le
    # réseau, que ce contrôle s'interdit, et `mise` le dit déjà lui-même à
    # chaque exécution sur le poste.
    epinglee = version_epinglee(SOUS_SURVEILLANCE[0])
    sol = plancher()
    if epinglee is None or sol is None:
        refus.append(
            f"version de mise introuvable : enveloppe={epinglee!r}, mise.toml={sol!r}. "
            "Un contrôle qui ne trouve pas ce qu'il compare passerait pour conforme."
        )
    elif epinglee != sol:
        refus.append(
            f"la CI installe mise {epinglee} et `mise.toml` exige au moins {sol} : "
            "un poste tiendrait une version que la CI n'a pas, ou l'inverse."
        )
    else:
        print(f"mise : la CI installe {epinglee}, et `mise.toml` exige au moins autant.")

    if refus:
        print("\n".join(f"REFUSÉ : {motif}" for motif in refus), file=sys.stderr)
        print(
            "\nUne version d'outil recopiée à plusieurs endroits diverge un jour, "
            "et Dependabot ne rattrape que le condensat.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
