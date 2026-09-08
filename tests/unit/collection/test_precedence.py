"""L'ordre de priorité des identifiants, et les trois documents qui l'annoncent.

Le défaut corrigé ici n'était pas dans le code : le runtime a toujours fait
passer un paramètre avant l'environnement, et l'environnement avant le fichier.
C'est le README publié sur Galaxy qui annonçait l'inverse, et rien ne pouvait le
dire, parce qu'une phrase ne se compare à rien.

Deux mesures, donc, et elles ne se remplacent pas :

* ce que le runtime **fait**, en mettant les trois sources en conflit ;
* ce que les documents **disent**, comparé au même ordre.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

ROOT = Path(__file__).resolve().parents[3]
COLLECTION = ROOT / "ansible_collections" / "stephrobert" / "scaleway"

#: Les documents publiés qui décrivent cet ordre, et la ligne qui l'introduit.
#: Ils sont nommés ici plutôt que découverts : une découverte par motif
#: n'aurait rien trouvé le jour où l'un d'eux serait renommé, et un contrôle
#: qui n'examine rien passe toujours.
DOCUMENTS: tuple[Path, ...] = (
    COLLECTION / "README.md",
    COLLECTION / "plugins" / "doc_fragments" / "scaleway.py",
    ROOT / "docs" / "architecture" / "runtime.md",
)


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

    return scaleway


def _profil(**champs: Any) -> SimpleNamespace:
    """Un profil SDK complet, celui que le fichier de configuration donnerait."""
    valeurs: dict[str, Any] = {
        "access_key": None,
        "secret_key": None,
        "api_url": None,
        "api_allow_insecure": None,
        "user_agent": None,
        "default_organization_id": None,
        "default_project_id": None,
    }
    valeurs.update(champs)
    return SimpleNamespace(**valeurs)


def _client(runtime: Any, monkeypatch: Any, *, fichier: str, joue: dict[str, Any]) -> Any:
    """Construit le client comme un module le ferait, fichier de config compris.

    `joue` est ce que le playbook écrit. L'environnement est posé par le test ;
    c'est `env_fallback`, dans l'`argument_spec`, qui le fait entrer, et c'est
    précisément l'étage qu'un test de `build_client_from_values` seul ne
    traverserait pas.
    """
    monkeypatch.setattr(
        runtime.Profile,
        "from_config_file_and_env",
        staticmethod(lambda *_a: _profil(access_key=fichier)),
    )
    monkeypatch.setattr(runtime.Client, "from_profile", staticmethod(lambda profil: profil))

    resultat = ArgumentSpecValidator(runtime.scaleway_argument_spec()).validate(joue)
    assert not resultat.error_messages, resultat.error_messages
    return runtime.build_client_from_values(dict(resultat.validated_parameters))


def test_un_parametre_lemporte_sur_lenvironnement_et_sur_le_fichier(
    runtime: Any, monkeypatch: Any
) -> None:
    """Les trois sources en conflit sur le même champ, et une seule gagne.

    C'est ce qu'un playbook écrit **exprès** pour viser un compte précis. Croire
    qu'une variable d'environnement le supplante conduit à travailler sur le
    mauvais projet en pensant faire le contraire, et l'API ne dit rien : les
    identifiants sont valides, juste pas ceux qu'on croyait.
    """
    monkeypatch.setenv("SCW_ACCESS_KEY", "SCWENVIRONNEMENTXXXX")
    client = _client(
        runtime,
        monkeypatch,
        fichier="SCWFICHIERXXXXXXXXXX",
        joue={"access_key": "SCWPARAMETREXXXXXXXX"},
    )
    assert client.access_key == "SCWPARAMETREXXXXXXXX"


def test_lenvironnement_lemporte_sur_le_fichier(runtime: Any, monkeypatch: Any) -> None:
    """Le deuxième rang, sans lequel le premier ne prouverait qu'un extrême."""
    monkeypatch.setenv("SCW_ACCESS_KEY", "SCWENVIRONNEMENTXXXX")
    client = _client(runtime, monkeypatch, fichier="SCWFICHIERXXXXXXXXXX", joue={})
    assert client.access_key == "SCWENVIRONNEMENTXXXX"


