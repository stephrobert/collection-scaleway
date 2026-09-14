"""Ce que la collection officielle livre vraiment, mesuré et versionné.

Un produit candidat gagne à être pris **derrière** la collection officielle
plutôt qu'en face d'elle : ils créent des choses que personne n'exploite
ensuite, et « ils le créent, nous l'exploitons » est une frontière qu'un
utilisateur comprend en une phrase (ADR-022).

Encore faut-il savoir ce qu'ils livrent, et c'est là que l'affirmation de
mémoire coûte cher : leur dépôt porte bien plus de modules que leur archive n'en
sert, l'écart étant d'un ordre de grandeur. Un décompte fait sur le dépôt se lit
exactement comme un décompte juste. ADR-022 porte la mesure et sa date.

    python scripts/officielle.py              # lire la mesure versionnée
    python scripts/officielle.py --mesurer    # la refaire, depuis le réseau

**Deux sources, parce qu'aucune ne porte les deux moitiés.** L'archive que
Galaxy sert dit ce qui est livré ; elle ne dit rien de ce qui est écarté, son
`MANIFEST.json` ne portant pas `build_ignore`. Le `galaxy.yml` du dépôt, lui,
nomme chaque fichier écarté, un par un.

La mesure est écrite sous `specs/officielle/`, comme les contrats : une
évolution de leur collection arrive donc comme un diff, jamais comme un
résultat qui change tout seul. Rien de ce qui lit cette mesure ne va sur le
réseau.

Codes de sortie : `0` succès, `1` le programme n'a pas pu faire son travail,
`2` la mesure contredit ce que le dépôt déclare s'interdire.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tarfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast

ROOT = Path(__file__).resolve().parents[1]
MESURE = ROOT / "specs" / "officielle" / "scaleway.scaleway.json"

#: La collection mesurée, et d'où viennent ses deux moitiés.
COLLECTION = "scaleway.scaleway"
GALAXY = "https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections"
DEPOT = "https://raw.githubusercontent.com/scaleway/ansible/main/galaxy.yml"

SCHEMA_VERSION = 1


class Mesure(TypedDict):
    """Ce que la mesure porte, nommé plutôt que deviné à la lecture.

    Un dictionnaire libre laisserait `mesure["modules_livre"]` passer la
    vérification de types et rendre `None` à l'exécution : la faute de frappe
    produirait un rapport qui dit zéro module livré, ce qui est plausible.
    """

    schema_version: int
    collection: str
    version: str
    published_at: str
    measured_at: str
    sources: dict[str, str]
    modules_livres: dict[str, str | None]
    plugins_livres: dict[str, list[str]]
    modules_ecartes: list[str]


#: Ce qu'ils servent bien, et que nous ne reprenons pas. Chaque entrée porte sa
#: raison, comme un override : une frontière sans raison est une frontière que
#: le prochain contributeur déplacera sans savoir ce qu'il défait.
#:
#: `sert` nomme **ce que leur archive livre**, pas ce que leur dépôt contient.
#: C'est ce que `_verifier_ce_quon_leur_laisse` recoupe avec la mesure : une
#: ligne qui s'interdirait quelque chose qu'ils ne livrent plus serait une
#: interdiction fantôme, et elle se lirait comme une décision en vigueur.
CE_QUON_LEUR_LAISSE = (
    {
        "nous": "AccessSecretVersion",
        "sert": "lookup/scaleway_secret",
        "raison": (
            "lit la valeur d'un secret, et c'est exactement ce que leur lookup "
            "fait. Un second chemin vers la même valeur ne rendrait service à "
            "personne et doublerait la surface sur laquelle un secret peut "
            "fuir."
        ),
    },
)


def _lire(url: str, quoi: str) -> bytes:
    """Une lecture réseau, dont l'échec dit ce qu'on n'a pas pu lire."""
    requete = urllib.request.Request(url, headers={"User-Agent": "collection-scaleway"})
    try:
        with urllib.request.urlopen(requete, timeout=60) as reponse:
            return cast(bytes, reponse.read())
    except Exception as erreur:
        raise SystemExit(f"{quoi} illisible : {erreur}") from erreur


