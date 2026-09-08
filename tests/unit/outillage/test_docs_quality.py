"""Ce que la porte documentaire mesure, et ce qu'elle refuse de laisser publier.

`ansible-test sanity` dit qu'un bloc `DOCUMENTATION` est bien formé. Il ne dit
rien de ce qu'il apprend à quelqu'un : un module dont toutes les options
portent « Not documented by the Scaleway API contract. » et dont l'exemple montre
`zone: <zone>` passe la sanity sans une remarque, et se publie tel quel.

Ces tests portent sur des modules écrits ici, pas sur ceux du dépôt : une porte
qui ne mesurerait plus rien le jour où la collection change n'est pas une porte.
"""

from __future__ import annotations

from pathlib import Path

import docs_quality
import pytest
import yaml

from generator.ansible.attributes import pour
from generator.ir.enums import OperationKind

EN_TETE = '#!/usr/bin/python\n"""Module de test."""\n\n'


def _module(dossier: Path, nom: str, documentation: str, exemples: str, retour: str) -> Path:
    chemin = dossier / f"{nom}.py"
    chemin.write_text(
        f'{EN_TETE}DOCUMENTATION = r"""{documentation}"""\n\n'
        f'EXAMPLES = r"""{exemples}"""\n\n'
        f'RETURN = r"""{retour}"""\n',
        encoding="utf-8",
    )
    return chemin


BON_EXEMPLE = """
- name: Read a Scaleway Instance
  stephrobert.scaleway.instance_server_info:
    zone: fr-par-1
    server_id: 11111111-2222-3333-4444-555555555555
  register: result
"""

BON_RETOUR = """
server:
  description: The Instance.
  returned: success
  type: dict
"""


def test_un_repli_de_description_est_bloquant(tmp_path: Path) -> None:
    """La phrase de repli est publiée telle quelle, et Galaxy ne se reprend pas."""
    chemin = _module(
        tmp_path,
        "demo_thing_info",
        f"""
module: demo_thing_info
short_description: Read a thing
description:
  - Read a thing.
options:
  server_id:
    description:
      - {docs_quality.REPLI}
    type: str
""",
        BON_EXEMPLE,
        BON_RETOUR,
    )
    _, defauts = docs_quality.examiner(chemin, {})
    genres = {d.genre for d in defauts if d.bloquant}
    assert "option-sans-description" in genres


def test_un_exemple_a_trou_est_bloquant(tmp_path: Path) -> None:
    """`zone: <zone>` n'est pas du YAML qu'on copie, c'est un formulaire vide."""
    chemin = _module(
        tmp_path,
        "demo_thing",
        """
module: demo_thing
short_description: Update a thing
description:
  - Update a thing.
options:
  zone:
    description:
      - The zone you want to target.
    type: str
""",
        """
- name: Update a thing
  demo.demo.demo_thing:
    zone: <zone>
  register: result
""",
        BON_RETOUR,
    )
    _, defauts = docs_quality.examiner(chemin, {})
    assert any(d.genre == "exemple-non-copiable" and d.bloquant for d in defauts)


def test_un_module_qui_ne_dit_pas_ce_quil_fait_est_bloquant(tmp_path: Path) -> None:
    chemin = _module(
        tmp_path,
        "demo_thing_info",
        """
module: demo_thing_info
short_description: Read a thing
options: {}
""",
        BON_EXEMPLE,
        BON_RETOUR,
    )
    _, defauts = docs_quality.examiner(chemin, {})
    assert any(d.genre == "description-absente" and d.bloquant for d in defauts)


def test_une_action_que_le_module_refuse_ne_doit_pas_etre_documentee(tmp_path: Path) -> None:
    """L'`argument_spec` fait foi : documenter davantage promet ce qu'il refuse.

    Le cas mesuré est `instance_server_action`, qui exposait quatre actions et
    en documentait sept, `terminate` compris, sur un module qui le refuse.
    """
    chemin = _module(
        tmp_path,
        "demo_thing_action",
        """
module: demo_thing_action
short_description: Act on a thing
description:
  - Perform an action.
  - '* `poweron`: Start the thing.'
  - '* `terminate`: Delete the thing.'
options:
  action:
    description:
      - The action to perform.
    type: str
    choices: [poweron]
""",
        BON_EXEMPLE,
        BON_RETOUR,
    )
    _, defauts = docs_quality.examiner(chemin, {"demo_thing_action": {"poweron"}})
    fautes = [d for d in defauts if d.genre == "action-exclue-documentee"]
    assert fautes and fautes[0].bloquant
    assert "terminate" in fautes[0].detail