def test_le_fichier_sert_quand_rien_dautre_ne_le_dit(runtime: Any, monkeypatch: Any) -> None:
    """Le contre-exemple : le troisième rang doit encore servir à quelque chose.

    Sans lui, un runtime qui ignorerait purement le fichier passerait les deux
    tests précédents.
    """
    monkeypatch.delenv("SCW_ACCESS_KEY", raising=False)
    client = _client(runtime, monkeypatch, fichier="SCWFICHIERXXXXXXXXXX", joue={})
    assert client.access_key == "SCWFICHIERXXXXXXXXXX"


#: Ce qui annonce la priorité dans un texte publié, et autour de quoi la
#: chercher. Sans cette fenêtre, « configuration file » se trouverait dans la
#: description de l'option `config_file`, à mille caractères de la phrase qui
#: parle d'ordre, et le contrôle jugerait deux passages sans rapport.
ANNONCE = re.compile(r"precedence", re.I)
FENETRE = 400


def _fenetres(texte: str) -> list[str]:
    """Les passages qui annoncent un ordre, espaces normalisés."""
    plat = " ".join(texte.split())
    return [
        plat[max(0, trouve.start() - FENETRE) : trouve.end() + FENETRE]
        for trouve in ANNONCE.finditer(plat)
    ]


def _rangs_trouves(passage: str, precedence: tuple[tuple[str, ...], ...]) -> list[int]:
    """La position de chaque rang dans le passage, par sa première formulation."""
    minuscules = passage.lower()
    positions = []
    for formulations in precedence:
        vues = [minuscules.find(mot) for mot in formulations if mot in minuscules]
        positions.append(min(vues) if vues else -1)
    return positions


@pytest.mark.parametrize("document", DOCUMENTS, ids=lambda chemin: chemin.name)
def test_chaque_document_publie_lordre_que_le_runtime_applique(
    runtime: Any, document: Path
) -> None:
    """Trois documents, trois formulations, un seul ordre.

    Le README de la collection a annoncé l'inverse jusqu'à la 0.4.0, et le
    fragment de documentation disait juste : deux pages publiées se
    contredisaient sans que rien ne le remarque.
    """
    passages = _fenetres(document.read_text(encoding="utf-8"))
    assert passages, f"{document.name} n'annonce aucune priorité"

    complets = 0
    for passage in passages:
        positions = _rangs_trouves(passage, runtime.PRECEDENCE)
        if min(positions) < 0:
            continue
        complets += 1
        assert positions == sorted(positions), (
            f"{document.name} annonce les sources dans l'ordre {positions} :\n{passage}"
        )
    assert complets, f"{document.name} ne nomme pas les trois sources autour de « precedence »"


def test_le_controle_mord_sur_la_phrase_publiee_jusqua_la_0_4_0(runtime: Any) -> None:
    """La phrase exacte que Galaxy a servie, et que rien ne comparait à rien.

    Sans ce test, le contrôle ci-dessus ne prouverait que sa propre indulgence :
    il passe sur trois documents qui viennent d'être corrigés, ce qui ne dit pas
    qu'il aurait refusé celui d'avant.
    """
    ancienne = (
        "Through the environment, through the Scaleway configuration file, "
        "or through module parameters, in that order of precedence:"
    )
    positions = _rangs_trouves(_fenetres(ancienne)[0], runtime.PRECEDENCE)
    assert min(positions) >= 0, "les trois sources sont bien nommées, c'est l'ordre qui ment"
    assert positions != sorted(positions)


def test_la_priorite_na_quune_definition(runtime: Any) -> None:
    """Aucun document ne réécrit l'ordre pour son compte.

    Une seconde liste ordonnée quelque part serait une seconde source, et deux
    sources d'une même chose finissent toujours par diverger : c'est ce qui
    s'est passé entre le README et le fragment.
    """
    fichiers = [
        chemin
        for chemin in (ROOT / "ansible_collections").rglob("*.py")
        if "PRECEDENCE" in chemin.read_text(encoding="utf-8")
    ]
    assert [chemin.name for chemin in fichiers] == ["scaleway.py"]
    assert len(runtime.PRECEDENCE) == 3
    assert all(re.fullmatch(r"[a-z ]+", mot) for rang in runtime.PRECEDENCE for mot in rang)