def _derniere_version() -> tuple[str, str]:
    """La version que Galaxy sert, et la date à laquelle elle y est arrivée.

    **Ce que Galaxy sert, pas ce que leur dépôt porte.** Un utilisateur installe
    l'archive publiée ; le dépôt peut être en avance de plusieurs mois, et
    mesurer le dépôt reviendrait à décrire une collection que personne n'a.
    """
    charge = json.loads(
        _lire(
            f"{GALAXY}/index/{COLLECTION.replace('.', '/')}/versions/?limit=1",
            "la liste des versions publiées",
        )
    )
    versions = charge.get("data") or []
    if not versions:
        raise SystemExit(f"Galaxy ne sert aucune version de {COLLECTION}")
    return versions[0]["version"], (versions[0].get("created_at") or "")[:10]


#: Le paramètre qui dit la forme d'un module. Leur patron est `state:
#: present/absent` sur tout, ce qui est le calque du SDK que ce dépôt refuse.
_ETAT = re.compile(r"^\s*state\s*=\s*dict\(", re.MULTILINE)
_CHOIX_ETAT = re.compile(r"choices\s*=\s*\[([^\]]*)\]")


def _forme(source: str) -> str | None:
    """La forme d'un module, lue dans son code plutôt que supposée.

    Rend les choix de `state` quand le module en porte un, et `None` sinon. Le
    `None` est l'information intéressante : c'est le module qui ne suit pas leur
    patron, donc celui dont la frontière avec nous demande à être regardée.
    """
    if not _ETAT.search(source):
        return None
    choix = _CHOIX_ETAT.search(source, _ETAT.search(source).start())  # type: ignore[union-attr]
    if not choix:
        return "state, sans choix déclarés"
    return "/".join(sorted(m.strip(" '\"") for m in choix.group(1).split(",") if m.strip()))


def _depuis_archive(version: str) -> tuple[dict[str, str | None], dict[str, list[str]]]:
    """Ce que l'archive publiée contient, ouverte en mémoire."""
    archive = _lire(
        f"{GALAXY}/artifacts/{COLLECTION.replace('.', '-')}-{version}.tar.gz",
        f"l'archive de {COLLECTION} {version}",
    )
    modules: dict[str, str | None] = {}
    plugins: dict[str, list[str]] = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for membre in tar.getmembers():
            parties = Path(membre.name).parts
            if len(parties) != 3 or parties[0] != "plugins" or not membre.isfile():
                continue
            genre, fichier = parties[1], Path(parties[2]).stem
            if not membre.name.endswith(".py") or fichier.startswith("__"):
                continue
            if genre == "modules":
                extrait = tar.extractfile(membre)
                source = extrait.read().decode("utf-8", "replace") if extrait else ""
                modules[fichier] = _forme(source)
            elif genre in ("inventory", "lookup"):
                plugins.setdefault(genre, []).append(fichier)
    return (
        dict(sorted(modules.items())),
        {genre: sorted(noms) for genre, noms in sorted(plugins.items())},
    )


def _depuis_depot() -> list[str]:
    """Les modules que leur `galaxy.yml` écarte de l'archive, un par un.

    **L'exclusion n'est pas un accident.** Chaque fichier écarté y est nommé,
    ce qui en fait une décision lisible plutôt qu'un effet de bord de motif.
    """
    import yaml

    declare = yaml.safe_load(_lire(DEPOT, "le galaxy.yml du dépôt officiel"))
    ecartes = [
        Path(ligne).stem
        for ligne in (declare.get("build_ignore") or [])
        if ligne.startswith("plugins/modules/")
    ]
    return sorted(ecartes)


def mesurer() -> Mesure:
    """La mesure complète, depuis ses deux sources."""
    version, publiee = _derniere_version()
    modules, plugins = _depuis_archive(version)
    return Mesure(
        schema_version=SCHEMA_VERSION,
        collection=COLLECTION,
        version=version,
        published_at=publiee,
        measured_at=datetime.now(UTC).strftime("%Y-%m-%d"),
        sources={"galaxy": GALAXY, "repository": DEPOT},
        modules_livres=modules,
        plugins_livres=plugins,
        modules_ecartes=_depuis_depot(),
    )


