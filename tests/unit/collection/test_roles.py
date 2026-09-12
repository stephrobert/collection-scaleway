"""Un playbook est l'ergonomie, un rôle est l'API d'exploitation.

Les playbooks livrés étaient des produits finis qu'on lance. Pour qu'une équipe
les adopte, il lui faut pouvoir appeler la même logique depuis ses playbooks,
ses workflows AWX, sa CI, sans recopier l'implémentation (#207).

Ces tests tiennent les trois choses qu'une mise en rôle peut casser sans que
rien d'autre ne le dise :

* **deux implémentations d'une même opération divergent toujours.** Le jour où
  elles divergent, personne ne sait laquelle de la documentation et du code a
  raison ;
* **les faits d'un rôle fuient chez qui l'inclut.** Un `set_fact: selection`
  atterrit dans les faits du playbook appelant et écrase le sien. C'est un
  défaut qui n'existe qu'une fois le code devenu rôle ;
* **un contrat d'arguments absent fait échouer à la troisième tâche** ce qui
  aurait dû échouer au démarrage.
"""

from __future__ import annotations

from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[3]
COLLECTION = RACINE / "ansible_collections" / "stephrobert" / "scaleway"
ROLES = COLLECTION / "roles"
PLAYBOOKS = COLLECTION / "playbooks"


def _roles() -> list[Path]:
    if not ROLES.is_dir():
        return []
    return sorted(chemin for chemin in ROLES.iterdir() if (chemin / "tasks" / "main.yml").is_file())


def _taches(chemin: Path) -> list[dict]:
    """Toutes les tâches du fichier, blocs compris, à plat.

    Un `block:` porte des tâches que le parcours doit voir : une garde qui ne
    regarderait que le premier niveau laisserait passer tout ce qui est protégé
    par une condition, c'est à dire l'essentiel d'un rôle qui refuse avant
    d'agir.
    """
    charge = yaml.safe_load(chemin.read_text(encoding="utf-8")) or []

    def _aplatir(taches: list) -> list[dict]:
        trouvees: list[dict] = []
        for tache in taches:
            if not isinstance(tache, dict):
                continue
            trouvees.append(tache)
            for cle in ("block", "rescue", "always"):
                trouvees.extend(_aplatir(tache.get(cle) or []))
        return trouvees

    return _aplatir(charge)


def test_il_y_a_des_roles_a_mesurer() -> None:
    """Sans ça, tout ce fichier serait vert sur rien.

    C'est la même précaution que `docs_quality` prend : une porte qui mesure
    zéro sujet ne dit pas que tout va bien, elle dit qu'elle n'a rien regardé.
    """
    assert _roles(), "aucun rôle : ces gardes ne mesureraient plus rien"


def test_chaque_role_porte_un_contrat_darguments() -> None:
    """Ansible le valide lui-même, et il le fait avant la première tâche."""
    for role in _roles():
        chemin = role / "meta" / "argument_specs.yml"
        assert chemin.is_file(), f"{role.name} n'a pas de contrat d'arguments"

        specs = yaml.safe_load(chemin.read_text(encoding="utf-8"))["argument_specs"]["main"]
        assert specs.get("options"), f"{role.name} déclare un contrat sans option"
        for nom, option in specs["options"].items():
            assert option.get("description"), f"{role.name} : `{nom}` sans description"


def test_les_options_dun_role_portent_son_nom() -> None:
    """Un rôle inclus chez quelqu'un partage son espace de noms avec le sien.

    `group` et `desired_state` sont des noms que n'importe quel playbook emploie.
    Les préfixer est ce qui permet d'inclure deux rôles dans le même play sans
    qu'ils se marchent dessus.
    """
    for role in _roles():
        specs = yaml.safe_load((role / "meta" / "argument_specs.yml").read_text(encoding="utf-8"))[
            "argument_specs"
        ]["main"]
        attendu = f"scaleway_{role.name}_"
        fautives = [nom for nom in specs["options"] if not nom.startswith(attendu)]
        assert fautives == [], f"{role.name} : {fautives} ne commencent pas par `{attendu}`"