def test_le_vocabulaire_du_contrat_est_bloquant(tmp_path: Path) -> None:
    """`Scaleway Lb` est le slug d'index, pas le nom du produit.

    Scaleway écrit « Load Balancer » dans sa console, sa facturation et sa
    documentation. Un lecteur qui cherche ses modules de Load Balancer ne tape
    pas « Lb ».
    """
    chemin = _module(
        tmp_path,
        "demo_thing",
        """
module: demo_thing
short_description: Manage a Scaleway Lb thing
description:
  - Update a thing.
options: {}
""",
        BON_EXEMPLE,
        BON_RETOUR,
    )
    _, defauts = docs_quality.examiner(chemin, {})
    assert any(d.genre == "vocabulaire-du-contrat" and d.bloquant for d in defauts)


def test_une_fuite_de_la_couche_http_est_bloquante(tmp_path: Path) -> None:
    """« You must set all parameters » est vrai de l'API et faux du module.

    Le module lit la ressource avant d'écrire et remplit lui-même les champs
    qu'on ne lui donne pas. Recopier la phrase du contrat publie une
    contradiction avec la phrase suivante, que le générateur écrit.
    """
    chemin = _module(
        tmp_path,
        "demo_thing",
        """
module: demo_thing
short_description: Manage a thing
description:
  - Update a thing. You must set all parameters.
options: {}
""",
        BON_EXEMPLE,
        BON_RETOUR,
    )
    _, defauts = docs_quality.examiner(chemin, {})
    assert any(d.genre == "fuite-de-la-couche-http" and d.bloquant for d in defauts)


def test_un_exemple_nomme_par_le_contrat_est_bloquant(tmp_path: Path) -> None:
    """`Run GetDashboard` nomme l'appel HTTP, pas ce que la tâche fait.

    Le nom reste dans la sortie d'Ansible de qui copie la tâche.
    """
    chemin = _module(
        tmp_path,
        "demo_thing_info",
        """
module: demo_thing_info
short_description: Read a thing
description:
  - Read a thing.
options: {}
""",
        """
- name: Run GetDashboard
  demo.demo.demo_thing_info:
    zone: fr-par-1
  register: result
""",
        BON_RETOUR,
    )
    _, defauts = docs_quality.examiner(chemin, {})
    assert any(d.genre == "exemple-nomme-par-le-contrat" and d.bloquant for d in defauts)


def test_un_module_sans_defaut_ne_bloque_rien(tmp_path: Path) -> None:
    """Une porte qui refuse tout ne mesure plus rien : elle mesure sa panne."""
    chemin = _module(
        tmp_path,
        "demo_thing_info",
        """
module: demo_thing_info
short_description: Read a thing
description:
  - Read a thing by its ID.
options:
  server_id:
    description:
      - UUID of the thing.
    type: str
""",
        BON_EXEMPLE,
        BON_RETOUR,
    )
    _, defauts = docs_quality.examiner(chemin, {})
    assert [d for d in defauts if d.bloquant] == []


def test_une_mesure_sur_zero_module_est_une_erreur(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Zéro défaut sur zéro module est un vert qui ne dit rien.

    C'est le défaut qui avait rendu un `ansible-test sanity` vert sur zéro
    fichier examiné : le compte rendu ne distinguait pas « rien à redire » de
    « rien mesuré ».
    """
    (tmp_path / "plugins" / "modules").mkdir(parents=True)

    class _Collection:
        path = tmp_path

    monkeypatch.setattr(docs_quality, "load_collection", lambda: _Collection())
    with pytest.raises(docs_quality.QualiteError, match="aucun module"):
        docs_quality.mesurer()


def test_la_porte_mesure_bien_la_collection_livree() -> None:
    """La collection publiée ne porte aucun défaut bloquant.

    Ce test regarde le dépôt et pas une fixture : c'est le seul du fichier qui
    le fasse, et c'est voulu. Les autres prouvent que la porte sait refuser ;
    celui-ci dit ce qu'elle mesure aujourd'hui sur ce qui part chez Galaxy.
    """
    mesure, defauts = docs_quality.mesurer()
    bloquants = [f"{d.module} : {d.genre} ({d.detail})" for d in defauts if d.bloquant]
    assert bloquants == [], "\n".join(bloquants)
    assert mesure.modules > 0


def test_le_plugin_dinventaire_entre_dans_la_mesure() -> None:
    """C'est la page qu'un utilisateur lit en premier, et elle était hors mesure.

    Le plugin d'inventaire a sa page sur Galaxy et ses options ; la porte ne
    regardait que `plugins/modules`. Surveiller les pages qu'on lit après, mais
    pas celle qu'on lit d'abord, laissait le trou au pire endroit.
    """
    mesure, _ = docs_quality.mesurer()
    assert mesure.modules == 51, (
        f"{mesure.modules} pages examinées, 50 modules et 1 plugin attendus"
    )


def test_les_exemples_dun_plugin_sont_des_fichiers_entiers(tmp_path: Path) -> None:
    """On copie un fichier d'inventaire, pas une tâche.

    Ils sont donc séparés par `---`, et `safe_load` ne rend que le premier :
    mesurer avec lui laissait tous les suivants hors de la mesure, et ils
    pouvaient repasser en commentaires sans que rien ne le dise.
    """
    chemin = tmp_path / "demo.py"
    chemin.write_text(
        EN_TETE + 'DOCUMENTATION = r"""\nname: demo\nshort_description: Read\n'
        'description:\n  - Read.\noptions: {}\n"""\n\n'
        'EXAMPLES = r"""\nplugin: demo.demo.demo\n\n---\nplugin: demo.demo.demo\n'
        'regions:\n  - fr-par\n"""\n\nRETURN = r"""\n"""\n',
        encoding="utf-8",
    )
    mesure, _ = docs_quality.examiner(chemin, {})
    assert mesure.exemples == 2, "le second document d'exemple n'est pas mesuré"


