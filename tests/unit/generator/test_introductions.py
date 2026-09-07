"""Le journal des apparitions, et ce que `version_added` publie (ADR-013).

Le défaut corrigé ici n'était pas une panne : chaque module se générait, se
chargeait, passait le sanity, et affirmait une date fausse. Les tests portent
donc sur ce que la page **publie**, pas sur ce que le code calcule.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from generator.ansible.collection import load_collection
from generator.ansible.introductions import (
    Introductions,
    IntroductionsError,
    load_introductions,
)
from generator.ansible.models import build_module_specs
from generator.plan import build_plan

ROOT = Path(__file__).resolve().parents[3]
SPECS = ROOT / "specs" / "scaleway"
MODULES = ROOT / "ansible_collections" / "stephrobert" / "scaleway" / "plugins" / "modules"


def _ecrire(chemin: Path, document: dict) -> Path:
    chemin.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return chemin


def _documentation(source: Path) -> dict:
    """Le bloc `DOCUMENTATION` d'un module livré, lu sans l'importer.

    Un module généré importe le runtime d'Ansible : le lire par AST mesure ce
    que la page publie sans dépendre de ce qui est installé.
    """
    arbre = ast.parse(source.read_text(encoding="utf-8"))
    for noeud in arbre.body:
        if isinstance(noeud, ast.Assign) and any(
            getattr(cible, "id", None) == "DOCUMENTATION" for cible in noeud.targets
        ):
            return yaml.safe_load(ast.literal_eval(noeud.value))
    raise AssertionError(f"{source.name} ne porte pas de bloc DOCUMENTATION")


# --- Ce que la collection livrée publie ------------------------------------


def test_chaque_module_livre_publie_la_date_que_le_journal_lui_donne() -> None:
    """La page dit la version d'apparition, pas celle de la génération.

    C'est la mesure du défaut : avant, chaque module annonçait la version
    courante de la collection, et une page Galaxy est publiée pour toujours.
    """
    journal = load_introductions()
    ecarts = []
    for fichier in sorted(MODULES.glob("*.py")):
        if fichier.name == "__init__.py":
            continue
        publie = _documentation(fichier).get("version_added")
        attendu = journal.module(fichier.stem)
        if publie != attendu:
            ecarts.append(f"{fichier.stem} publie {publie}, le journal dit {attendu}")
    assert ecarts == [], "\n".join(ecarts)


def test_aucun_module_livre_nannonce_la_version_courante_de_la_collection() -> None:
    """L'invariant qui dit que la date n'est plus un horodatage.

    Il tient tant que la version en préparation est postérieure à celle qui est
    publiée, ce que `scripts/introductions.py` refuse de laisser dériver.
    """
    courante = load_collection().version
    livres = [f for f in sorted(MODULES.glob("*.py")) if f.name != "__init__.py"]
    coupables = [f.stem for f in livres if _documentation(f).get("version_added") == courante]
    assert livres, "aucun module examiné : un contrôle qui ne regarde rien passe toujours"
    assert coupables == []


# --- Ce que le modèle construit --------------------------------------------


def test_le_modele_date_un_module_depuis_le_journal_et_non_depuis_la_collection() -> None:
    plan = build_plan("instance", "v1", spec_root=SPECS)
    collection = load_collection()
    specs, _ = build_module_specs(plan, collection, introductions=load_introductions())
    par_nom = {spec.name: spec for spec in specs}
    assert par_nom["instance_server_info"].version_added == "0.1.0"
    assert par_nom["instance_server_info"].version_added != collection.version


def test_une_valeur_de_retour_posterieure_a_son_module_publie_sa_propre_version() -> None:
    """`result` est né en 0.4.0 sur un module de 0.1.0, et la page doit le dire."""
    plan = build_plan("lb", "v1", spec_root=SPECS)
    specs, _ = build_module_specs(plan, load_collection(), introductions=load_introductions())
    spec = next(item for item in specs if item.name == "lb_ip_info")
    retours = spec.return_documentation()
    assert retours["result"]["version_added"] == "0.4.0"
    assert "version_added" not in retours["ips"]


def test_une_option_nee_avec_son_module_ne_repete_pas_sa_date() -> None:
    plan = build_plan("lb", "v1", spec_root=SPECS)
    specs, _ = build_module_specs(plan, load_collection(), introductions=load_introductions())
    spec = next(item for item in specs if item.name == "lb_ip_info")
    options = spec.documentation()["options"]
    assert options
    assert all("version_added" not in entree for entree in options.values())


def test_sans_journal_tout_est_neuf_dans_la_version_courante() -> None:
    """Le repli explicite, celui du contrat de laboratoire.

    Il existe pour qu'une collection sans passé n'ait pas à s'en inventer un ;
    ce n'est pas le chemin de la vraie génération, et le test qui suit le
    prouve.
    """
    plan = build_plan("instance", "v1", spec_root=SPECS)
    collection = load_collection()
    specs, _ = build_module_specs(plan, collection)
    assert {spec.version_added for spec in specs} == {collection.version}


def test_la_generation_par_le_cli_lit_le_journal(tmp_path: Path) -> None:
    """Le vrai chemin de production, mesuré en le faisant tourner.

    Sans ce test, un `build_module_specs` appelé sans journal dans `cli.py`
    laisserait tous les tests verts et republierait la version du jour.
    """
    sortie = tmp_path / "modules"
    resultat = subprocess.run(
        [
            sys.executable,
            "-m",
            "generator",
            "generate",
            "instance",
            "--module",
            "instance_server_info",
            "--output-dir",
            str(sortie),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultat.returncode == 0, resultat.stderr
    publie = _documentation(sortie / "instance_server_info.py")["version_added"]
    assert publie == "0.1.0"


# --- Ce que le chargeur refuse ---------------------------------------------


def test_le_journal_refuse_un_module_date_deux_fois(tmp_path: Path) -> None:
    """L'invariant « une release ne redate rien », rendu mesurable par la forme."""
    chemin = _ecrire(
        tmp_path / "j.yml",
        {
            "en_preparation": "0.3.0",
            "apparitions": {
                "0.1.0": {"modules": ["widget_widget"]},
                "0.2.0": {"modules": ["widget_widget"]},
            },
        },
    )
    with pytest.raises(IntroductionsError, match="daté deux fois"):
        load_introductions(chemin)


