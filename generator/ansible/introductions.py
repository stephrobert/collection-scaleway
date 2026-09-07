"""Quand chaque module, option et valeur de retour est entré dans la collection.

`version_added` répond à une question qu'un utilisateur ne peut pas trancher
autrement : **puis-je appeler ce module avec la version que j'ai épinglée ?**
La réponse est un fait historique. Le contrat ne la porte pas, le classifieur
ne peut pas la déduire, et le générateur ne doit pas la deviner.

Jusqu'à la 0.4.0 il la devinait quand même, en publiant la version courante de
la collection : chaque génération redatait donc tous les modules du jour où
elle tournait (#125). Une page Galaxy est publiée pour toujours, et celles-là
affirmaient une date fausse. ADR-013 porte la mesure et la décision.

Ce module lit le journal des apparitions, et rien d'autre. Trois propriétés le
tiennent, et chacune a son refus :

* **un nom n'apparaît qu'une fois.** Le journal est fait de blocs datés ; un
  nom présent dans deux blocs est une apparition redatée, et le chargement
  échoue. C'est l'invariant « une release ne change jamais un `version_added`
  existant », rendu mesurable par la forme du fichier plutôt qu'écrit dans un
  commentaire ;
* **un bloc ne porte que les clés attendues.** Une faute de frappe sur
  `retours` produirait un journal silencieusement inerte, exactement comme un
  override dont le champ n'existe pas ;
* **ce qui n'est pas encore daté reçoit `en_preparation`**, une valeur écrite à
  la main dans le même fichier. Ce n'est pas une devinette : c'est une décision
  déclarée, et `scripts/introductions.py` la confronte à ce que les fragments
  de changelog impliquent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]

#: Le journal, versionné à côté du code qui le lit.
DEFAULT_JOURNAL = Path(__file__).resolve().parent / "introductions.yml"

#: Les seules clés qu'un bloc daté accepte. Une clé inconnue est refusée
#: plutôt qu'ignorée : un `retour` au singulier ne daterait rien, et rien ne le
#: dirait.
_BLOCK_KEYS: frozenset[str] = frozenset({"modules", "options", "retours"})


class IntroductionsError(ValueError):
    """Le journal des apparitions est absent, mal formé, ou il se contredit."""


def _rang(version: str) -> tuple[int, ...]:
    """Ordonne deux numéros de version, et refuse ce qui n'en est pas un.

    Comparer `"0.10.0"` et `"0.9.0"` comme des chaînes rendrait le mauvais
    verdict, et le mauvais verdict serait silencieux.
    """
    morceaux = version.split(".")
    try:
        return tuple(int(morceau) for morceau in morceaux)
    except ValueError as erreur:
        raise IntroductionsError(
            f"« {version} » n'est pas un numéro de version comparable : {erreur}"
        ) from erreur


@dataclass(frozen=True)
class Introductions:
    """Le journal chargé, interrogeable par nom.

    Les tables sont des `MappingProxyType` : le modèle est gelé de bout en
    bout, et une étape ne peut pas dater un module au passage.
    """

    en_preparation: str
    modules: Mapping[str, str]
    options: Mapping[tuple[str, str], str]
    retours: Mapping[tuple[str, str], str]

    @classmethod
    def sans_journal(cls, version: str) -> Introductions:
        """Un journal vide : tout est neuf, et daté de `version`.

        C'est l'état d'une collection qui n'a rien publié, et c'est ce que le
        contrat de laboratoire veut : ses modules n'ont pas d'histoire, et leur
        golden ne doit pas bouger quand celle de la vraie collection avance.
        """
        return cls(
            en_preparation=version,
            modules=MappingProxyType({}),
            options=MappingProxyType({}),
            retours=MappingProxyType({}),
        )

    def module(self, nom: str) -> str:
        """La version où ce module est apparu, ou celle en préparation."""
        return self.modules.get(nom, self.en_preparation)

    def option(self, module: str, option: str) -> str | None:
        """La version d'une option, **et seulement si elle diffère du module**.

        Rendre la même valeur que le module ferait publier le même badge sur
        chaque option de chaque page, ce qui n'apprend rien et noie celui qui
        compte.

        Une option que le journal ne connaît pas est **neuve**, et reçoit donc
        la version en préparation. Le journal est exhaustif : s'il ne la
        nomme pas, c'est qu'elle n'existait pas.
        """
        return self._posterieure(module, self.options.get((module, option)))

    def retour(self, module: str, cle: str) -> str | None:
        """La version d'une valeur de retour, si elle est postérieure au module."""
        return self._posterieure(module, self.retours.get((module, cle)))

    def _posterieure(self, module: str, version: str | None) -> str | None:
        """La version d'un membre, tue quand elle est celle de son module."""
        effective = version or self.en_preparation
        return None if effective == self.module(module) else effective

    @property
    def connus(self) -> frozenset[str]:
        """Les modules que le journal date déjà."""
        return frozenset(self.modules)


