"""Le paquet s'interroge en entier, et sans supposer combien il porte de plugins.

Deux hypothèses vivaient dans `scripts/package.py`, et toutes deux tenaient par
la taille de la collection au jour où elles ont été écrites.

**Un module sur cinquante.** Le contrôle interrogeait `instance_server_info`,
« module représentatif ». Un module cassé parmi les quarante-neuf autres passait.

**Un seul plugin d'inventaire.** Le contrôle refusait explicitement d'en voir
deux. C'est la même hypothèse que le nom écrit en dur, déplacée du nom vers le
nombre, et le nom écrit en dur avait déjà coûté un diagnostic.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import package
import pytest

from generator.ansible.collection import Collection


def _collection(racine: Path) -> Collection:
    return Collection(namespace="demo", name="widget", version="0.0.1", path=racine)


def test_un_repertoire_de_plugins_inconnu_est_refuse(tmp_path: Path) -> None:
    """Une découverte qui ignore ce qu'elle ne connaît pas est une passoire.

    Le jour où un `lookup/` apparaît, il doit être interrogé. Le jour où un
    répertoire que ce contrôle ne sait pas traiter apparaît, il doit le dire :
    un plugin ignoré est un plugin hors de la preuve, et personne ne s'en
    apercevrait.
    """
    (tmp_path / "plugins" / "modules").mkdir(parents=True)
    (tmp_path / "plugins" / "quelque_chose_de_neuf").mkdir(parents=True)

    with pytest.raises(package.PackageError, match="quelque_chose_de_neuf"):
        package.check_types_de_plugins(_collection(tmp_path))


def test_les_repertoires_connus_passent(tmp_path: Path) -> None:
    """`modules`, `module_utils` et `doc_fragments` ne s'interrogent pas ainsi.

    Ce ne sont pas des omissions : `modules` a son propre contrôle,
    `module_utils` est du code partagé, et un `doc_fragment` se vérifie fondu
    dans la documentation des modules qui l'incorporent.
    """
    for nom in ("modules", "module_utils", "doc_fragments", "inventory"):
        (tmp_path / "plugins" / nom).mkdir(parents=True)

    package.check_types_de_plugins(_collection(tmp_path))


def test_un_paquet_sans_module_est_refuse(tmp_path: Path) -> None:
    """Zéro module interrogé est un vert qui ne dit rien.

    C'est le défaut qui avait rendu un `ansible-test sanity` vert sur zéro
    fichier examiné, et il ne coûte rien de le refuser ici aussi.
    """
    (tmp_path / "plugins" / "modules").mkdir(parents=True)

    with pytest.raises(package.PackageError, match="aucun module"):
        package.check_installed(tmp_path, _collection(tmp_path))


def test_un_module_que_larchive_ne_documente_pas_est_refuse(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Interroger les cinquante ne prouve rien sans regarder les cinquante réponses.

    C'est le fond du défaut : le contrôle interrogeait un « module
    représentatif », et un module cassé parmi les quarante-neuf autres passait.
    Ici, `ansible-doc` répond pour les deux modules, et le second ne porte
    aucune `short_description` : le paquet doit être refusé, et le module
    nommé.
    """
    modules = tmp_path / "plugins" / "modules"
    modules.mkdir(parents=True)
    for nom in ("instance_server_info", "lb_lb_info"):
        (modules / f"{nom}.py").write_text("", encoding="utf-8")

    reponse = json.dumps(
        {
            "demo.widget.instance_server_info": {
                "doc": {"short_description": "Read servers", "options": {"zone": {}}}
            },
            "demo.widget.lb_lb_info": {"doc": {"options": {"zone": {}}}},
        }
    )
    monkeypatch.setattr(
        package.subprocess,
        "run",
        lambda commande, **_: subprocess.CompletedProcess(commande, 0, reponse, ""),
    )

    with pytest.raises(package.PackageError) as erreur:
        package.check_installed(tmp_path, _collection(tmp_path))

    assert "lb_lb_info" in str(erreur.value)


def test_le_depot_interroge_tous_ses_modules() -> None:
    """Ce que le contrôle couvre aujourd'hui, sur la collection livrée.

    Le seul test du fichier qui regarde le dépôt : les autres prouvent que la
    garde sait refuser, celui-ci dit ce qu'elle mesure.
    """
    from generator.ansible.collection import load_collection

    collection = load_collection()
    modules = sorted(
        chemin.stem
        for chemin in (collection.path / "plugins" / "modules").glob("*.py")
        if not chemin.stem.startswith("_")
    )
    assert len(modules) >= 50, f"{len(modules)} modules : la collection a-t-elle rétréci ?"
    package.check_types_de_plugins(collection)
