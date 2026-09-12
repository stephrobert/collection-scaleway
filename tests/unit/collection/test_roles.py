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
        fautifs = sorted({nom for nom in poses if not nom.startswith(attendus)})
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
