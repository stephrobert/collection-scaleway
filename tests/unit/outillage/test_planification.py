"""Un enchaînement qu'on lance à la main reste une démonstration.

`power_schedule` ne vaut qu'appelé deux fois par jour, et rien ne disait comment
on en arrive là (#184). Le guide donne trois chemins, et l'important n'est pas
les trois chemins : c'est qu'il dise **lequel a tourné**.

Ces tests tiennent cette distinction. Une page qui présenterait les trois comme
équivalents affirmerait trois choses en en ayant mesuré une, et c'est exactement
le motif que ce dépôt refuse ailleurs.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
GUIDE = RACINE / "docs" / "guides" / "scheduling.md"
LANCEUR = RACINE / "scripts" / "quickstart.py"
PLAYBOOKS = RACINE / "ansible_collections" / "stephrobert" / "scaleway" / "playbooks"

#: L'enchaînement que le guide donne comme éprouvé. Il est nommé ici parce que
#: c'est le lien que les tests tiennent : la page l'annonce rejoué, et le
#: lanceur doit le rejouer.
EPROUVE = "power_schedule"


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _non_playbooks() -> set[str]:
    """Ce qui porte le préfixe de la collection sans être un playbook.

    Lu sur le disque plutôt qu'écrit ici : la liste à la main valait
    `{"scaleway"}` dans `example_coverage.py`, et le jour où le plugin a été
    renommé en `compute`, ce contrôle a refusé un playbook valide en disant
    que `compute` n'en était pas un. Il avait raison sur la forme et tort sur
    le fond.
    """
    collection = RACINE / "ansible_collections" / "stephrobert" / "scaleway"
    plugins = {
        chemin.stem
        for genre in ("inventory", "lookup", "modules", "filter")
        for chemin in (collection / "plugins" / genre).glob("*.py")
        if chemin.stem != "__init__"
    }
    # Les rulebooks se citent par leur nom complet comme les playbooks, et n'en
    # sont pas. Lus sur le disque pour la même raison que les plugins : la
    # liste écrite à la main a déjà refusé un nom valide le jour d'un renommage.
    rulebooks = {
        chemin.stem for chemin in (collection / "extensions" / "eda" / "rulebooks").glob("*.yml")
    }
    return plugins | rulebooks


def test_le_guide_part_denchainements_livres() -> None:
    """« Pas d'un playbook inventé pour la page », dit l'issue.

    Un guide qui documenterait la planification d'un playbook d'illustration
    planifierait une illustration.
    """
    livres = {chemin.stem for chemin in PLAYBOOKS.glob("*.yml")}
    cites = set(re.findall(r"stephrobert\.scaleway\.([a-z0-9_]+)", _guide()))

    assert cites, "le guide ne cite plus aucun playbook"
    absents = sorted(cites - livres - _non_playbooks())
    assert absents == [], f"le guide planifie des playbooks qui n'existent pas : {absents}"


def _etapes_jouees() -> dict[str, str]:
    """Les étapes que le lanceur joue vraiment, et le code de chacune.

    Lues dans la table `ETAPES` plutôt que cherchées au texte : une fonction
    qui reste écrite et que plus rien n'appelle laisserait un `grep` vert, et
    c'est la forme la plus courante d'un contrôle qui ne contrôle plus.
    """
    arbre = ast.parse(LANCEUR.read_text(encoding="utf-8"))
    corps = {
        noeud.name: ast.get_source_segment(LANCEUR.read_text(encoding="utf-8"), noeud) or ""
        for noeud in ast.walk(arbre)
        if isinstance(noeud, ast.FunctionDef)
    }

    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Assign):
            continue
        if not any(isinstance(cible, ast.Name) and cible.id == "ETAPES" for cible in noeud.targets):
            continue
        appelees = [
            element.elts[1].id
            for element in getattr(noeud.value, "elts", [])
            if isinstance(element, ast.Tuple)
            and len(element.elts) == 2
            and isinstance(element.elts[1], ast.Name)
        ]
        return {nom: corps.get(nom, "") for nom in appelees}

    raise AssertionError("la table `ETAPES` a disparu du lanceur : il ne joue plus de parcours")


def test_le_chemin_annonce_eprouve_est_celui_que_le_depot_rejoue() -> None:
    """La seule affirmation du guide qui puisse être fausse en silence.

    Le guide dit que `power_schedule` est rejoué par `scripts/quickstart.py`.
    Si l'étape sort du parcours, la page continue de l'annoncer, et personne
    ne le voit : c'est précisément une affirmation que rien ne vérifie.
    """
    jouant = [nom for nom, code in _etapes_jouees().items() if EPROUVE in code]

    assert jouant, (
        f"aucune étape jouée n'appelle `{EPROUVE}`, que le guide annonce rejoué. "
        "L'un des deux ment, et c'est la page qu'on croira"
    )
    assert "quickstart.py" in _guide(), "le guide n'indique plus où le chemin éprouvé est rejoué"


def test_le_guide_dit_ce_qui_na_pas_tourne() -> None:
    """Les deux autres chemins sont donnés comme non éprouvés, pas comme égaux."""
    guide = _guide()

    assert "not tested" in guide, (
        "aucun chemin n'est déclaré non éprouvé : soit les trois ont tourné, "
        "soit la page présente comme mesuré ce qui ne l'est pas"
    )
    assert "measured once" in guide, (
        "le guide ne distingue plus ce qui a tourné une fois de ce qui est rejoué"
    )


def test_aucun_identifiant_nest_ecrit_dans_le_guide() -> None:
    """« Les identifiants passent par le mécanisme de la plateforme. »

    Chaque exemple les prend de son environnement, de ses secrets ou de son
    injecteur. Une valeur écrite ici serait recopiée telle quelle par le
    premier lecteur pressé.
    """
    guide = _guide()

    for ligne in guide.splitlines():
        for variable in ("SCW_ACCESS_KEY", "SCW_SECRET_KEY"):
            if f"{variable}:" not in ligne and f"{variable}=" not in ligne:
                continue
            assert ("{{" in ligne) or ("${{" in ligne) or ("--penv" in ligne), (
                f"« {ligne.strip()} » donne une valeur au lieu de la demander à la plateforme"
            )


def test_chaque_chemin_nomme_la_garde_qui_rend_le_refus_visible() -> None:
    """`strict: true` seul écrit la raison et n'arrête rien (#176).

    Une planification qui tourne sur un inventaire vide et rend compte d'un
    succès est pire qu'une planification qui ne tourne pas. Les trois chemins
    doivent donc nommer la variable, chacun dans sa forme.
    """
    sections = re.split(r"^## ", _guide(), flags=re.MULTILINE)[1:]
    chemins = [
        section
        for section in sections
        if section.startswith(("Scheduled CI", "ansible-navigator", "AWX"))
    ]
    assert len(chemins) == 3, f"le guide ne donne plus trois chemins : {len(chemins)}"

    muets = [
        section.splitlines()[0]
        for section in chemins
        if "ANY_UNPARSED_IS_FAILED" not in section and "inventory file above" not in section
    ]
    assert muets == [], (
        f"ces chemins ne disent pas comment rendre un refus d'inventaire visible : {muets}"
    )