def test_un_champ_de_retour_sans_description_est_bloquant(tmp_path: Path) -> None:
    """La porte ne regardait que les clés de premier niveau.

    Le générateur venait de gagner le droit de publier les champs des
    ressources, et cent phrases de repli sont parties sur Galaxy sans que rien
    ne les compte : la surface publiée s'était élargie, la mesure non.
    """
    chemin = _module(
        tmp_path,
        "demo_thing_info",
        """
module: demo_thing_info
short_description: Read a thing
description:
  - Read a thing.
options: {}
""",
        BON_EXEMPLE,
        f"""
thing:
  description: The thing.
  returned: success
  type: dict
  contains:
    id:
      description:
        - Unique ID of the thing.
      returned: when the API returns it
      type: str
    couleur:
      description:
        - {docs_quality.REPLI}
      returned: when the API returns it
      type: str
""",
    )
    mesure, defauts = docs_quality.examiner(chemin, {})
    assert mesure.champs == 2 and mesure.champs_decrits == 1
    fautes = [d for d in defauts if d.genre == "champ-de-retour-sans-description"]
    assert fautes and fautes[0].bloquant
    assert "couleur" in fautes[0].detail


def test_la_porte_documentaire_ne_reproche_aucun_attribut() -> None:
    """C'est `docs_quality` qui juge la page, et ce test dit où en est le dépôt.

    Le contrôle vit là parce qu'un défaut d'`attributes` est un défaut
    documentaire, et parce que `release:check` le lance avant de publier. Le
    refaire ici en donnerait deux implémentations, dont une seule serait
    corrigée le jour où la table changera.
    """
    _, defauts = docs_quality.mesurer()
    miens = [
        f"{defaut.module} : {defaut.detail}"
        for defaut in defauts
        if defaut.genre == "attributs-non-conformes-a-la-classe"
    ]
    assert miens == [], "\n".join(miens)


def test_la_porte_documentaire_refuse_une_page_qui_ment_sur_son_diff(tmp_path: Path) -> None:
    """Le contre-exemple, sans lequel le test précédent ne prouve que l'état du jour.

    Un module de gestion qui annoncerait `diff_mode: none` passerait
    `ansible-test sanity` sans un mot : la section est bien formée, et elle est
    fausse.
    """
    modules = tmp_path / "modules"
    modules.mkdir()
    menteur = dict(pour(OperationKind.MANAGE))
    menteur["diff_mode"] = {**menteur["diff_mode"], "support": "none"}
    (modules / "widget_chose.py").write_text(
        "DOCUMENTATION = r'''\n"
        + yaml.safe_dump(
            {
                "module": "widget_chose",
                "description": ["Manage a widget."],
                "attributes": menteur,
            },
            sort_keys=False,
        )
        + "'''\nRETURN = r'''{}'''\nEXAMPLES = r'''[]'''\n",
        encoding="utf-8",
    )

    _, defauts = docs_quality.examiner(modules / "widget_chose.py", {})
    categories = [defaut.genre for defaut in defauts]
    assert "attributs-non-conformes-a-la-classe" in categories
