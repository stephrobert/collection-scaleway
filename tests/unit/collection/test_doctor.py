"""Chaque contrôle du `doctor` peut rougir, et un `?` ne se lit pas comme un oui.

Un vert qui ne peut pas devenir rouge est une décoration, et ce playbook existe
précisément pour remplacer des diagnostics décoratifs. Ces tests le jouent pour
de vrai, dans des configurations qui doivent le faire échouer.

**Rien ici ne touche à un compte Scaleway.** `SCW_API_URL` désigne un port que
personne n'écoute : le module échoue à joindre l'API, ce qui est justement le
cas que le troisième état doit distinguer d'un refus.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[3]
PLAYBOOK = RACINE / "ansible_collections/stephrobert/scaleway/playbooks/doctor.yml"
#: Un port sans personne derrière. La boucle locale refuse la connexion tout de
#: suite, donc le test ne dépend ni du réseau ni d'un délai d'attente.
PORT_MORT = "http://127.0.0.1:4999"


def _jouer(*options: str, environnement: dict[str, str] | None = None) -> tuple[int, str]:
    base = {
        "PATH": f"/usr/bin:/bin:{RACINE}/.venv/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "ANSIBLE_COLLECTIONS_PATH": str(RACINE),
        "SCW_API_URL": PORT_MORT,
    }
    resultat = subprocess.run(
        ["ansible-playbook", str(PLAYBOOK), *options],
        env={**base, **(environnement or {})},
        capture_output=True,
        text=True,
        timeout=300,
    )
    return resultat.returncode, resultat.stdout + resultat.stderr


def _rapport(sortie: str) -> list[str]:
    """Les lignes du rapport, telles que le playbook les imprime."""
    return [
        ligne.strip().strip(",").strip('"')
        for ligne in sortie.splitlines()
        if ligne.strip().startswith(('"ok ', '"ko ', '"? '))
    ]


@pytest.fixture(scope="module")
def ansible_disponible() -> None:
    if not (RACINE / ".venv" / "bin" / "ansible-playbook").is_file():
        pytest.skip("ansible-playbook absent de l'environnement")


# --- ce que chaque contrôle fait quand il doit dire non --------------------


def test_un_ansible_core_trop_ancien_rougit(ansible_disponible: None) -> None:
    """Le seuil vient de `meta/runtime.yml` et il est mesuré ; le forcer falsifie
    la comparaison, pas la mesure."""
    code, sortie = _jouer("-e", "core_minimum=99.0.0")

    assert code != 0, "un core trop ancien doit faire échouer le doctor"
    lignes = _rapport(sortie)
    assert any(ligne.startswith("ko") and "ansible-core" in ligne for ligne in lignes), lignes
    assert "the collection requires >= 99.0.0" in sortie


def test_un_sdk_trop_ancien_rougit(ansible_disponible: None) -> None:
    code, sortie = _jouer("-e", "sdk_minimum=99.0.0")

    assert code != 0
    assert any(ligne.startswith("ko") and "SDK" in ligne for ligne in _rapport(sortie)), _rapport(
        sortie
    )


def test_aucune_source_didentifiants_rougit(ansible_disponible: None, tmp_path: Path) -> None:
    """`HOME` vide écarte le fichier de configuration, et l'environnement est nu."""
    code, sortie = _jouer(environnement={"HOME": str(tmp_path), "SCW_API_URL": PORT_MORT})

    assert code != 0
    lignes = _rapport(sortie)
    assert any(ligne.startswith("ko") and "no credential source" in ligne for ligne in lignes), (
        lignes
    )


# --- le troisième état, et ce qui le distingue -----------------------------


def test_une_api_injoignable_est_un_point_dinterrogation_pas_un_refus(
    ansible_disponible: None, tmp_path: Path
) -> None:
    """Ne pas avoir pu regarder n'est pas avoir mesuré un refus.

    La distinction vit dans le rapport : le verdict final échoue dans les deux
    cas, parce que quelqu'un dont l'API est injoignable n'est pas prêt, mais le
    message ne prétend pas avoir mesuré ce qu'il n'a pas vu.

    **L'environnement est posé, pas hérité.** La première version lisait les
    identifiants de la machine : elle passait sur un poste qui en a et
    rougissait sur le runner qui n'en a pas, où le message portait aussi un
    `not ready`. Des identifiants factices et un `HOME` vide rendent le cas
    reproductible, et le contrôle des sources ne teste que leur présence.
    """
    code, sortie = _jouer(
        environnement={
            "HOME": str(tmp_path),
            "SCW_API_URL": PORT_MORT,
            "SCW_ACCESS_KEY": "SCW" + "XXXXXXXXXXXXXXXXXXX",
            "SCW_SECRET_KEY": "11111111-2222-3333-4444-555555555555",
        }
    )

    lignes = _rapport(sortie)
    injoignable = [ligne for ligne in lignes if ligne.startswith("?")]
    assert injoignable, lignes
    assert "could not be reached, so nothing is known" in injoignable[0]
    assert code != 0, "un doctor qui n'a pas pu vérifier l'API ne dit pas Ready"
    assert "not verified" in sortie
    assert "not ready" not in sortie, "rien n'a été mesuré comme faux ici"


def test_le_rapport_sort_meme_quand_un_controle_rougit(ansible_disponible: None) -> None:
    """Un contrôle qui arrêterait le play cacherait ceux d'après.

    C'est le comportement que ce playbook remplace : découvrir un problème par
    exécution est la façon la plus sûre de dépenser un premier contact pour rien.
    """
    _, sortie = _jouer("-e", "core_minimum=99.0.0")

    lignes = _rapport(sortie)
    assert len(lignes) == 4, f"les quatre contrôles doivent figurer au rapport : {lignes}"


# --- ce qu'il ne dit jamais ------------------------------------------------


def test_aucune_valeur_didentifiant_ne_sort(ansible_disponible: None) -> None:
    """La source se nomme, la valeur jamais : un rapport se colle dans un ticket."""
    factice_acces = "SCW" + "XXXXXXXXXXXXXXXXXXX"
    factice_secret = "11111111-2222-3333-4444-555555555555"

    _, sortie = _jouer(
        environnement={
            "SCW_API_URL": PORT_MORT,
            "SCW_ACCESS_KEY": factice_acces,
            "SCW_SECRET_KEY": factice_secret,
        }
    )

    assert factice_acces not in sortie
    assert factice_secret not in sortie
    # Et pourtant il dit d'où elles viennent, sinon il n'aiderait personne.
    assert "SCW_ACCESS_KEY (environment)" in sortie