def test_le_journal_refuse_une_cle_de_bloc_inconnue(tmp_path: Path) -> None:
    """Une faute de frappe produirait un journal silencieusement inerte."""
    chemin = _ecrire(
        tmp_path / "j.yml",
        {
            "en_preparation": "0.2.0",
            "apparitions": {"0.1.0": {"modules": ["widget_widget"], "retour": {}}},
        },
    )
    with pytest.raises(IntroductionsError, match="clé\\(s\\) inconnue"):
        load_introductions(chemin)


def test_le_journal_refuse_un_membre_date_sur_un_module_absent(tmp_path: Path) -> None:
    chemin = _ecrire(
        tmp_path / "j.yml",
        {
            "en_preparation": "0.3.0",
            "apparitions": {
                "0.1.0": {"modules": ["widget_widget"]},
                "0.2.0": {"options": {"widget_gizmo": ["zone"]}},
            },
        },
    )
    with pytest.raises(IntroductionsError, match="module absent"):
        load_introductions(chemin)


def test_le_journal_refuse_un_bloc_qui_nest_pas_anterieur_a_la_preparation(
    tmp_path: Path,
) -> None:
    """Un bloc daté est une version publiée, donc antérieure à celle qui vient."""
    chemin = _ecrire(
        tmp_path / "j.yml",
        {
            "en_preparation": "0.2.0",
            "apparitions": {"0.2.0": {"modules": ["widget_widget"]}},
        },
    )
    with pytest.raises(IntroductionsError, match="pas antérieur"):
        load_introductions(chemin)


def test_le_journal_refuse_labsence_de_version_en_preparation(tmp_path: Path) -> None:
    chemin = _ecrire(tmp_path / "j.yml", {"apparitions": {"0.1.0": {"modules": ["w"]}}})
    with pytest.raises(IntroductionsError, match="en_preparation"):
        load_introductions(chemin)


def test_un_nom_inconnu_du_journal_recoit_la_version_en_preparation(tmp_path: Path) -> None:
    chemin = _ecrire(
        tmp_path / "j.yml",
        {"en_preparation": "0.9.0", "apparitions": {"0.1.0": {"modules": ["widget_widget"]}}},
    )
    journal = load_introductions(chemin)
    assert journal.module("widget_widget") == "0.1.0"
    assert journal.module("widget_neuf") == "0.9.0"
    # Une option neuve sur un module ancien se date, celle d'un module neuf non.
    assert journal.option("widget_widget", "neuve") == "0.9.0"
    assert journal.option("widget_neuf", "neuve") is None


def test_les_versions_se_comparent_par_leurs_nombres(tmp_path: Path) -> None:
    """`0.10.0` est postérieure à `0.9.0`, ce qu'une comparaison de chaînes rate."""
    chemin = _ecrire(
        tmp_path / "j.yml",
        {
            "en_preparation": "0.11.0",
            "apparitions": {
                "0.9.0": {"modules": ["ancien"]},
                "0.10.0": {"modules": ["recent"]},
            },
        },
    )
    journal = load_introductions(chemin)
    assert journal.module("ancien") == "0.9.0"
    assert journal.module("recent") == "0.10.0"


def test_sans_journal_le_modele_ne_date_rien_de_particulier() -> None:
    vide = Introductions.sans_journal("9.9.9")
    assert vide.module("nimporte") == "9.9.9"
    assert vide.option("nimporte", "option") is None
    assert vide.retour("nimporte", "cle") is None
