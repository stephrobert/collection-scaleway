"""`strict` annonce un arrêt qu'il ne produit pas seul, et la page doit le dire.

Le guide l'explique bien, et `integration.py` le mesure dans les deux sens.
C'est la **page courte** qui promettait autre chose, et c'est elle
qu'`ansible-doc` imprime et que Galaxy rend (#176). Un utilisateur qui laisse
le défaut `true` et n'ouvre jamais le guide se croit couvert : sa chaîne
d'intégration passe au vert sur zéro machine avec une clé révoquée.

Le nom de la variable d'environnement se lit **dans la mesure**, par AST, jamais
recopié ici. Une variable renommée dans ce qu'on exerce rend alors la page
fausse tout de suite, au lieu de la laisser vieillir : c'est exactement le
défaut que cette issue a relevé, et le recopier le reproduirait.
"""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[3]
PLUGIN = (
    RACINE
    / "ansible_collections"
    / "stephrobert"
    / "scaleway"
    / "plugins"
    / "inventory"
    / "compute.py"
)
INTEGRATION = RACINE / "scripts" / "integration.py"
GUIDE = RACINE / "docs" / "guides" / "dynamic-inventory.md"

MESURE = "check_strict_mode_is_visible"


def _garde_mesuree() -> str:
    """La variable que la mesure d'intégration passe vraiment à Ansible.

    Lue dans le code plutôt qu'écrite ici : c'est ce qui fait de ce test un
    lien entre la page et l'exercice, et pas deux affirmations côte à côte.
    """
    arbre = ast.parse(INTEGRATION.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.FunctionDef) or noeud.name != MESURE:
            continue
        noms = {
            cle.value
            for dictionnaire in ast.walk(noeud)
            if isinstance(dictionnaire, ast.Dict)
            for cle in dictionnaire.keys
            if isinstance(cle, ast.Constant)
            and isinstance(cle.value, str)
            and cle.value.startswith("ANSIBLE_")
        }
        assert len(noms) == 1, (
            f"`{MESURE}` passe {sorted(noms)} : ce test attend la seule variable "
            "qui rend le refus visible, et il faut le rouvrir si elle se dédouble"
        )
        return noms.pop()
    raise AssertionError(
        f"`{MESURE}` a disparu de integration.py : plus rien ne mesure la "
        "rétrogradation, et la description ne s'appuie alors sur rien"
    )


def _description_de_strict() -> str:
    texte = PLUGIN.read_text(encoding="utf-8")
    debut = texte.index('DOCUMENTATION = r"""') + len('DOCUMENTATION = r"""')
    documentation = yaml.safe_load(texte[debut : texte.index('"""', debut)])
    option = documentation["options"]["strict"]
    return " ".join(" ".join(option["description"]).split())


def test_la_description_nomme_la_variable_qui_rend_le_refus_visible() -> None:
    """Sans elle, `strict: true` écrit la raison et n'arrête rien."""
    garde = _garde_mesuree()

    assert garde in _description_de_strict(), (
        f"la description de `strict` ne nomme pas {garde}. C'est la page "
        "qu'`ansible-doc` imprime : ce qu'elle tait ne se lit nulle part ailleurs"
    )


def test_la_description_dit_quansible_retrograde_lechec() -> None:
    """Nommer la variable sans dire pourquoi laisse le lecteur deviner."""
    description = _description_de_strict().lower()

    assert "downgrade" in description, (
        "la description donne le remède sans le symptôme : ce qui surprend "
        "l'utilisateur est qu'Ansible rétrograde l'échec, pas le nom de la variable"
    )


def test_le_guide_et_la_page_nomment_la_meme_variable() -> None:
    """Deux documents qui divergent valent moins qu'un seul.

    C'est l'asymétrie que l'issue relève : le document long disait vrai, la page
    courte disait autre chose, et c'est la page courte qui est publiée à côté de
    l'option.
    """
    garde = _garde_mesuree()

    assert garde in GUIDE.read_text(encoding="utf-8"), (
        f"le guide ne nomme plus {garde} alors que la mesure l'exerce"
    )