def lire() -> Mesure:
    """La mesure versionnée, hors ligne.

    Elle est absente tant que personne ne l'a faite, et c'est un échec de
    programme, pas un verdict : « je n'ai pas la mesure » et « la mesure dit
    non » ne sont pas la même chose.
    """
    if not MESURE.exists():
        raise SystemExit(
            f"{MESURE.relative_to(ROOT)} n'existe pas. `mise run sync:officielle` "
            "la produit ; ce programme ne va jamais sur le réseau tout seul."
        )
    return cast(Mesure, json.loads(MESURE.read_text(encoding="utf-8")))


def _verifier_ce_quon_leur_laisse(mesure: Mesure) -> list[str]:
    """Chaque chose qu'on s'interdit est-elle encore servie par eux ?

    **Une interdiction fantôme se lit comme une décision en vigueur.** Le jour
    où ils cessent de livrer leur lookup de secrets, la raison de ne pas écrire
    `AccessSecretVersion` tombe, et personne ne le remarquerait si rien ne
    recoupait les deux.
    """
    livres = {f"{genre}/{nom}" for genre, noms in mesure["plugins_livres"].items() for nom in noms}
    livres |= {f"modules/{nom}" for nom in mesure["modules_livres"]}
    return [
        f"{entree['nous']} : {entree['sert']} n'est plus livré par "
        f"{mesure['collection']} {mesure['version']}"
        for entree in CE_QUON_LEUR_LAISSE
        if entree["sert"] not in livres
    ]


def rendre(mesure: Mesure) -> str:
    """La mesure, pour un terminal."""
    modules = mesure["modules_livres"]
    ecartes = mesure["modules_ecartes"]
    formes = {forme for forme in modules.values() if forme}
    lignes = [
        f"{mesure['collection']} {mesure['version']}, publiée le {mesure['published_at']}",
        f"mesurée le {mesure['measured_at']}",
        "",
        f"  {len(modules) + len(ecartes):>3} modules écrits dans leur dépôt",
        f"  {len(modules):>3} modules livrés dans l'archive",
        f"  {len(ecartes):>3} écartés, nommés un par un dans leur `build_ignore`",
        "",
        "  livrés :",
    ]
    lignes += [f"    {nom:<32} {forme or 'pas de `state`'}" for nom, forme in modules.items()]
    lignes += [
        "",
        f"  forme de ces {len(modules)} : "
        + (", ".join(sorted(formes)) if len(formes) == 1 else "hétérogène"),
        "",
        "  plugins livrés :",
    ]
    lignes += [
        f"    {genre}/{nom}" for genre, noms in mesure["plugins_livres"].items() for nom in noms
    ]
    lignes += ["", "  ce qu'on leur laisse, et pourquoi :"]
    for entree in CE_QUON_LEUR_LAISSE:
        lignes.append(f"    {entree['nous']} -> {entree['sert']}")
        lignes.append(f"      {entree['raison']}")
    return "\n".join(lignes)


def main(argv: list[str]) -> int:
    parametres = argparse.ArgumentParser(description=__doc__)
    parametres.add_argument(
        "--mesurer",
        action="store_true",
        help="refaire la mesure depuis le réseau et l'écrire sous specs/officielle/",
    )
    options = parametres.parse_args(argv[1:])

    if options.mesurer:
        mesure = mesurer()
        MESURE.parent.mkdir(parents=True, exist_ok=True)
        MESURE.write_text(
            json.dumps(mesure, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"mesure écrite dans {MESURE.relative_to(ROOT)}\n")
    else:
        mesure = lire()

    print(rendre(mesure))

    perimees = _verifier_ce_quon_leur_laisse(mesure)
    if perimees:
        print("\nce que le dépôt s'interdit ne correspond plus à ce qu'ils livrent :")
        for ligne in perimees:
            print(f"  {ligne}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