def test_aucun_role_ne_pose_un_fait_sans_le_prefixer() -> None:
    """Un fait non préfixé écrase celui de qui inclut le rôle.

    Le défaut n'existe pas tant que le code est un playbook : il apparaît le
    jour où quelqu'un l'inclut, chez lui, et se manifeste comme une variable
    qui change de valeur sans raison.
    """
    for role in _roles():
        # **Lu dans le YAML, pas cherché au texte.** La première version de cette
        # garde employait une expression rationnelle, et elle ne voyait que deux
        # des six faits que `power_schedule` pose : son motif s'arrêtait au
        # premier commentaire à l'intérieur du bloc. Elle passait en mesurant un
        # tiers du sujet, ce qui est la façon la plus discrète de ne rien garder.
        poses = sorted(
            nom
            for tache in _taches(role / "tasks" / "main.yml")
            for nom in (tache.get("ansible.builtin.set_fact") or {})
        )
        assert poses, f"{role.name} : aucun `set_fact` trouvé, la garde ne mesure plus rien"

        # Deux préfixes, et la distinction est une convention utile : avec le
        # tiret bas c'est interne, sans lui c'est ce que le rôle laisse pour son
        # appelant. `fleet_report` laisse son rapport, et un appelant qui doit
        # relire l'écran plutôt que la donnée n'a pas d'API.
        attendus = (f"_scaleway_{role.name}_", f"scaleway_{role.name}_")
        # **Un seul nom commun, et il est déclaré ici.** `scaleway_operation`
        # désigne la dernière opération du play, parce que le cas courant est
        # une chaîne qui veut le résultat de ce qu'elle vient de lancer. Deux
        # opérations dans le même play s'écrasent donc sur ce nom, et c'est
        # pour ça que chacune pose aussi le sien, qui dure. Ce sont deux noms
        # pour un même objet, pas deux calculs : ils ne peuvent pas diverger.
        partages = {"scaleway_operation"}
        fautifs = sorted(
            {nom for nom in poses if not nom.startswith(attendus) and nom not in partages}
        )
        assert fautifs == [], (
            f"{role.name} pose {fautifs} sans préfixe : ces faits écraseraient "
            f"ceux de qui inclut le rôle. Attendu : {' ou '.join(attendus)}..."
        )


def test_un_playbook_livre_appelle_son_role_et_ne_le_reimplemente_pas() -> None:
    """Deux implémentations d'une même opération divergent toujours.

    C'est la garde que la mise en rôle rend nécessaire : sans elle, rien
    n'empêche d'ajouter une tâche « juste pour cette fois » dans la façade, et
    le jour où les deux chemins diffèrent, la documentation décrit l'un et
    l'utilisateur joue l'autre.
    """
    for role in _roles():
        playbook = PLAYBOOKS / f"{role.name}.yml"
        assert playbook.is_file(), (
            f"{role.name} n'a pas de playbook : le rôle est l'API, le playbook "
            "est l'ergonomie, et l'ergonomie ne doit pas disparaître"
        )

        play = yaml.safe_load(playbook.read_text(encoding="utf-8"))[0]
        roles_appeles = [
            entree["role"] if isinstance(entree, dict) else entree
            for entree in play.get("roles", [])
        ]
        assert roles_appeles == [f"stephrobert.scaleway.{role.name}"], (
            f"{playbook.name} doit appeler exactement son rôle, et rien d'autre : {roles_appeles}"
        )

        for tache in play.get("tasks", []) or []:
            modules = [cle for cle in tache if cle.startswith("stephrobert.scaleway.")]
            assert modules == [], (
                f"{playbook.name} appelle {modules} en plus de son rôle : une "
                "opération implémentée deux fois finit par se contredire"
            )


