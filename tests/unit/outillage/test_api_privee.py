"""Ce que le contrôle des API privées refuse, et ce qu'il laisse passer.

Il est né de deux occurrences réelles : le runtime appelait
`scaleway_core.api.API._request`, l'a quitté **parce que c'était privé**, puis
écrivait `requests.Response._content` (#132). Une règle qu'on énonce sans la
mesurer se réintroduit par la porte d'à côté.
"""

from __future__ import annotations

from pathlib import Path

import api_privee


def _fichier(dossier: Path, contenu: str) -> Path:
    chemin = dossier / "module.py"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_ecrire_un_attribut_prive_dune_bibliotheque_est_refuse(tmp_path: Path) -> None:
    """La ligne exacte que le runtime portait."""
    chemin = _fichier(
        tmp_path,
        "import json\n\n\ndef f(response, charge):\n    response._content = json.dumps(charge)\n",
    )
    acces = api_privee.examiner(chemin)
    assert [entree.expression for entree in acces] == ["response._content"]


def test_lire_un_attribut_prive_dune_bibliotheque_est_refuse(tmp_path: Path) -> None:
    """L'écriture n'est pas le seul couplage : lire engage autant."""
    chemin = _fichier(tmp_path, "def f(client):\n    return client._profile\n")
    assert [entree.expression for entree in api_privee.examiner(chemin)] == ["client._profile"]


def test_un_attribut_prive_sur_soi_est_le_style_du_depot(tmp_path: Path) -> None:
    """`self._client` n'engage aucune dépendance : c'est du privé à soi.

    Sans ce contre-exemple, le contrôle refuserait tout le runtime, et on le
    désactiverait.
    """
    chemin = _fichier(
        tmp_path,
        "class A:\n"
        "    def __init__(self, module):\n"
        "        self._module = module\n"
        "    def f(self):\n"
        "        return self._module\n",
    )
    assert api_privee.examiner(chemin) == []


def test_un_protocole_du_langage_nest_pas_un_attribut_prive(tmp_path: Path) -> None:
    """`__doc__`, `__name__` : documentés par Python, pas par une bibliothèque."""
    chemin = _fichier(tmp_path, "def f(x):\n    return x.__class__.__name__ + str(x.__doc__)\n")
    assert api_privee.examiner(chemin) == []


def test_lacces_est_signale_avec_sa_ligne(tmp_path: Path) -> None:
    """Un contrôle qui dit qu'un défaut existe sans dire où ne sert à rien."""
    chemin = _fichier(tmp_path, "def f(r):\n    pass\n\n\ndef g(r):\n    return r._raw\n")
    acces = api_privee.examiner(chemin)
    assert [(entree.ligne, entree.expression) for entree in acces] == [(6, "r._raw")]


def test_le_code_livre_du_depot_est_conforme() -> None:
    """Le seul test du fichier qui regarde le dépôt, et c'est voulu."""
    fichiers = sorted(api_privee.LIVRE.rglob("*.py"))
    assert fichiers, "aucun fichier examiné : un contrôle qui ne regarde rien passe toujours"
    acces = [
        f"{entree.fichier.name}:{entree.ligne} {entree.expression}"
        for chemin in fichiers
        for entree in api_privee.examiner(chemin)
    ]
    assert acces == [], "\n".join(acces)
