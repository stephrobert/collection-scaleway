"""Le mode strict sort-il vraiment en 2, et sur quoi ?

La règle 9 du projet dit que les codes de sortie sont stables et que la CI en
dépend : `0` succès, `1` erreur, `2` opération non triée ou override orphelin.
Rien ne le vérifiait.

**C'est un contrôle qui cherche une absence**, et c'est pour ça qu'il se
maquille tout seul : `report --strict` sort en 0 quand tout est classé, ce qui
est le cas sur les deux produits. Un mode strict cassé rendrait exactement la
même chose, 0, sur un dépôt sain. Le témoin n'avait jamais été planté pour le
seul mécanisme dont la sortie est un code que la CI lit.

Les contrats sont construits ici, minuscules, plutôt que pris sur Instance : ces
tests ne doivent pas rougir le jour où Scaleway ajoute une opération.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from generator.cli import main

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_UNDECIDED = 2


def _contrat(chemin: Path, operations: dict[str, dict[str, str]]) -> None:
    """Un document OpenAPI réduit à ce que la classification regarde."""
    paths: dict[str, dict[str, object]] = {}
    for identifiant, forme in operations.items():
        paths.setdefault(forme["chemin"], {})[forme["methode"]] = {
            "operationId": identifiant,
            "responses": {"200": {"description": "ok"}},
        }
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        yaml.safe_dump(
            {
                "openapi": "3.1.0",
                "info": {"title": "Laboratoire", "version": "v1"},
                "paths": paths,
                "components": {"schemas": {}},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def _lancer(tmp_path: Path, specs: Path, overrides: Path) -> int:
    return main(
        [
            "--spec-root",
            str(specs),
            "--overrides-root",
            str(overrides),
            "report",
            "labo",
            "--api-version",
            "v1",
            "--output-dir",
            str(tmp_path / "rapports"),
            "--strict",
        ]
    )


@pytest.fixture
def racines(tmp_path: Path) -> tuple[Path, Path]:
    specs = tmp_path / "specs"
    overrides = tmp_path / "overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    return specs, overrides


def test_une_operation_quaucune_regle_ne_tranche_sort_en_deux(
    tmp_path: Path, racines: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """`PUT` avec un verbe qui n'est pas une écriture : rien ne la classe."""
    specs, overrides = racines
    _contrat(
        specs / "labo.v1.yml",
        {
            "ListWidgets": {"chemin": "/widgets", "methode": "get"},
            "AttachWidget": {"chemin": "/widgets/{id}/attachment", "methode": "put"},
        },
    )
    assert _lancer(tmp_path, specs, overrides) == EXIT_UNDECIDED
    assert "1 opération(s) non classée(s)" in capsys.readouterr().err


def test_un_override_dont_la_cle_ne_designe_rien_sort_en_deux(
    tmp_path: Path, racines: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """La clé dépend de la ressource déduite : corriger une ressource déplace la clé."""
    specs, overrides = racines
    _contrat(specs / "labo.v1.yml", {"ListWidgets": {"chemin": "/widgets", "methode": "get"}})
    (overrides / "labo.yml").write_text(
        yaml.safe_dump(
            {
                "operations": {
                    "labo.v1.Widget.CetteOperationNexistePas": {
                        "generation": "ignore",
                        "reason": "un override dont la clé ne désigne rien est inerte, "
                        "et une faute de frappe en produit un",
                    }
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    assert _lancer(tmp_path, specs, overrides) == EXIT_UNDECIDED
    assert "1 override(s) orphelin(s)" in capsys.readouterr().err


def test_un_contrat_sans_operation_est_rouge(
    tmp_path: Path, racines: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """Zéro non classée et zéro orpheline, donc tout va bien : le vert le plus gratuit."""
    specs, overrides = racines
    _contrat(specs / "labo.v1.yml", {})
    assert _lancer(tmp_path, specs, overrides) == EXIT_ERROR
    assert "ne déclare aucune opération" in capsys.readouterr().err


def test_un_contrat_entierement_classe_sort_en_zero(
    tmp_path: Path, racines: tuple[Path, Path]
) -> None:
    """Le cas voisin, qui ne doit pas bouger : sans lui les trois autres ne prouvent rien.

    Un mode strict qui sortirait en 2 sur tout ferait passer les trois tests
    précédents, et rougirait la CI sur un dépôt sain.
    """
    specs, overrides = racines
    _contrat(
        specs / "labo.v1.yml",
        {
            "ListWidgets": {"chemin": "/widgets", "methode": "get"},
            "RebootWidget": {"chemin": "/widgets/{id}/action", "methode": "post"},
        },
    )
    assert _lancer(tmp_path, specs, overrides) == EXIT_OK