def _lire_bloc(
    version: str,
    bloc: Any,
    modules: dict[str, str],
    options: dict[tuple[str, str], str],
    retours: dict[tuple[str, str], str],
) -> None:
    """Verse un bloc daté dans les tables, en refusant toute redatation."""
    if not isinstance(bloc, dict):
        raise IntroductionsError(f"apparitions.{version} n'est pas un mapping")

    inconnues = sorted(set(bloc) - _BLOCK_KEYS)
    if inconnues:
        raise IntroductionsError(
            f"apparitions.{version} : clé(s) inconnue(s) {inconnues} ; "
            f"attendu {sorted(_BLOCK_KEYS)}"
        )

    for nom in bloc.get("modules") or ():
        if nom in modules:
            raise IntroductionsError(
                f"le module {nom} est daté deux fois : {modules[nom]} puis {version}. "
                "Un journal s'ajoute, il ne se réécrit pas."
            )
        modules[str(nom)] = version

    for cle, table in (("options", options), ("retours", retours)):
        contenu = bloc.get(cle) or {}
        if not isinstance(contenu, dict):
            raise IntroductionsError(f"apparitions.{version}.{cle} n'est pas un mapping")
        for module, noms in contenu.items():
            for nom in noms or ():
                paire = (str(module), str(nom))
                if paire in table:
                    raise IntroductionsError(
                        f"{cle[:-1]} {module}.{nom} est daté deux fois : "
                        f"{table[paire]} puis {version}. "
                        "Un journal s'ajoute, il ne se réécrit pas."
                    )
                table[paire] = version


def load_introductions(chemin: Path | None = None) -> Introductions:
    """Charge le journal, et refuse un journal qui se contredit."""
    source = chemin or DEFAULT_JOURNAL
    if not source.is_file():
        raise IntroductionsError(f"journal des apparitions absent : {source}")

    with source.open(encoding="utf-8") as flux:
        document: Any = yaml.safe_load(flux)
    if not isinstance(document, dict):
        raise IntroductionsError(f"{source} ne contient pas un mapping")

    en_preparation = document.get("en_preparation")
    if not isinstance(en_preparation, str) or not en_preparation:
        raise IntroductionsError(
            f"{source} : `en_preparation` absent. Sans lui, un module neuf "
            "n'aurait aucune date, et le générateur devrait en inventer une."
        )
    rang_prepa = _rang(en_preparation)

    apparitions = document.get("apparitions") or {}
    if not isinstance(apparitions, dict):
        raise IntroductionsError(f"{source} : `apparitions` n'est pas un mapping")

    modules: dict[str, str] = {}
    options: dict[tuple[str, str], str] = {}
    retours: dict[tuple[str, str], str] = {}

    # Trié : deux blocs versés dans l'ordre du fichier donneraient deux messages
    # d'erreur différents pour la même contradiction.
    for version in sorted(apparitions, key=_rang):
        if _rang(str(version)) >= rang_prepa:
            raise IntroductionsError(
                f"{source} : le bloc {version} n'est pas antérieur à la version en "
                f"préparation {en_preparation}. Un bloc daté est une version publiée."
            )
        _lire_bloc(str(version), apparitions[version], modules, options, retours)

    # Une option ou un retour daté sur un module que le journal ne connaît pas
    # est un orphelin : il ne date rien, et une faute de frappe le produirait.
    orphelins = sorted(
        {module for module, _ in (*options, *retours)} - set(modules),
    )
    if orphelins:
        raise IntroductionsError(
            f"{source} : option(s) ou retour(s) datés sur un module absent du journal : {orphelins}"
        )

    return Introductions(
        en_preparation=en_preparation,
        modules=MappingProxyType(modules),
        options=MappingProxyType(options),
        retours=MappingProxyType(retours),
    )
