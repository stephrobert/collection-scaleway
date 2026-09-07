"""GitHub n'est pas une zone de qualification.

Une pull request rouge coûte trois fois : le temps du runner, le temps de la
relecture, et le budget d'API du dépôt. Ce dernier a déjà fait échouer CodeQL,
OSV-Scanner et la revue de dépendances **en même temps**, sur un `API rate limit
exceeded for installation` qui n'avait rien à voir avec le code poussé. Une
boucle d'essai qui passe par la CI épuise exactement ce budget.

Ce programme lance en local, dans l'ordre de la CI, ce que la CI lance. Un
échec ici coûte quelques minutes ; le même échec là-bas coûte un aller-retour et
une part du budget.

**Ce qu'il dit de ce qu'il ne peut pas faire est la moitié utile.** Une porte
locale qui passerait sous silence les étapes qu'elle ne sait pas rejouer serait
le défaut que ce dépôt a déjà connu : un `ansible-test sanity` vert sur zéro
fichier examiné. Chaque étape non rejouable est donc **nommée** dans le compte
rendu, avec ce qui l'empêche.

    python scripts/qualifier.py            # tout, dans l'ordre, arrêt au premier échec
    python scripts/qualifier.py --tout     # tout, sans s'arrêter, puis le bilan
    python scripts/qualifier.py --rapide   # ce qui tient en moins d'une minute
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Etape:
    """Une étape de la CI, et la commande qui la rejoue ici.

    `job` nomme le job GitHub que l'étape couvre : c'est ce qui permet de lire
    le compte rendu comme une carte de la CI, et de voir tout de suite ce qui
    n'y est pas.
    """

    nom: str
    job: str
    commande: tuple[str, ...]
    rapide: bool = False
    #: Le programme dont l'absence rend l'étape injouable, s'il y en a un.
    outil: str = ""
    #: Ce que l'étape ne prouve pas, même verte.
    reserve: str = ""


@dataclass
class Verdict:
    """Ce qu'une étape a produit."""

    etape: Etape
    issue: str
    secondes: float = 0.0
    detail: str = ""


#: L'ordre est celui de la CI, et l'ordre compte : `check` en premier parce
#: qu'il est le plus court et attrape le plus, les étapes en conteneur en
#: dernier parce qu'elles téléchargent.
ETAPES: tuple[Etape, ...] = (
    Etape(
        nom="lint, types, tests, rapport strict, golden, falsify",
        job="Générateur",
        commande=("mise", "run", "check"),
        rapide=True,
    ),
    Etape(
        nom="ansible-test sanity",
        job="collection",
        commande=("mise", "run", "sanity"),
        reserve=(
            "la CI le rejoue sur quatre versions d'ansible-core ; ici il tourne "
            "sur celle du venv. `mise run setup:ansible` en épingle une autre."
        ),
    ),
    Etape(
        nom="playbooks et inventaire contre l'émulateur",
        job="Intégration",
        commande=("mise", "run", "integration"),
    ),
    Etape(
        nom="la plateforme d'exemple, déployée puis détruite",
        job="Plateforme d'exemple",
        commande=("mise", "run", "example"),
    ),
    Etape(
        nom="site de documentation et playbooks cités",
        job="Archive",
        commande=("mise", "run", "docs:site", "docs:examples", "check:worktree"),
    ),
    Etape(
        nom="actionlint, zizmor, poutine",
        job="Workflow security",
        commande=("mise", "run", "security"),
        rapide=True,
        outil="actionlint",
    ),
    Etape(
        nom="politique de confiance du pipeline",
        job="Plumber",
        commande=("mise", "run", "security:trust"),
        rapide=True,
        outil="plumber",
    ),
    Etape(
        nom="vulnérabilités connues des dépendances",
        job="scan-pr / osv-scan",
        commande=("osv-scanner", "scan", "source", "--recursive", "."),
        rapide=True,
        outil="osv-scanner",
    ),
    Etape(
        nom="image d'environnement d'exécution",
        job="Image",
        commande=("python", "scripts/qualifier.py", "--image"),
    ),
    Etape(
        nom="image et fuzzers ClusterFuzzLite",
        job="ClusterFuzzLite",
        commande=("python", "scripts/qualifier.py", "--fuzz"),
        outil="podman",
    ),
)