def test_chaque_role_rend_la_structure_commune() -> None:
    """Une grammaire que deux opérations sur trois parlent est une convention.

    Et une convention se perd : la quatrième opération la suivra ou ne la
    suivra pas, personne ne le verra, et la chaîne qui lit le résultat
    redeviendra un analyseur de sortie standard (#206).

    Ce test tient les deux moitiés : la structure est posée, et elle est
    **construite par le filtre**. Une structure écrite à la main dans un rôle
    aurait la même forme et aucune des garanties : ni les comptes déduits des
    noms, ni le refus d'une raison manquante, ni `null` quand rien n'a pu être
    examiné.
    """
    for role in _roles():
        taches = _taches(role / "tasks" / "main.yml")
        poses = {
            nom: valeur
            for tache in taches
            for nom, valeur in (tache.get("ansible.builtin.set_fact") or {}).items()
        }

        attendus = {"scaleway_operation", f"scaleway_{role.name}_operation"}
        manquants = sorted(attendus - set(poses))
        assert manquants == [], (
            f"{role.name} ne rend pas {manquants} : une opération dont le "
            "résultat ne se lit que dans sa phrase oblige à analyser du texte"
        )

        construction = "\n".join(
            str(tache.get("vars", {}).get("resultat", ""))
            for tache in taches
            if "resultat" in (tache.get("vars") or {})
        )
        # La parenthèse fait partie du motif : sans elle, la garde acceptait
        # `operation_result_absent(`, qui contient le nom cherché. `/falsify`
        # l'a montré en restant vert sur une mutation qui aurait dû mordre.
        assert "stephrobert.scaleway.operation_result(" in construction, (
            f"{role.name} compose sa structure à la main : elle aurait la forme "
            "sans les garanties, ce qui est pire qu'une phrase parce que ça se "
            "lit comme un contrat"
        )


def test_un_role_qui_selectionne_emploie_la_grammaire_commune() -> None:
    """Quatre grammaires pour une question, c'est trois de trop (#208).

    Un rôle qui lirait `groups[...]` lui-même aurait sa propre façon de
    désigner, et l'utilisateur apprendrait la grammaire une fois par rôle. Pire,
    il perdrait les refus qui vont avec : le nom ambigu qu'on ne tranche pas, la
    clé inconnue qu'on ne prend pas pour une sélection vide.
    """
    for role in _roles():
        options = yaml.safe_load(
            (role / "meta" / "argument_specs.yml").read_text(encoding="utf-8")
        )["argument_specs"]["main"]["options"]
        if f"scaleway_{role.name}_selector" not in options:
            continue  # cette opération ne désigne pas des machines

        texte = (role / "tasks" / "main.yml").read_text(encoding="utf-8")
        assert "stephrobert.scaleway.select_hosts(" in texte, (
            f"{role.name} déclare un sélecteur et ne l'emploie pas : il résout "
            "sa cible autrement, donc avec d'autres refus que les autres"
        )
        assert "groups[" not in texte, (
            f"{role.name} lit `groups[...]` directement : c'est la grammaire "
            "parallèle que le sélecteur existe pour supprimer"
        )


def test_le_plan_ne_se_rend_quen_repetition() -> None:
    """« No action has been sent » sur un vrai passage serait un mensonge.

    Le plan dit qu'aucune action n'est partie. Rendu hors du mode check, il
    l'affirmerait après avoir agi, ce qui est pire qu'un silence : c'est une
    phrase que le lecteur croira (ADR-020).
    """
    for role in _roles():
        plan = next(
            (
                tache
                for tache in _taches(role / "tasks" / "main.yml")
                if tache.get("name") == "The plan, for a reviewer"
            ),
            None,
        )
        if plan is None:
            continue  # cette opération ne rend pas de plan

        assert plan.get("when") == "ansible_check_mode", (
            f"{role.name} rend son plan hors de la répétition : il dirait "
            "« aucune action envoyée » après en avoir envoyé"
        )
        # Le plan est un rendu de la structure, pas un second calcul : deux
        # sources du même fait finiraient par se contredire.
        assert plan["vars"]["resultat"] == "{{ scaleway_operation }}", (
            f"{role.name} compose son plan autrement que depuis le résultat"
        )
