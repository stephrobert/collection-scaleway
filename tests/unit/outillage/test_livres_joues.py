"""Un playbook livré est joué contre la vraie API, ou déclaré avec sa raison.

Le gabarit de pull request pose la règle : « Run against the real account before
closing ». Le mécanisme qui va sur le compte réel ne visitait pas le répertoire
des playbooks livrés, si bien qu'aucun des sept n'y avait jamais été joué (#196).

Le manque était invisible parce que rien ne le mesurait : `integration.py` les
joue contre l'émulateur, ce qui prouve leur forme et pas leur fond. Ces tests
tiennent la table qui répare ça, et refusent qu'un playbook neuf y échappe.
"""

from __future__ import annotations

from pathlib import Path

import example
import pytest

RACINE = Path(__file__).resolve().parents[3]


def test_chaque_playbook_livre_a_une_entree() -> None:
    """Un playbook écrit n'est pas un playbook qui a tourné."""
    livres = {chemin.name for chemin in example.LIVRES_DIR.glob("*.yml")}

    assert livres, "le répertoire des playbooks livrés ne se lit plus"
    manquants = sorted(livres - set(example.LIVRES))
    assert manquants == [], (
        f"playbook(s) livré(s) sans entrée : {manquants}. Les jouer ou les "
        "déclarer sans cible avec leur raison, jamais les laisser en silence"
    )


def test_aucune_entree_ne_designe_un_playbook_absent() -> None:
    """Une entrée orpheline décrit un playbook qui n'existe plus."""
    livres = {chemin.name for chemin in example.LIVRES_DIR.glob("*.yml")}

    orphelines = sorted(set(example.LIVRES) - livres)
    assert orphelines == [], f"entrée(s) sans playbook : {orphelines}"


def test_une_entree_porte_des_variables_ou_une_raison() -> None:
    """Ne pas jouer un playbook est une décision, et une décision se motive."""
    for nom, entree in sorted(example.LIVRES.items()):
        assert ("variables" in entree) != ("sans_cible" in entree), (
            f"{nom} : une entrée porte ses variables, ou la raison de ne pas la jouer"
        )
        if "sans_cible" in entree:
            assert len(entree["sans_cible"]) > 40, (
                f"{nom} : « {entree['sans_cible']} » ne dit pas pourquoi"
            )


def test_un_playbook_livre_inconnu_fait_echouer_la_cible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """La garde mord : c'est elle qui rend le manque impossible à répéter.

    Le répertoire est remplacé par un faux : le test mesure la fonction, et pas
    l'état du dépôt, qui est vert par construction.
    """
    (tmp_path / "doctor.yml").write_text("", encoding="utf-8")
    (tmp_path / "surprise.yml").write_text("", encoding="utf-8")
    monkeypatch.setattr(example, "LIVRES_DIR", tmp_path)

    with pytest.raises(example.ExempleError) as erreur:
        example.jouer_les_livres({}, {"zone": "fr-par-1"})

    assert "surprise.yml" in str(erreur.value)
    assert "sans entrée" in str(erreur.value)


def test_ce_qui_ecrit_remet_la_plateforme_comme_il_la_trouvee() -> None:
    """`power_schedule` éteint puis rallume : sinon le `destroy` diverge.

    Une plateforme laissée de travers fait échouer la destruction sur un état
    qui n'est plus celui du déploiement, et c'est ce qui laisse des ressources
    facturées debout.
    """
    entree = example.LIVRES["power_schedule.yml"]

    assert entree["variables"]["desired_state"] == "off"
    assert entree["puis"]["desired_state"] == "on"
    assert entree["variables"]["group"] == entree["puis"]["group"]


def test_aucun_playbook_qui_ecrit_ne_vise_le_bastion() -> None:
    """L'éteindre couperait la route que les playbooks SSH empruntent."""
    for nom, entree in sorted(example.LIVRES.items()):
        for variables in (entree.get("variables"), entree.get("puis")):
            groupe = (variables or {}).get("group")
            if groupe is not None:
                assert "bastion" not in groupe, f"{nom} vise {groupe}"
                assert groupe == "scw_tag_etage_charge", (
                    f"{nom} vise {groupe} : le groupe vient de l'étiquette que la "
                    "stack pose sur le tier web et applicatif, jamais d'un défaut"
                )