#: Ce que la CI fait et qu'on ne rejoue pas ici, avec la raison. La liste est
#: publiée à chaque passage : une porte locale qui tairait ses trous mentirait
#: par omission, et c'est exactement le vert sur zéro fichier examiné.
NON_REJOUES: tuple[tuple[str, str], ...] = (
    (
        "CodeQL",
        "la base de données demande plusieurs minutes et le téléversement du "
        "SARIF passe par l'API du dépôt ; rien de local ne le reproduit.",
    ),
    (
        "Revue des changements de dépendances",
        "elle compare la branche à la base via le graphe de dépendances de "
        "GitHub, qui n'existe que côté serveur.",
    ),
    (
        "TruffleHog",
        "il compare deux commits d'un dépôt distant ; `git diff` local ne "
        "porte pas la même chose. Le garde-fou qui compte est la protection "
        "contre la poussée de secrets, active sur le dépôt.",
    ),
    (
        "OpenSSF Scorecard",
        "il lit l'état du dépôt sur GitHub, pas l'arbre de travail.",
    ),
)


def _lancer(commande: tuple[str, ...], secondes_max: int = 3600) -> tuple[int, str]:
    """Lance une commande à la racine, et rend son code et sa sortie."""
    resultat = subprocess.run(
        commande,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=secondes_max,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return resultat.returncode, resultat.stdout + resultat.stderr


def construire_image(fichier: str, tag: str, contexte: str = ".") -> int:
    """Construit une image avec le moteur disponible, podman ou docker.

    La CI construit les deux images qu'elle publie ; les construire ici est le
    seul moyen de savoir qu'un `Containerfile` tient avant de le pousser. Trois
    échecs de construction ClusterFuzzLite d'affilée ont été diagnostiqués
    depuis la CI, chacun réel, chacun trouvable ici en quelques minutes.
    """
    moteur = shutil.which("podman") or shutil.which("docker")
    if moteur is None:
        print("ni podman ni docker : l'image n'est pas construite", file=sys.stderr)
        return 1
    code, sortie = _lancer((moteur, "build", "-f", fichier, "-t", tag, contexte))
    if code != 0:
        print(sortie[-4000:], file=sys.stderr)
    return code


def construire_les_fuzzers() -> int:
    """Construit l'image du fuzzer **et compile les fuzzers dedans**.

    Construire l'image ne prouve rien : elle ne fait que copier le dépôt. Ce
    qui échoue, et qui a échoué trois fois, c'est `compile` : le `pip install`,
    le plancher de version, la résolution des imports par PyInstaller.
    """
    moteur = shutil.which("podman") or shutil.which("docker")
    if moteur is None:
        print("ni podman ni docker : les fuzzers ne sont pas construits", file=sys.stderr)
        return 1
    tag = "collection-scaleway-cfl:qualification"
    code = construire_image(".clusterfuzzlite/Dockerfile", tag)
    if code != 0:
        return code
    code, sortie = _lancer(
        (
            moteur,
            "run",
            "--rm",
            "-e",
            "FUZZING_LANGUAGE=python",
            "-e",
            "SANITIZER=address",
            tag,
            "compile",
        )
    )
    if code != 0:
        print(sortie[-4000:], file=sys.stderr)
    _lancer((moteur, "rmi", "-f", tag))
    return code


def etapes_retenues(rapide: bool) -> list[Etape]:
    return [etape for etape in ETAPES if etape.rapide or not rapide]


def qualifier(etapes: list[Etape], jusquau_bout: bool) -> list[Verdict]:
    """Joue les étapes dans l'ordre, et rend un verdict par étape."""
    verdicts: list[Verdict] = []
    for etape in etapes:
        if etape.outil and shutil.which(etape.outil) is None:
            verdicts.append(Verdict(etape, "outil absent", detail=etape.outil))
            print(f"  ~  {etape.job:22} {etape.nom}  ({etape.outil} absent)")
            continue

        print(f"  .  {etape.job:22} {etape.nom} ...", flush=True)
        debut = time.monotonic()
        code, sortie = _lancer(etape.commande)
        duree = time.monotonic() - debut
        if code == 0:
            verdicts.append(Verdict(etape, "vert", duree))
            print(f"  ok {etape.job:22} {etape.nom}  ({duree:.0f} s)")
            continue

        verdicts.append(Verdict(etape, "rouge", duree, sortie[-4000:]))
        print(f"  KO {etape.job:22} {etape.nom}  ({duree:.0f} s)", file=sys.stderr)
        print(sortie[-4000:], file=sys.stderr)
        if not jusquau_bout:
            break
    return verdicts


def compte_rendu(verdicts: list[Verdict], demandees: list[Etape]) -> int:
    """Le bilan, et surtout ce qui n'a pas été mesuré."""
    verts = [v for v in verdicts if v.issue == "vert"]
    rouges = [v for v in verdicts if v.issue == "rouge"]
    absents = [v for v in verdicts if v.issue == "outil absent"]
    non_jouees = [e for e in demandees if all(v.etape is not e for v in verdicts)]

    print(f"\n{len(verts)}/{len(demandees)} étape(s) de la CI rejouée(s) en vert.")

    reserves = [(v.etape.job, v.etape.reserve) for v in verts if v.etape.reserve]
    if reserves:
        print("\nCe qu'une étape verte ne prouve pas :")
        for job, reserve in reserves:
            print(f"  {job} : {reserve}")

    if absents:
        print("\nÉtape(s) non jouées faute d'outil, donc non mesurées :")
        for verdict in absents:
            print(f"  {verdict.etape.job} : {verdict.detail} n'est pas installé")

    if non_jouees:
        print("\nÉtape(s) non atteintes, l'arrêt s'étant fait avant :")
        for etape in non_jouees:
            print(f"  {etape.job} : {etape.nom}")

    print("\nCe que la CI fait et qu'aucune commande locale ne rejoue :")
    for nom, raison in NON_REJOUES:
        print(f"  {nom} : {raison}")

    sys.stdout.flush()
    if rouges:
        print(
            f"\n{len(rouges)} étape(s) rouge(s) : {', '.join(v.etape.job for v in rouges)}.",
            file=sys.stderr,
        )
        return 1
    if absents or non_jouees:
        print(
            "\nRien n'est rouge, et tout n'a pas été mesuré : voir ci-dessus avant de pousser.",
            file=sys.stderr,
        )
        return 2
    print("\nTout ce qui est rejouable en local est vert.")
    return 0


def main(argv: list[str]) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--tout", action="store_true", help="ne pas s'arrêter au premier échec")
    analyseur.add_argument("--rapide", action="store_true", help="seulement ce qui tient en peu")
    analyseur.add_argument("--image", action="store_true", help=argparse.SUPPRESS)
    analyseur.add_argument("--fuzz", action="store_true", help=argparse.SUPPRESS)
    options = analyseur.parse_args(argv)

    if options.image:
        return construire_image("Containerfile", "stephrobert-scaleway-ee:qualification")
    if options.fuzz:
        return construire_les_fuzzers()

    demandees = etapes_retenues(options.rapide)
    print(f"Qualification locale : {len(demandees)} étape(s) de la CI, dans son ordre.\n")
    verdicts = qualifier(demandees, jusquau_bout=options.tout)
    return compte_rendu(verdicts, demandees)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
