"""Détecter puis diagnostiquer, jamais détecter puis modifier.

Un rulebook qui éteindrait des machines sur un événement mal formé est le mode
de défaillance que `power_schedule` refuse par construction, déplacé là où
personne ne le relit : un événement est atteignable par un tiers d'une façon
qu'une ligne de commande n'est pas (#212).

Ces tests tiennent cette frontière, et ils la tiennent en **dérivant** ce qu'un
playbook fait plutôt qu'en se fiant à son nom. Un playbook renommé garderait un
nom rassurant ; ce qu'il appelle, non.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[3]
COLLECTION = RACINE / "ansible_collections" / "stephrobert" / "scaleway"
RULEBOOKS = COLLECTION / "extensions" / "eda" / "rulebooks"


def _rulebooks() -> list[Path]:
    return sorted(RULEBOOKS.glob("*.yml")) if RULEBOOKS.is_dir() else []


def _playbooks_declenches(rulebook: Path) -> set[str]:
    """Les playbooks qu'une règle lance, lus dans la structure."""
    lances: set[str] = set()
    for jeu in yaml.safe_load(rulebook.read_text(encoding="utf-8")) or []:
        for regle in jeu.get("rules", []) or []:
            action = regle.get("action") or {}
            nom = (action.get("run_playbook") or {}).get("name")
            if nom:
                lances.add(nom.removeprefix("stephrobert.scaleway."))
    return lances


def _ecrit(playbook: str) -> bool:
    """Ce playbook appelle-t-il autre chose qu'une lecture ?

    Dérivé du rôle quand il y en a un, du playbook sinon. Se fier au nom
    laisserait passer un `fleet_report` qui se serait mis à écrire, et c'est
    exactement le genre de dérive qu'une garde doit voir.
    """
    sources = [COLLECTION / "playbooks" / f"{playbook}.yml"]
    role = COLLECTION / "roles" / playbook / "tasks"
    if role.is_dir():
        sources.extend(sorted(role.glob("*.yml")))

    appels: set[str] = set()
    for chemin in sources:
        if chemin.is_file():
            appels |= set(
                re.findall(
                    r"^\s+(?:-\s+)?stephrobert\.scaleway\.([a-z0-9_]+):",
                    chemin.read_text(encoding="utf-8"),
                    flags=re.MULTILINE,
                )
            )
    return any(not nom.endswith("_info") for nom in appels)


def test_il_y_a_un_rulebook_a_mesurer() -> None:
    """Une garde qui mesure zéro sujet ne dit pas que tout va bien."""
    assert _rulebooks(), "aucun rulebook livré : ces gardes ne mesureraient rien"


def test_une_reaction_ne_declenche_que_des_lectures() -> None:
    """C'est toute la frontière, et elle est délibérée.

    L'autoremédiation viendra si quelqu'un la demande, avec ce qu'elle exige :
    une garde sur ce qu'elle a le droit de toucher, et une trace de ce qu'elle
    a fait. En attendant, lire le parc est la moitié utile et la sûre.
    """
    for rulebook in _rulebooks():
        lances = _playbooks_declenches(rulebook)
        assert lances, f"{rulebook.name} ne lance aucun playbook : il ne réagit à rien"

        ecrivains = sorted(nom for nom in lances if _ecrit(nom))
        assert ecrivains == [], (
            f"{rulebook.name} déclenche {ecrivains}, qui écrivent. Un événement "
            "est atteignable par un tiers d'une façon qu'une ligne de commande "
            "n'est pas, et une réaction qui écrit sur un événement mal formé est "
            "le défaut que les enchaînements refusent par construction"
        )


def test_chaque_playbook_declenche_est_livre() -> None:
    """Une réaction qui lancerait un playbook absent échouerait au premier événement."""
    livres = {chemin.stem for chemin in (COLLECTION / "playbooks").glob("*.yml")}

    for rulebook in _rulebooks():
        absents = sorted(_playbooks_declenches(rulebook) - livres)
        assert absents == [], f"{rulebook.name} lance des playbooks absents : {absents}"


def test_un_evenement_inattendu_est_nomme_plutot_quignore() -> None:
    """Une charge utile que personne n'a vérifiée est ce sur quoi une règle
    finit par tirer. Le dire coûte une règle, et ça évite un déclenchement
    silencieux sur autre chose."""
    for rulebook in _rulebooks():
        jeux = yaml.safe_load(rulebook.read_text(encoding="utf-8")) or []
        conditions = [
            regle.get("condition", "") for jeu in jeux for regle in (jeu.get("rules") or [])
        ]
        assert any("is not defined" in condition for condition in conditions), (
            f"{rulebook.name} n'a aucune règle pour un événement qui ne porte pas "
            "ce qu'il attend : il l'ignorerait en silence"
        )
