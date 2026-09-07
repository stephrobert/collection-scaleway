"""Le verrou du fuzzer concorde avec celui du dépôt, et s'installe par empreinte.

Le fuzzer construit son image dans l'infrastructure d'OSS-Fuzz, loin de
`mise run check`. Il y installait son lecteur YAML avec un `pip3 install
pyyaml==6.0.3` : la version était tirée du verrou, l'empreinte ne l'était pas.
Scorecard l'a signalé, et le reproche est juste — une version dit *quoi*, une
empreinte dit *quel octet*, et c'était le seul endroit du dépôt où une
dépendance s'installait sans.

Épingler par empreinte crée aussitôt un second verrou à tenir. Ce contrôle est
ce qui l'empêche de dériver : `mise run lock` fait monter PyYAML, le verrou du
fuzzer garde l'ancien, et le fuzzer mesure alors un lecteur que la CI n'emploie
plus. Rien ne rougirait — le fuzzer continuerait de trouver des défauts, dans
du code qui n'est plus celui du dépôt.

    python scripts/verrou_fuzz.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Le verrou du dépôt, produit par `mise run lock`, et celui du fuzzer, qui n'en
#: reprend que ce dont l'image d'OSS-Fuzz a besoin.
VERROU_DU_DEPOT = ROOT / "requirements-dev.lock"
VERROU_DU_FUZZER = ROOT / ".clusterfuzzlite" / "requirements.txt"

#: Le script de construction, qui doit installer le second et pas autre chose.
CONSTRUCTION = ROOT / ".clusterfuzzlite" / "build.sh"

_PAQUET = re.compile(r"^(?P<nom>[A-Za-z0-9._-]+)==(?P<version>[^\s\\]+)")
_EMPREINTE = re.compile(r"--hash=(?P<empreinte>sha256:[0-9a-f]{64})")


def paquets(texte: str) -> dict[str, tuple[str, frozenset[str]]]:
    """Lit un fichier d'exigences pip, empreintes comprises.

    Le format continue une exigence sur plusieurs lignes par une barre oblique
    inverse en fin de ligne ; les empreintes d'un paquet sont donc portées par
    les lignes qui suivent la sienne, et non par la sienne.
    """
    trouves: dict[str, tuple[str, frozenset[str]]] = {}
    courant: str | None = None
    empreintes: set[str] = set()
    for ligne in texte.splitlines():
        nu = ligne.strip()
        if nu.startswith("#") or not nu:
            continue
        depart = _PAQUET.match(nu)
        if depart:
            if courant is not None:
                trouves[courant] = (trouves[courant][0], frozenset(empreintes))
            courant = depart.group("nom").lower()
            trouves[courant] = (depart.group("version"), frozenset())
            empreintes = set()
        if courant is not None:
            empreintes.update(m.group("empreinte") for m in _EMPREINTE.finditer(nu))
    if courant is not None:
        trouves[courant] = (trouves[courant][0], frozenset(empreintes))
    return trouves


def ecarts_de_verrou(fuzzer: str, depot: str) -> list[str]:
    """Ce qui sépare le verrou du fuzzer de celui du dépôt.

    Le fuzzer n'installe qu'une part du verrou du dépôt : ce qui manque chez lui
    n'est pas un écart. Ce qui en est absent, ce qui n'a pas la même version, et
    ce qui n'a pas exactement les mêmes empreintes en sont.
    """
    du_fuzzer = paquets(fuzzer)
    du_depot = paquets(depot)
    if not du_fuzzer:
        return [
            "le verrou du fuzzer ne déclare aucun paquet : un contrôle qui "
            "n'examine rien rend vert sur n'importe quoi."
        ]

    trouves: list[str] = []
    for nom, (version, empreintes) in sorted(du_fuzzer.items()):
        if not empreintes:
            trouves.append(
                f"{nom}=={version} s'installe sans empreinte : une version dit quoi, "
                "une empreinte dit quel octet."
            )
        if nom not in du_depot:
            trouves.append(
                f"{nom} est installé par le fuzzer et absent de "
                f"{VERROU_DU_DEPOT.name} : il mesure une dépendance que le dépôt n'a pas."
            )
            continue
        attendue, siennes = du_depot[nom]
        if version != attendue:
            trouves.append(
                f"{nom} : le fuzzer installe {version}, le dépôt tient {attendue}. "
                "Le fuzzer ne mesure plus le code que la CI exécute."
            )
        elif empreintes and empreintes != siennes:
            manquantes = sorted(siennes - empreintes)
            surnumeraires = sorted(empreintes - siennes)
            trouves.append(
                f"{nom} : les empreintes divergent de {VERROU_DU_DEPOT.name} "
                f"({len(manquantes)} manquante(s), {len(surnumeraires)} en trop)."
            )
    return trouves


def ecarts_de_construction(construction: str) -> list[str]:
    """Le script d'image installe bien par empreinte, et depuis le verrou.

    Sans ce contrôle, le verrou du fuzzer pourrait rester impeccable pendant
    qu'un `pip install` écrit à côté ramène une dépendance non épinglée. C'est
    exactement le défaut que Scorecard a signalé, et il se réintroduirait sans
    que rien ne rougisse.
    """
    trouves: list[str] = []
    for ligne in construction.splitlines():
        nu = ligne.strip()
        if nu.startswith("#") or not re.match(r"^pip3?\s+install\b", nu):
            continue
        if "--require-hashes" not in nu:
            trouves.append(
                f"« {nu} » installe sans `--require-hashes` : Scorecard le refuse, et il a raison."
            )
        if "-r " not in nu:
            trouves.append(
                f"« {nu} » n'installe pas depuis un fichier d'exigences : les "
                "empreintes n'ont alors nulle part où être tenues."
            )
    if not trouves and "pip" not in construction:
        trouves.append(
            f"{CONSTRUCTION.name} n'installe plus rien : ce contrôle ne mesure "
            "plus la construction du fuzzer."
        )
    return trouves


def main() -> int:
    fuzzer = VERROU_DU_FUZZER.read_text(encoding="utf-8")
    ecarts = ecarts_de_verrou(fuzzer, VERROU_DU_DEPOT.read_text(encoding="utf-8"))
    ecarts += ecarts_de_construction(CONSTRUCTION.read_text(encoding="utf-8"))
    if ecarts:
        for ecart in ecarts:
            print(f"  {ecart}", file=sys.stderr)
        print(
            "\nRégénérer le verrou du fuzzer depuis celui du dépôt, puis relire le diff.",
            file=sys.stderr,
        )
        return 1

    installes = sorted(paquets(fuzzer))
    print(
        f"verrou du fuzzer : {len(installes)} paquet(s) épinglé(s) par empreinte "
        f"et concordant(s) avec {VERROU_DU_DEPOT.name} ({', '.join(installes)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
