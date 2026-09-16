"""« Testé sur Scaleway » doit être une propriété du commit, pas une phrase.

Le dépôt sépare proprement unité, émulateur et cloud réel, et ne prétend pas que
l'émulateur remplace le compte. Le trou était dans la publication : **rien
n'attestait par machine que ce commit précis avait passé le scénario réel**
avant de partir sur Galaxy. Une version pouvait se publier sur la foi d'un tir
fait trois semaines plus tôt, sur un autre arbre.

```text
la preuve    ce qu'un tir a donné, pour un SHA, versionnée comme le relevé
le sceau     le tag signé de la publication, qui la couvre comme il couvre le code
la porte     `release:check`, qui refuse de publier un SHA sans preuve valide
```

**Le tir se joue en local, et c'est une décision, pas un défaut.** La faire
produire par un workflow lui donnerait une attestation de provenance que
personne ne peut fabriquer, et coûterait deux choses qui valent plus cher ici :
la clé secrète Scaleway, qui sait créer des ressources facturées, vivrait dans
les secrets du dépôt ; et le diagnostic sur place disparaîtrait, alors que les
défauts de réseau de cette stack ont tous été trouvés en gardant la plateforme
vivante, après avoir été cherchés en vain à coups de playbooks.

Le sceau existe quand même : les tags de publication de ce dépôt sont signés,
mesuré, et une preuve commitée est couverte par le tag qui la publie. La menace
qu'une attestation de CI écarterait est qu'un tiers fabrique une preuve, et le
mainteneur est seul à publier.

**Ce que le SHA apporte, et qui ne dépend pas de tout ça** : une preuve non liée
au commit se rapproche de n'importe quelle publication. C'est le défaut que #96
nommait, et il se corrige ici quel que soit l'endroit où le tir se joue.

**Ce que cette preuve ne dit pas.** Qu'un tir a réussi ne dit pas que le produit
est bon : il dit que ce scénario-là, ce jour-là, sur cet arbre-là, a fait ce
qu'on attendait et n'a rien laissé derrière. C'est beaucoup moins qu'une
garantie, et c'est exactement ce que la porte de release réclamait sans pouvoir
le vérifier.

Usage :

    python scripts/preuve_tir.py --sceller build/example/dernier-reel.json
    python scripts/preuve_tir.py --verifier                  juge HEAD
    python scripts/preuve_tir.py --verifier --commit <sha>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREUVES = ROOT / "preuves"

#: Au-delà, la preuve ne parle plus de ce qu'on publie.
#:
#: **Ce n'est pas une durée de validité du produit**, c'est une borne sur la
#: distance entre ce qui a été joué et ce qui part. Le contrôle compare d'abord
#: les SHA ; ce délai attrape le cas où l'on republie tel quel un commit ancien,
#: dont le tir précède des changements d'API que personne n'a rejoués.
JOURS_MAX = 30

#: Ce qu'un artefact de run doit porter pour valoir preuve. Lues plutôt que
#: recopiées : c'est `scripts/example.py` qui les écrit.
ATTENDUS = ("cible", "residu", "modules_joues", "modules_en_echec", "run_id")


class PreuveTirError(RuntimeError):
    """La preuve manque, ne désigne pas ce commit, ou ne prouve rien."""


def _affichable(chemin: Path) -> str:
    """Un chemin lisible, même hors du dépôt.

    `relative_to` lève quand le chemin est ailleurs, et **un message d'erreur
    qui plante en se composant cache l'erreur qu'il devait annoncer**. Le dépôt
    l'a déjà payé dans `readme_counters`, sur un test qui déplace un répertoire ;
    ici c'est un test qui déplace celui des preuves, et le refus qu'on voulait
    lire est devenu un `ValueError` sans rapport.
    """
    try:
        return str(chemin.relative_to(ROOT))
    except ValueError:
        return str(chemin)


def _git(*args: str) -> str:
    resultat = subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT, check=False)
    if resultat.returncode != 0:
        raise PreuveTirError(f"`git {' '.join(args)}` a échoué : {resultat.stderr.strip()}")
    return resultat.stdout.strip()


@dataclass(frozen=True)
class Preuve:
    """Ce qu'un tir réel a donné, pour un commit nommé."""

    commit: str
    date: str
    verdict: str
    residu: str
    modules_joues: int
    empreinte: str
    fichier: Path


