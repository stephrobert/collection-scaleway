"""D'où les compteurs publiés tirent leurs nombres, et ce qu'ils refusent.

Le défaut mesuré : un test qui lançait une génération restreinte à un module
écrivait son compte rendu dans `build/reports`, celui dont les blocs dérivés
tirent leur compte. Le README a publié le compte de ce seul module, et `--check`
l'a déclaré conforme, parce qu'il compare le bloc à cette même source. ADR-007
porte la mesure et sa date.

Un bloc dérivé ne protège de rien si sa source peut être écrasée par autre
chose qu'une mesure du dépôt.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import readme_counters

COMPLET = """\
# Génération : instance v1

Contrat : `instance.v1.yml`
Modules écrits : **28**, écartés : **2**

## Ce qui n'est pas écrit

| raison | modules |
|---|---|
| classe WORKFLOW : aucun renderer à ce stade (2) | `a`, `b` |
"""

RESTREINT = """\
# Génération : instance v1

Contrat : `instance.v1.yml`
Modules écrits : **1**, écartés : **29**

## Ce qui n'est pas écrit

| raison | modules |
|---|---|
| non demandé : `--module` restreint cette production (29) | `a`, `b` |
"""


@pytest.fixture
def rapports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un répertoire de comptes rendus à nous, jamais celui du dépôt."""
    monkeypatch.setattr(readme_counters, "RAPPORTS", tmp_path)
    return tmp_path


def test_une_generation_complete_donne_ses_deux_comptes(rapports: Path) -> None:
    (rapports / "instance.v1.generation.md").write_text(COMPLET, encoding="utf-8")
    assert readme_counters._modules_ecrits() == (28, 30)


def test_les_produits_sadditionnent(rapports: Path) -> None:
    """Le compteur n'a longtemps lu qu'`instance.v1` : le contre-exemple reste."""
    (rapports / "instance.v1.generation.md").write_text(COMPLET, encoding="utf-8")
    (rapports / "lb.v1.generation.md").write_text(
        COMPLET.replace("**28**", "**22**").replace("**2**", "**0**"), encoding="utf-8"
    )
    assert readme_counters._modules_ecrits() == (50, 52)


def test_un_compte_rendu_de_generation_restreinte_est_refuse(rapports: Path) -> None:
    """Il se lit comme une mesure du dépôt, et il n'en est pas une.

    Refuser plutôt que compter, parce qu'un nombre faux dans un bloc dérivé se
    lit exactement comme un nombre juste.
    """
    (rapports / "instance.v1.generation.md").write_text(RESTREINT, encoding="utf-8")
    with pytest.raises(readme_counters.CompteursError, match="génération restreinte"):
        readme_counters._modules_ecrits()


def test_un_seul_compte_rendu_restreint_suffit_a_refuser(rapports: Path) -> None:
    """Le mélange est le cas réel : un produit complet, l'autre restreint."""
    (rapports / "instance.v1.generation.md").write_text(RESTREINT, encoding="utf-8")
    (rapports / "lb.v1.generation.md").write_text(COMPLET, encoding="utf-8")
    with pytest.raises(readme_counters.CompteursError, match="génération restreinte"):
        readme_counters._modules_ecrits()


def test_aucun_compte_rendu_est_une_erreur_et_non_un_zero(rapports: Path) -> None:
    """Un bloc annonçant zéro module produit passerait pour un dépôt vide."""
    with pytest.raises(readme_counters.CompteursError, match="aucun compte rendu"):
        readme_counters._modules_ecrits()
