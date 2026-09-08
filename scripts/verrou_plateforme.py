"""Une plateforme debout laisse une trace, et cette trace protège sa destruction.

Un run réel a laissé des ressources facturées vivantes, et le `finally` avait
pourtant été atteint et lancé la destruction : c'est la destruction elle-même
qui n'a pas pu s'exécuter. ADR-015 porte l'incident, son compte et sa date.

La cause est mesurée. `examples/stack/.terraform.lock.hcl` est **versionné**, et
j'ai changé de branche git pendant que le déploiement tournait pour traiter une
autre issue. La branche d'arrivée ne déclarait pas le fournisseur `tls` que le
déploiement utilisait, et Terraform a refusé de charger un schéma que sa propre
définition ne nommait plus.

**Un `finally` ne protège que si la commande qu'il lance peut encore
s'exécuter.** C'est la limite exacte de la garantie de résidu zéro, et elle
n'était écrite nulle part.

Ce module pose un verrou pendant qu'une plateforme est debout :

* il **refuse** un second run tant que le premier n'a pas rendu la main ;
* il **compare** l'arbre au moment de détruire avec celui qui a déployé, et
  nomme le commit à retrouver quand les deux divergent.

Il ne refuse pas de détruire : refuser reviendrait à laisser des ressources
facturées pour faire respecter une règle d'hygiène. Il dit ce qui a changé, et
il le dit **avant** que Terraform échoue, quand la phrase sert encore.

**Le commit sert à comparer, pas à s'y ramener.** Une plateforme déployée depuis
un arbre sale reste détruisible, et le verdict le dit plutôt que de l'interdire.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Le verrou vit là où vivent déjà les artefacts de couverture, et il survit au
#: shell : il a fallu retrouver le `run_id` de l'incident dans un journal.
VERROU = ROOT / "build" / "example" / "plateforme.json"

#: Ce dont la destruction dépend, et qui est versionné. Un changement de branche
#: les remplace sous une infrastructure déployée.
SUIVIS: tuple[str, ...] = (
    "examples/stack",
    "scripts/example.py",
)


class VerrouError(RuntimeError):
    """Une plateforme est debout, ou l'arbre a changé sous elle."""


@dataclass(frozen=True)
class Plateforme:
    """Ce qu'il faut savoir d'un déploiement pour le détruire."""

    run_id: str
    cible: str
    commit: str
    branche: str
    arbre_sale: bool
    empreinte: str
    depuis: str


def _git(*arguments: str) -> str:
    resultat = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return resultat.stdout.strip() if resultat.returncode == 0 else ""


def empreinte() -> str:
    """Ce que git connaît des fichiers dont la destruction dépend.

    **`git status --porcelain` et non le commit seul.** Le commit ne dit rien
    d'une modification non commitée, et c'est justement ce qu'un `git stash` ou
    un éditeur laisse derrière. L'empreinte couvre les deux : ce qui est
    enregistré, et ce qui ne l'est pas encore.
    """
    enregistre = _git("rev-parse", "HEAD:examples/stack")
    en_cours = _git("status", "--porcelain", "--", *SUIVIS)
    return f"{enregistre}|{en_cours}"


def poser(run_id: str, cible: str) -> Plateforme:
    """Écrit le verrou. Refuse si une plateforme est déjà debout."""
    existant = lire()
    if existant is not None:
        raise VerrouError(
            f"une plateforme est déjà debout : run {existant.run_id} sur "
            f"{existant.cible}, depuis {existant.depuis}.\n"
            "Un second run la détruirait par son `finally`, et le premier "
            "détruirait ce que le second aura créé.\n"
            f"La détruire, puis retirer {VERROU.relative_to(ROOT)}."
        )
    plateforme = Plateforme(
        run_id=run_id,
        cible=cible,
        commit=_git("rev-parse", "HEAD"),
        branche=_git("rev-parse", "--abbrev-ref", "HEAD"),
        arbre_sale=bool(_git("status", "--porcelain", "--", *SUIVIS)),
        empreinte=empreinte(),
        depuis=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    VERROU.parent.mkdir(parents=True, exist_ok=True)
    VERROU.write_text(json.dumps(asdict(plateforme), indent=2) + "\n", encoding="utf-8")
    return plateforme


def lire() -> Plateforme | None:
    """La plateforme debout, ou `None`."""
    if not VERROU.is_file():
        return None
    try:
        donnees = json.loads(VERROU.read_text(encoding="utf-8"))
        return Plateforme(**donnees)
    except (ValueError, TypeError):
        # Un verrou illisible dit qu'une plateforme **peut** être debout, et
        # c'est l'hypothèse prudente : le supprimer en silence perdrait
        # l'information qui reste.
        raise VerrouError(
            f"{VERROU.relative_to(ROOT)} est illisible. Une plateforme est "
            "peut-être debout : vérifier le compte avant de le retirer."
        ) from None


def derive() -> str:
    """Ce qui a changé sous la plateforme depuis son déploiement, ou ''.

    Rend une phrase à imprimer, jamais une exception : découvrir la dérive ne
    doit pas empêcher la destruction, seulement la préparer.
    """
    plateforme = lire()
    if plateforme is None:
        return ""
    if empreinte() == plateforme.empreinte:
        return ""

    actuel = _git("rev-parse", "--abbrev-ref", "HEAD")
    return (
        "L'ARBRE A CHANGÉ SOUS LA PLATEFORME.\n"
        f"  déployée depuis : {plateforme.commit[:12]} sur {plateforme.branche}"
        f"{' (arbre sale)' if plateforme.arbre_sale else ''}\n"
        f"  détruite depuis : {_git('rev-parse', 'HEAD')[:12]} sur {actuel}\n"
        "\n"
        "`examples/stack/` est versionné, verrou Terraform compris. Une "
        "destruction lancée depuis une définition qui n'est plus celle du "
        "déploiement échoue sur un fournisseur absent, et laisse tout debout.\n"
        f"  git checkout {plateforme.commit[:12]} -- examples/stack\n"
        "puis relancer la destruction, puis `python scripts/residue.py verify`."
    )


def retirer() -> None:
    """Retire le verrou. La plateforme n'est plus debout."""
    VERROU.unlink(missing_ok=True)


def main() -> int:
    plateforme = lire()
    if plateforme is None:
        print("aucune plateforme debout.")
        return 0
    print(
        f"plateforme debout : run {plateforme.run_id} sur {plateforme.cible}, "
        f"depuis {plateforme.depuis}\n"
        f"  déployée depuis {plateforme.commit[:12]} sur {plateforme.branche}"
    )
    message = derive()
    if message:
        print("\n" + message)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