def _lire(chemin: Path) -> Preuve:
    charge = json.loads(chemin.read_text(encoding="utf-8"))
    manquants = [cle for cle in ("commit", "date", "verdict", "residu") if cle not in charge]
    if manquants:
        raise PreuveTirError(f"{chemin.name} ne porte pas {', '.join(manquants)}")
    return Preuve(
        commit=str(charge["commit"]),
        date=str(charge["date"]),
        verdict=str(charge["verdict"]),
        residu=str(charge["residu"]),
        modules_joues=int(charge.get("modules_joues", 0)),
        empreinte=str(charge.get("empreinte", "")),
        fichier=chemin,
    )


def sceller(artefact: Path, commit: str | None = None) -> Path:
    """Transformer l'artefact d'un run réel en preuve attachée à un commit.

    L'artefact dit ce qui a tourné ; il ne dit pas **sur quel arbre**. C'est tout
    ce que cette fonction ajoute, et c'est ce qui manquait : sans le SHA, une
    preuve se rapproche de n'importe quelle publication.
    """
    if not artefact.is_file():
        raise PreuveTirError(f"{artefact} n'existe pas : lancer le tir avant de le sceller")

    charge = json.loads(artefact.read_text(encoding="utf-8"))
    absents = [cle for cle in ATTENDUS if cle not in charge]
    if absents:
        raise PreuveTirError(
            f"{artefact.name} ne ressemble pas à un artefact de run : "
            f"{', '.join(absents)} manque(nt)."
        )

    if charge["cible"] != "reel":
        raise PreuveTirError(
            f"{artefact.name} vient de la cible {charge['cible']!r}. Seul le cloud réel "
            "vaut preuve ici : l'émulateur prouve la forme d'un run, jamais le compte "
            "(ADR-006)."
        )

    # **Un arbre sale rend la preuve menteuse.** Elle nomme un SHA, et le tir a
    # tourné sur autre chose : les modifications non versionnées y étaient, et le
    # commit nommé ne les porte pas. Personne ne peut plus rejouer ce qui a été
    # prouvé.
    #
    # `release.py` refusait déjà de publier depuis un arbre sale, pour la même
    # raison exactement, et le scellement ne le faisait pas. Mesuré le
    # 16 septembre 2026 : une preuve a été produite sur un arbre portant des
    # fichiers modifiés, et elle affirmait le SHA d'avant.
    sale = _git("status", "--porcelain")
    if sale:
        lignes = sale.splitlines()
        raise PreuveTirError(
            f"l'arbre porte {len(lignes)} modification(s) non versionnée(s) : le tir "
            "a tourné dessus, et la preuve nommerait un commit qui ne les contient "
            "pas.\n    "
            + "\n    ".join(lignes[:5])
            + ("\n    ..." if len(lignes) > 5 else "")
            + "\n    Commiter, puis rejouer le tir sur l'arbre qu'on publiera."
        )

    echecs = list(charge.get("modules_en_echec") or [])
    residu = str(charge["residu"])
    # Nommés avant d'entrer dans le dictionnaire : le nom du fichier les relit,
    # et les relire depuis un `dict[str, Any]` fait perdre leur type.
    sha = commit or _git("rev-parse", "HEAD")
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    preuve = {
        "commit": sha,
        "date": date,
        # Le verdict se dérive de ce que le run a laissé, jamais d'un drapeau
        # qu'on lui passerait : une preuve qui se déclare bonne toute seule ne
        # prouve rien.
        "verdict": "PASS" if not echecs and residu == "aucun" else "FAIL",
        "residu": residu,
        "modules_joues": len(charge.get("modules_joues") or []),
        "modules_en_echec": echecs,
        "run_id": str(charge["run_id"]),
        "empreinte": "sha256:" + hashlib.sha256(artefact.read_bytes()).hexdigest(),
    }

    PREUVES.mkdir(parents=True, exist_ok=True)
    destination = PREUVES / f"tir-{date}-{sha[:9]}.json"
    destination.write_text(
        json.dumps(preuve, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return destination


def _seule_la_preuve_les_separe(ancetre: str, commit: str) -> bool:
    """Ces deux commits ne diffèrent-ils que par ce qui vit sous `preuves/` ?

    **Une preuve ne peut pas être dans le commit qu'elle atteste.** Le tir se
    joue sur un arbre propre, la preuve nomme ce commit-là, et la commiter en
    crée forcément un autre : exiger qu'elle désigne HEAD, c'est demander
    quelque chose d'impossible, et la garde se serait fait désactiver dans le
    mois.

    Le décalage admis est donc étroit et vérifiable : un commit d'écart, dont le
    contenu ne bouge que là où les preuves vivent. Tout le reste de l'arbre est
    celui qui a tourné.
    """
    if not ancetre or ancetre == commit:
        return True
    ancestral = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancetre, commit],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if ancestral.returncode != 0:
        return False
    touches = _git("diff", "--name-only", ancetre, commit).splitlines()
    return bool(touches) and all(chemin.startswith("preuves/") for chemin in touches)


def pour(commit: str) -> Preuve:
    """La preuve qui désigne ce commit, ou un refus qui dit ce qui manque."""
    if not PREUVES.is_dir():
        raise PreuveTirError(
            f"aucun répertoire {_affichable(PREUVES)} : rien n'atteste qu'un tir réel "
            "ait jamais eu lieu."
        )
    trouvees = [
        preuve
        for chemin in sorted(PREUVES.glob("tir-*.json"))
        if (preuve := _lire(chemin)).commit == commit
        or _seule_la_preuve_les_separe(preuve.commit, commit)
    ]
    if not trouvees:
        raise PreuveTirError(
            f"aucune preuve de tir réel pour {commit[:9]}. « Testé sur Scaleway » serait "
            "une phrase, pas une propriété de ce commit.\n"
            "    `python scripts/example.py reel` sur ce SHA, puis "
            "`python scripts/preuve_tir.py --sceller build/example/dernier-reel.json`,\n"
            "    et commiter la preuve : le tag signé de la publication la couvrira."
        )
    return trouvees[-1]


def refus(commit: str, aujourdhui: str | None = None) -> list[str]:
    """Ce qui empêche de publier ce commit, du point de vue du tir réel."""
    try:
        preuve = pour(commit)
    except PreuveTirError as erreur:
        return [str(erreur)]

    dits: list[str] = []
    if preuve.verdict != "PASS":
        dits.append(
            f"{preuve.fichier.name} rend le verdict {preuve.verdict!r} : le tir réel de "
            f"{commit[:9]} n'a pas passé. Publier dessus reviendrait à dire le contraire "
            "de ce qui a été mesuré."
        )
    if preuve.residu != "aucun":
        dits.append(
            f"{preuve.fichier.name} déclare un résidu : {preuve.residu!r}. Le compte est "
            "facturé, et une version ne se publie pas sur un tir qui a laissé quelque "
            "chose derrière lui."
        )

    date = datetime.strptime(aujourdhui or datetime.now(UTC).strftime("%Y-%m-%d"), "%Y-%m-%d")
    age = (date - datetime.strptime(preuve.date, "%Y-%m-%d")).days
    if age > JOURS_MAX:
        dits.append(
            f"{preuve.fichier.name} date de {age} jours, au-delà des {JOURS_MAX} admis. "
            "Elle désigne bien ce commit, et l'API a pu bouger sous lui depuis : rejouer "
            "le tir plutôt que republier une mesure que personne n'a refaite."
        )
    return dits


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    groupe = parseur.add_mutually_exclusive_group(required=True)
    groupe.add_argument("--sceller", metavar="ARTEFACT", help="l'artefact du run réel")
    groupe.add_argument("--verifier", action="store_true", help="juger un commit")
    parseur.add_argument("--commit", default=None, help="par défaut, HEAD")
    arguments = parseur.parse_args(argv[1:])

    if arguments.sceller:
        destination = sceller(Path(arguments.sceller), arguments.commit)
        print(f"{_affichable(destination)} écrit.")
        return 0

    commit = arguments.commit or _git("rev-parse", "HEAD")
    dits = refus(commit)
    if not dits:
        preuve = pour(commit)
        print(f"{preuve.fichier.name} : {preuve.verdict}, résidu {preuve.residu}, {preuve.date}")
        return 0

    for dit in dits:
        print(f"  {dit}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except PreuveTirError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
