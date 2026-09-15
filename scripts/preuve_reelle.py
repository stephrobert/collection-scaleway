"""Ce qu'un tir réel a vraiment exercé, dérivé de sa transcription.

Le dépôt publie déjà quatre étages de preuve, et le quatrième, « joué contre une
cible », n'entrait dans aucun document : il dépend d'une exécution, et un bloc
dérivé doit se recalculer hors ligne. Une transcription enregistrée lève
l'objection. Elle est un fichier versionné, donc lisible hors ligne, et elle
porte ce que le réseau a **réellement** transporté.

L'audit du 15 septembre 2026 a nommé le manque en creux : le guide Kubernetes
allait publier une matrice de preuve écrite à la main, et une matrice écrite à
la main est exactement le genre d'affirmation qui survit à ce qui la mesurait.

```text
la transcription   ce qui a circulé, avec son agent, sa méthode et son chemin
le plan            quel module porte quelle route
le rapprochement   quel module a donc tourné pour de vrai
```

**Ce que ce script refuse de faire, et pourquoi.** Il ne devine jamais l'auteur
d'une requête : une ligne sans agent lisible est une erreur, pas une ligne qui
ne compte pas. Compter zéro là où on ne sait pas est la façon la plus discrète
de publier un tableau faux, et un tableau de preuve faux est pire que pas de
tableau du tout.

Usage :

    python scripts/preuve_reelle.py k8s          le rapprochement, en clair
    python scripts/preuve_reelle.py k8s --routes  les routes émises, comptées

Le bloc publié est écrit par `scripts/readme_counters.py`, comme tous les
autres : deux scripts qui écriraient des blocs dérivés finiraient par ne plus
mesurer la même chose.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTIONS = ROOT / "transcriptions"
SPECS = ROOT / "specs" / "scaleway"

#: L'agent que la collection annonce, et par lequel on la distingue.
#:
#: La transcription porte trois agents : celui-ci, celui du provider Terraform
#: qui a bâti la plateforme, et `python-requests` par lequel `scripts/residue.py`
#: prend ses empreintes. Sans ce filtre, le tableau créditerait la collection de
#: tout ce que Terraform a créé, ce qui est à peu près l'inverse de ce que ce
#: dépôt cherche à montrer.
AGENT = "scaleway-sdk-python"

#: Un segment de chemin : tout sauf une barre. Sans cette borne, le gabarit
#: `/clusters/{id}` avalerait `/clusters/{id}/nodes`, et deux modules se
#: disputeraient la même route.
SEGMENT = "[^/]+"


class PreuveError(RuntimeError):
    """Une source manque ou se contredit, et un tableau faux serait pire."""


@dataclass(frozen=True)
class Tir:
    """Une transcription, et ce que la collection y a émis."""

    fichier: Path
    date: str
    routes: Counter[tuple[str, str]]


def _agent(enregistrement: dict[str, object]) -> str:
    """L'agent d'une requête, refusé plutôt que deviné quand il manque."""
    requete = enregistrement.get("req")
    entetes = requete.get("headers") if isinstance(requete, dict) else None
    for nom, valeur in (entetes or {}).items():
        if str(nom).lower() != "user-agent":
            continue
        return valeur if isinstance(valeur, str) else str(valeur[0])
    raise PreuveError(
        f"la requête {enregistrement.get('seq')} ne porte pas d'agent, donc rien "
        "ne dit qui l'a émise. Une ligne qu'on ne sait pas attribuer ne se compte "
        "ni d'un côté ni de l'autre : elle s'explique."
    )


def lire(chemin: Path) -> Tir:
    """Les routes que la collection a émises, comptées.

    La date vient du nom du fichier **et** des horodatages, et les deux doivent
    concorder : un tir renommé sans être rejoué publierait une preuve datée
    d'aujourd'hui sur des mesures d'hier.
    """
    if not chemin.is_file():
        raise PreuveError(f"{chemin} n'existe pas")

    nommee = re.search(r"(\d{4}-\d{2}-\d{2})", chemin.stem)
    if not nommee:
        raise PreuveError(
            f"{chemin.name} ne porte pas sa date. Un tir sans date est une preuve "
            "dont personne ne sait de quand elle parle."
        )

    routes: Counter[tuple[str, str]] = Counter()
    jours: set[str] = set()
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        enregistrement = json.loads(ligne)
        jours.add(str(enregistrement.get("t", ""))[:10])
        if AGENT not in _agent(enregistrement):
            continue
        routes[(enregistrement["method"], enregistrement["path"])] += 1

    if nommee.group(1) not in jours:
        raise PreuveError(
            f"{chemin.name} s'annonce du {nommee.group(1)} et ne porte aucune "
            f"requête de ce jour : {', '.join(sorted(jours))}."
        )
    return Tir(fichier=chemin, date=nommee.group(1), routes=routes)


def _motif(gabarit: str) -> re.Pattern[str]:
    """Le gabarit d'une opération, en motif qui reconnaît un chemin concret.

    Le gabarit est découpé sur ses accolades, et seules les parties littérales
    sont échappées : échapper d'abord puis remplacer obligerait à défaire ce
    qu'on vient de faire, ce qui est le genre de va-et-vient dont on ne sait
    plus, six mois après, s'il couvre bien toutes les formes.
    """
    litteraux = re.split(r"\{[^}]+\}", gabarit)
    return re.compile("^" + SEGMENT.join(re.escape(part) for part in litteraux) + "$")


def _operations(produit: str, version: str) -> dict[str, tuple[tuple[str, str], ...]]:
    """Les routes que chaque module livré porte, lues dans le plan.

    Importé ici plutôt qu'en tête : ce module est aussi appelé par
    `readme_counters`, et le plan coûte une seconde par produit.
    """
    from generator.ansible.collection import load_collection
    from generator.ansible.models import build_module_specs
    from generator.plan import build_plan

    specs, _ = build_module_specs(build_plan(produit, version, spec_root=SPECS), load_collection())
    portees: dict[str, tuple[tuple[str, str], ...]] = {}
    for spec in specs:
        routes = tuple(
            (operation.method, operation.path)
            for operation in (
                spec.get_operation,
                spec.list_operation,
                spec.read_operation,
                spec.update_operation,
                spec.action_operation,
            )
            if operation is not None
        )
        portees[spec.name] = tuple(sorted(set(routes)))
    return portees


def _service(portees: dict[str, tuple[tuple[str, str], ...]]) -> str:
    """Le service d'API du produit, dérivé de ses routes : `/k8s/`.

    **Le premier segment, et pas le préfixe commun.** Le premier essai prenait
    le plus long préfixe partagé par les gabarits, soit
    `/k8s/v1/regions/{region}/`, qui ne préfixe aucun chemin réel : toutes les
    routes du tir étaient écartées avant tout rapprochement, chaque module
    sortait « non atteint », et le tableau était parfaitement lisible et
    entièrement faux. ADR-024 porte la mesure et sa date.

    Le premier segment ne se calcule pas, il se lit. Il a une seconde vertu :
    une route servie par une version d'API que le plan ne porte pas, `/k8s/v2/`
    le jour où elle existera, ressort **orpheline** au lieu de disparaître dans
    un filtre.
    """
    services = {
        chemin.split("/")[1] for routes in portees.values() for _, chemin in routes if "/" in chemin
    }
    if len(services) != 1:
        raise PreuveError(
            f"les routes de ce plan relèvent de {len(services)} service(s) : "
            f"{', '.join(sorted(services)) or 'aucun'}. Le rapprochement ne sait "
            "pas de quel produit il parle."
        )
    return f"/{services.pop()}/"


@dataclass(frozen=True)
class Rapprochement:
    """Ce que le tir prouve, ce qu'il suggère, et ce qu'il laisse dans l'ombre.

    **Trois états, parce qu'une route partagée ne prouve personne.** Un module
    MANAGE lit avant d'écrire (ADR-003), donc `GET /clusters/{id}` est portée
    par `k8s_cluster_info` et par `k8s_cluster`. La requête a circulé ; rien
    dans la transcription ne dit lequel des deux l'a émise.

    Créditer le premier de la liste donnerait un tableau lisible où une moitié
    des « oui » serait un tirage au sort. Les séparer dit la vérité : ce que le
    tir prouve, et ce sur quoi il ne se prononce pas.
    """

    tir: Tir
    atteints: dict[str, int]
    indistincts: tuple[str, ...]
    muets: tuple[str, ...]
    orphelines: tuple[tuple[str, str], ...]


def rapprocher(produit: str, version: str, tir: Tir) -> Rapprochement:
    """Quel module chaque route émise a fait tourner.

    Une route qu'un seul module porte le prouve. Une route que plusieurs
    portent ne prouve aucun d'eux, et les nomme tous comme non distinguables.
    """
    portees = _operations(produit, version)
    service = _service(portees)

    motifs = [
        (nom, methode, _motif(gabarit))
        for nom, routes in portees.items()
        for methode, gabarit in routes
    ]

    atteints: Counter[str] = Counter()
    indistincts: set[str] = set()
    orphelines: list[tuple[str, str]] = []
    for (methode, chemin), combien in sorted(tir.routes.items()):
        if not chemin.startswith(service):
            continue
        trouves = sorted(
            {nom for nom, verbe, motif in motifs if verbe == methode and motif.match(chemin)}
        )
        if len(trouves) == 1:
            atteints[trouves[0]] += combien
        elif trouves:
            indistincts.update(trouves)
        else:
            orphelines.append((methode, chemin))

    # Un module qu'une route distinctive prouve n'est pas indistinct parce
    # qu'une autre de ses routes est partagée : la preuve l'emporte sur le
    # doute, et `k8s_cluster` est prouvé par son PATCH quel que soit le sort de
    # son GET.
    indistincts -= set(atteints)

    # **Un rapprochement qui ne rapproche rien mesure sa propre panne.** Le
    # premier essai filtrait sur un préfixe qui ne préfixait aucun chemin réel :
    # zéro atteint, zéro orpheline, et tous les modules annoncés jamais
    # exercés. Le tableau était parfaitement lisible et entièrement faux, ce
    # qui est exactement le mode de défaillance que ce fichier existe pour
    # éviter.
    #
    # Le critère est l'incohérence, pas le zéro : un tir qui n'émet rien sur ce
    # produit est un fait, un tir qui en émet et dont rien ne se rapproche est
    # un défaut d'outil.
    #
    # **Elle ne consulte pas le filtre qu'elle surveille.** Deux versions de
    # cette garde ont compté les routes « du produit » en réutilisant le filtre
    # suspect, et chacune était donc inerte exactement dans le cas qu'elle
    # devait attraper. Le test l'a dit les deux fois.
    #
    # Le critère ne dépend plus de rien : le tir a transporté des requêtes, et
    # il n'en est sorti ni preuve, ni doute, ni orpheline. Les deux causes
    # possibles sont nommées, parce qu'un tir passé au mauvais produit mérite
    # la même phrase qu'un filtre cassé : dans les deux cas, ce tableau ne
    # mesure plus rien.
    if tir.routes and not atteints and not indistincts and not orphelines:
        raise PreuveError(
            f"{tir.fichier.name} porte {sum(tir.routes.values())} requête(s) de la "
            f"collection, et aucune n'a été rapprochée d'un module de `{produit}` "
            f"ni signalée orpheline. Soit le filtre `{service}` ne reconnaît plus "
            "ces chemins, soit ce tir n'est pas celui de ce produit."
        )

    return Rapprochement(
        tir=tir,
        atteints=dict(sorted(atteints.items())),
        indistincts=tuple(sorted(indistincts)),
        muets=tuple(sorted(set(portees) - set(atteints) - indistincts)),
        orphelines=tuple(orphelines),
    )


def tir_le_plus_recent(produit: str) -> Path:
    """La transcription la plus récente de ce produit.

    Elles sont nommées `<sujet>-<date>.jsonl`, et le sujet n'est pas le nom du
    produit : `kapsule` est le nom commercial de `k8s`. La correspondance est
    donc déclarée là où elle se lit, plutôt que devinée d'un slug.
    """
    sujets = {"k8s": "kapsule"}
    motif = f"{sujets.get(produit, produit)}-*.jsonl"
    tirs = sorted(TRANSCRIPTIONS.glob(motif))
    if not tirs:
        raise PreuveError(
            f"aucune transcription `{motif}` sous {TRANSCRIPTIONS}. Le tableau de "
            "preuve d'un produit vient de son tir, jamais d'une liste écrite."
        )
    return tirs[-1]


def main(argv: list[str]) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("produit", help="le produit, par exemple `k8s`")
    parseur.add_argument("--version", default="v1")
    parseur.add_argument("--routes", action="store_true", help="les routes émises, comptées")
    arguments = parseur.parse_args(argv[1:])

    tir = lire(tir_le_plus_recent(arguments.produit))
    resultat = rapprocher(arguments.produit, arguments.version, tir)

    print(f"{tir.fichier.name}, tir du {tir.date}\n")
    if arguments.routes:
        for (methode, chemin), combien in sorted(tir.routes.items()):
            print(f"{combien:5}  {methode} {chemin}")
        return 0

    for nom, combien in resultat.atteints.items():
        print(f"  atteint        {nom}  ({combien} appel(s))")
    for nom in resultat.indistincts:
        print(f"  indistinct     {nom}  (seule une route partagée a circulé)")
    for nom in resultat.muets:
        print(f"  non atteint    {nom}")
    for methode, chemin in resultat.orphelines:
        print(f"  ORPHELINE      {methode} {chemin}")

    if resultat.orphelines:
        print(
            f"\n{len(resultat.orphelines)} route(s) émises que ce plan ne porte pas. "
            "La collection a appelé quelque chose qu'aucun module ne déclare : "
            "c'est un trou de rapprochement, et le tableau le tairait.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except PreuveError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        raise SystemExit(1) from erreur
