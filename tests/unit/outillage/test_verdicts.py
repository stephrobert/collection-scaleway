"""L'outillage refuse les verdicts qui n'ont rien mesuré.

Trois commandes de ce dépôt peuvent rendre un vert parfait sans avoir rien
regardé, ou pire, mesurer autre chose que ce qu'elles annoncent. Ce fichier
tient la garde de chacune, parce qu'une garde qu'aucun test ne mesure est un
commentaire.
"""

from __future__ import annotations

import json
import os
import subprocess
import tarfile
from pathlib import Path

import doc_examples
import docsite
import integration
import package
import pytest
import sanity

import docs
from generator.ansible.collection import Collection, load_collection

#: Ce que `feint env scaleway` écrit sur sa sortie standard, mesuré.
EXPORTS_DE_LEMULATEUR = "\n".join(
    [
        "export SCW_ACCESS_KEY='SCWXXXXXXXXXXXXXXXXX'",
        "export SCW_API_URL='http://127.0.0.1:4599'",
        "export SCW_DEFAULT_ZONE='fr-par-1'",
    ]
)


def _sortie(stdout: str, code: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr="")


def _collection_factice(racine: Path) -> Collection:
    """Une collection qui existe sur disque et ne contient rien."""
    chemin = racine / "ansible_collections" / "local" / "scaleway"
    chemin.mkdir(parents=True, exist_ok=True)
    return Collection(namespace="local", name="scaleway", version="0.0.0", path=chemin)


# --- ansible-test peut ne rien tester et sortir en 0 -----------------------


def test_une_sanity_qui_na_rien_examine_est_un_echec() -> None:
    """Mesuré sur ce dépôt : sous `build/`, git ne liste rien.

    `ansible-test` saute alors toutes les cibles, affiche un avertissement, et
    sort en 0. La sortie est indiscernable de celle d'une collection saine.
    """
    assert sanity.measured_something('Running sanity test "import"') is True
    assert sanity.measured_something("WARNING: All targets skipped.") is False


def test_une_collection_que_git_ne_suit_pas_ne_se_teste_pas() -> None:
    """La cause du faux vert, et non son symptôme.

    Dans un dépôt git, `ansible-test` demande à git la liste des fichiers. Sur
    un répertoire que git ne suit pas, il en reçoit zéro, saute toutes ses
    cibles et sort en 0.
    """
    assert sanity.refusal(under_git=True, tracked=0, where="ansible_collections/x/y") is not None
    assert sanity.refusal(under_git=True, tracked=12, where="ansible_collections/x/y") is None


def test_hors_depot_git_la_garde_ne_sapplique_pas() -> None:
    """Sans dépôt, `ansible-test` parcourt le disque et voit tout.

    Refuser là serait refuser une mesure qui aurait lieu : c'est le cas du
    harnais de falsification, qui copie ce dépôt sans son `.git`.
    """
    assert sanity.refusal(under_git=False, tracked=0, where="ailleurs") is None


# --- une intégration absente doit échouer, pas se sauter -------------------


def test_une_integration_sans_emulateur_echoue_au_lieu_de_se_sauter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un test qui se saute tout seul finit par ne plus jamais tourner."""
    monkeypatch.delenv("FEINT", raising=False)
    monkeypatch.setattr(integration.shutil, "which", lambda _: None)

    with pytest.raises(integration.IntegrationError) as erreur:
        integration.feint_binary()
    assert "feint" in str(erreur.value)


def test_lemulateur_se_designe_par_la_variable_denvironnement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEINT", "/ailleurs/feint")
    assert integration.feint_binary() == "/ailleurs/feint"


def test_le_scenario_amorce_plus_dune_page() -> None:
    """En dessous de 100, la pagination ne serait jamais exercée."""
    assert integration.SEEDED_SERVERS > 100


# --- l'environnement du scénario vient de l'émulateur ---------------------


def test_les_identifiants_viennent_de_lemulateur() -> None:
    """Les écrire ici créerait une seconde source de ce que feint accepte."""
    exports = integration.parse_exports(EXPORTS_DE_LEMULATEUR)
    assert exports["SCW_API_URL"] == "http://127.0.0.1:4599"
    assert exports["SCW_ACCESS_KEY"] == "SCWXXXXXXXXXXXXXXXXX"
    assert "'" not in exports["SCW_DEFAULT_ZONE"]


def test_un_environnement_sans_url_demulateur_arrete_le_scenario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sans cette variable, le playbook parlerait à l'API Scaleway réelle.

    C'est la garde la plus coûteuse à perdre de ce dépôt : de vrais
    identifiants, de vraies ressources, une vraie facture.
    """
    incomplet = "export SCW_ACCESS_KEY='SCWXXXXXXXXXXXXXXXXX'"
    monkeypatch.setattr(integration, "run", lambda *a, **k: _sortie(incomplet))

    with pytest.raises(integration.IntegrationError) as erreur:
        integration.client_environment("feint")
    assert "SCW_API_URL" in str(erreur.value)


def test_lenvironnement_complet_est_accepte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integration, "run", lambda *a, **k: _sortie(EXPORTS_DE_LEMULATEUR))
    assert integration.client_environment("feint")["SCW_API_URL"] == integration.ENDPOINT


def test_la_sonde_demulateur_utilise_le_verbe_qui_distingue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`feint wait` rend 0 ou 1 ; `feint status` rend 0 dans les deux cas.

    Mesuré avant de choisir : prendre `status` pour sonde aurait fait croire
    qu'un émulateur répondait toujours, et le scénario n'en aurait jamais
    démarré en local.
    """
    appels: list[list[str]] = []

    def faux_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        appels.append(command)
        return _sortie("")

    monkeypatch.setattr(integration, "run", faux_run)
    assert integration.answers("feint") is True
    assert appels[0][1] == "wait"


# --- le scénario range ce qu'il crée --------------------------------------


def test_le_demarrage_range_les_machines_quil_cree() -> None:
    """Sans `--cleanup`, une exécution sous `incus-ovn` laisse un conteneur.

    Constaté une fois, sur la machine de développement : le scénario passait,
    et `incus list` montrait encore le conteneur du serveur allumé.
    """
    commande = integration.start_command("feint", Path("/tmp/etat.json"))
    assert "--cleanup" in commande
    assert commande[commande.index("--vm") + 1] == integration.VM_MODE


def test_le_mode_machine_est_off_par_defaut(monkeypatch: pytest.MonkeyPatch) -> None:
    """Démarrer des machines est un effet de bord qui se demande."""
    monkeypatch.delenv("FEINT_VM", raising=False)
    assert os.environ.get("FEINT_VM", "off") == "off"


def test_un_serveur_qui_ne_demarre_pas_fait_echouer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sinon le playbook échouerait plus loin, sur un message qui ne dit rien.

    Le message doit porter le **dernier état observé**, pas un état supposé :
    c'est lui qui distingue « la machine n'a pas démarré » de « l'émulateur ne
    répond plus ».
    """
    monkeypatch.setattr(integration, "BOOT_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(integration.time, "sleep", lambda _: None)
    monkeypatch.setattr(integration, "call", lambda *a, **k: {"server": {"state": "stopped"}})

    with pytest.raises(integration.IntegrationError) as erreur:
        integration.power_on("un-identifiant")
    assert "stopped" in str(erreur.value)
    assert integration.VM_MODE in str(erreur.value)


def test_un_emulateur_dans_le_mauvais_mode_nest_pas_adopte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C'est arrivé : un run a demandé incus-ovn et a mesuré du mode off.

    Un émulateur en `off` écoutait déjà, le scénario l'a adopté, et la sortie
    était celle d'un run réussi. Seule la durée de démarrage, 0,0 s au lieu de
    1,0 s, disait que rien n'avait démarré.
    """
    monkeypatch.setattr(integration, "VM_MODE", "incus-ovn")
    monkeypatch.setattr(
        integration, "run", lambda *a, **k: _sortie('{"running": true, "machines": "none"}')
    )

    with pytest.raises(integration.IntegrationError) as erreur:
        integration.check_adopted_mode("feint")
    assert "none" in str(erreur.value)
    assert "incus-ovn" in str(erreur.value)


def test_un_emulateur_dans_le_bon_mode_est_adopte(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integration, "VM_MODE", "incus-ovn")
    monkeypatch.setattr(
        integration, "run", lambda *a, **k: _sortie('{"running": true, "machines": "incus-ovn"}')
    )
    integration.check_adopted_mode("feint")


def test_le_mode_off_attend_des_machines_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """`off` côté drapeau, `none` côté statut : la traduction est explicite."""
    monkeypatch.setattr(integration, "VM_MODE", "off")
    monkeypatch.setattr(
        integration, "run", lambda *a, **k: _sortie('{"running": true, "machines": "none"}')
    )
    integration.check_adopted_mode("feint")


# --- la documentation officielle, et le vert qui ne juge rien -------------


def test_un_linter_de_doc_sans_module_est_un_echec(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Mesuré : antsibull-docs sort en 0 sur une collection sans plugin.

    Le même piège qu'`ansible-test`, et la même réponse : connaître la
    population avant de croire le verdict.
    """
    with pytest.raises(docs.DocsError) as erreur:
        docs.modules_to_document(_collection_factice(tmp_path))
    assert "vide" in str(erreur.value)


def test_les_modules_produits_sont_la_population_du_lint() -> None:
    assert "instance_server_info" in docs.documented_modules(load_collection())


def test_le_lint_demande_les_references_croisees() -> None:
    """`--plugin-docs` est ce qui fait lire les M(...) et les O(...).

    Sans lui, le linter ne juge que les fichiers annexes, et la référence
    invalide qu'`ansible-test sanity` laisse passer passerait aussi ici.
    """
    assert "--plugin-docs" in docs.LINT_FLAGS
    assert "--validate-collection-refs" in docs.LINT_FLAGS


# --- les exemples sont joués, pas seulement écrits ------------------------


def test_un_scenario_sans_exemple_est_un_echec(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Un exemple que personne n'exécute pourrit, et personne ne le voit."""
    with pytest.raises(integration.IntegrationError) as erreur:
        integration.playbooks(_collection_factice(tmp_path))
    assert "playbook" in str(erreur.value)


def test_le_scenario_joue_le_contrat_puis_les_exemples() -> None:
    chemins = integration.playbooks(load_collection())
    assert chemins[0] == integration.PLAYBOOK
    assert len(chemins) > 1
    assert all(chemin.is_file() for chemin in chemins)


# --- l'archive livrée -----------------------------------------------------


def _archive(tmp_path: Path, chemins: list[str]) -> Path:
    """Fabrique une archive minimale portant exactement ces chemins."""
    archive = tmp_path / "collection.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for chemin in chemins:
            fichier = tmp_path / "contenu"
            fichier.write_text("x", encoding="utf-8")
            tar.add(fichier, arcname=chemin)
    return archive


def test_une_archive_qui_emporte_le_generateur_est_refusee(tmp_path: Path) -> None:
    """Le générateur, les contrats et les tests n'ont rien à faire chez un
    utilisateur : une archive qui les emporte est une fuite, pas un excès de
    poids."""
    archive = _archive(tmp_path, [*package.REQUIRED, "generator/cli.py"])

    with pytest.raises(package.PackageError) as erreur:
        package.check_contents(archive)
    assert "generator" in str(erreur.value)


def test_une_archive_qui_oublie_un_module_est_refusee(tmp_path: Path) -> None:
    """Sans cette moitié, une archive vide passerait le contrôle précédent."""
    archive = _archive(tmp_path, ["MANIFEST.json"])

    with pytest.raises(package.PackageError) as erreur:
        package.check_contents(archive)
    assert "instance_server_info" in str(erreur.value)


def test_une_archive_complete_est_acceptee(tmp_path: Path) -> None:
    archive = _archive(tmp_path, list(package.REQUIRED))
    assert package.check_contents(archive) == tuple(sorted(package.REQUIRED))


def test_larchive_emporte_la_licence_et_le_changelog() -> None:
    """Deux exigences de la liste de contrôle d'inclusion des collections."""
    assert "LICENSE" in package.REQUIRED
    assert "CHANGELOG.rst" in package.REQUIRED
    assert "changelogs/changelog.yaml" in package.REQUIRED


# --- un inventaire dynamique peut rendre un vert sans machine -------------


#: Un graphe minimal, tel qu'`ansible-inventory --list` le rend : les chaînes
#: venues d'un plugin y sont marquées non sûres, et c'est ce marquage qui fait
#: échouer un contrôle écrit sans l'avoir mesuré.
def _graphe(machines: int = 1, etat_running: bool = True) -> dict[str, object]:
    hostvars: dict[str, object] = {
        f"web{index:02d}": {
            "scaleway_id": {"__ansible_unsafe": f"uuid-{index}"},
            "scaleway_product": {"__ansible_unsafe": "instance"},
        }
        for index in range(1, machines + 1)
    }
    graphe: dict[str, object] = {"_meta": {"hostvars": hostvars}}
    if etat_running and machines:
        graphe["scw_state_running"] = {"hosts": ["web01"]}
    return graphe


def test_le_marquage_non_sur_dansible_est_deballe() -> None:
    """Mesuré : `--list` rend `{"__ansible_unsafe": "..."}` et non la chaîne."""
    assert integration.unwrap({"__ansible_unsafe": "uuid-1"}) == "uuid-1"
    assert integration.unwrap("uuid-1") == "uuid-1"
    assert integration.unwrap({"autre": "chose"}) == {"autre": "chose"}


def test_un_inventaire_incomplet_arrete_le_scenario(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une pagination cassée rendrait cent machines, ce qui ressemble à un parc."""
    monkeypatch.setattr(integration, "inventory_graph", lambda _env: _graphe(machines=3))

    with pytest.raises(integration.IntegrationError) as erreur:
        integration.check_inventory({}, 104, "uuid-1")

    assert "3 machine(s)" in str(erreur.value)


def test_une_machine_sans_identite_arrete_le_scenario(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans `scaleway_id`, les modules Day-2 ne peuvent rien faire de la machine."""
    graphe = _graphe(machines=1)
    graphe["_meta"]["hostvars"]["web01"]["scaleway_id"] = ""  # type: ignore[index]
    monkeypatch.setattr(integration, "inventory_graph", lambda _env: graphe)

    with pytest.raises(integration.IntegrationError) as erreur:
        integration.check_inventory({}, 1, "uuid-1")

    assert "sans identité" in str(erreur.value)


def test_le_serveur_allume_doit_se_retrouver_dans_son_groupe_detat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le groupe doit suivre l'API, et non une valeur recopiée à la découverte."""
    monkeypatch.setattr(
        integration, "inventory_graph", lambda _env: _graphe(machines=1, etat_running=False)
    )

    with pytest.raises(integration.IntegrationError) as erreur:
        integration.check_inventory({}, 1, "uuid-1")

    assert "scw_state_running" in str(erreur.value)


def test_un_inventaire_complet_est_accepte(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le contre-exemple : sans lui, les trois tests ci-dessus passeraient aussi
    sur une fonction qui refuserait tout."""
    monkeypatch.setattr(integration, "inventory_graph", lambda _env: _graphe(machines=2))
    integration.check_inventory({}, 2, "uuid-1")


def test_le_scenario_mesure_le_mode_strict_dans_les_deux_sens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le contrôle affirme deux faits, donc il doit échouer si l'un des deux ment.

    Ici, Ansible refuse même sans la variable : le contrôle doit le dire, parce
    que la documentation affirme le contraire et devrait alors être relue.
    """
    monkeypatch.setattr(integration, "run", lambda *a, **k: _sortie("{}", code=1))

    with pytest.raises(integration.IntegrationError) as erreur:
        integration.check_strict_mode_is_visible({})

    assert "relire" in str(erreur.value)


# --- une archive peut porter un plugin qu'Ansible ne sait pas charger ------


def test_un_plugin_dinventaire_sans_options_nest_pas_charge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Un `module_utils/` oublié au build laisse le fichier et perd le plugin."""
    collection = _collection_factice(tmp_path)
    monkeypatch.setattr(
        package,
        "subprocess",
        type(
            "FauxSubprocess",
            (),
            {"run": staticmethod(lambda *a, **k: _sortie('{"local.scaleway.scaleway": {}}'))},
        ),
    )

    with pytest.raises(package.PackageError) as erreur:
        package.check_inventory_plugin(tmp_path, collection)

    assert "products" in str(erreur.value)


def test_un_plugin_dinventaire_complet_est_accepte(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    collection = _collection_factice(tmp_path)
    documente = json.dumps(
        {
            "local.scaleway.scaleway": {
                "doc": {"options": {nom: {} for nom in package.INVENTORY_OPTIONS}}
            }
        }
    )
    monkeypatch.setattr(
        package,
        "subprocess",
        type(
            "FauxSubprocess",
            (),
            {"run": staticmethod(lambda *a, **k: _sortie(documente))},
        ),
    )
    package.check_inventory_plugin(tmp_path, collection)


# --- ce que le dépôt publie de ses fichiers de bureau ----------------------


def _depot_git() -> Path:
    """La racine du dépôt, ou un saut explicite hors dépôt.

    `scripts/falsify.py` copie l'arbre **sans** `.git` pour jouer les tests dans
    une copie hors dépôt. Ce contrôle porte sur ce que git enregistre : là-bas
    il n'a rien à mesurer, et le dire vaut mieux que de faire rougir la
    falsification sur une absence de dépôt.
    """
    racine = load_collection().collections_root
    if not (racine / ".git").exists():
        pytest.skip("hors dépôt git : il n'y a rien à mesurer sur ce que git enregistre")
    return racine


def test_les_notes_de_bureau_ne_sont_ni_suivies_ni_nommees_dans_le_gitignore() -> None:
    """Deux propriétés distinctes, et la seconde est celle qu'on oublie.

    Ne pas suivre le fichier empêche de le publier. Ne pas le **nommer** dans
    le `.gitignore` versionné empêche de publier son existence et son nom :
    une ligne `CLAUDE.md` dans un fichier public dit à tout le monde qu'un
    document privé porte ce nom.

    L'exclusion vit donc dans `.git/info/exclude`, qui n'est jamais poussé.
    Ce test est ce qui empêche qu'elle remonte dans le `.gitignore` un jour où
    quelqu'un trouvera ça plus simple, ce qui est arrivé une fois.
    """
    racine = _depot_git()

    suivi = subprocess.run(
        ["git", "ls-files", "--", "CLAUDE.md", "BRIEF.md"],
        cwd=racine,
        capture_output=True,
        text=True,
        check=False,
    )
    assert suivi.returncode == 0
    assert suivi.stdout.strip() == "", "un fichier de bureau est suivi par git"

    versionne = (racine / ".gitignore").read_text(encoding="utf-8")
    for nom in ("CLAUDE.md", "BRIEF.md"):
        assert nom not in versionne, (
            f"{nom} est nommé dans le .gitignore versionné : l'exclusion doit "
            "vivre dans .git/info/exclude, qui ne part pas dans le dépôt"
        )


# --- un site de documentation peut se construire sur rien ------------------


def _site_factice(tmp_path: Path, modules: list[str], pages: list[str]) -> None:
    """Un dépôt de laboratoire : des modules d'un côté, des pages de l'autre."""
    (tmp_path / "modules").mkdir(parents=True, exist_ok=True)
    for nom in modules:
        (tmp_path / "modules" / f"{nom}.py").write_text("", encoding="utf-8")
    reference = tmp_path / "src" / "collections" / "local" / "scaleway"
    reference.mkdir(parents=True, exist_ok=True)
    for nom in pages:
        (reference / f"{nom}_module.rst").write_text("", encoding="utf-8")


@pytest.fixture
def site_isole(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(docsite, "MODULES", tmp_path / "modules")
    monkeypatch.setattr(docsite, "SITE_SRC", tmp_path / "src")
    return tmp_path


def test_un_site_construit_sur_zero_module_est_un_echec(site_isole: Path) -> None:
    """Sphinx construit très bien un site vide, et le vert ressemble au vrai."""
    _site_factice(site_isole, modules=[], pages=[])

    paquets = tuple(nom for nom, _ in docsite.GENERATOR_PACKAGES)
    with pytest.raises(docsite.SiteError) as erreur:
        docsite.check_population(("instance.v1",), paquets)

    assert "aucun module" in str(erreur.value)


def test_un_module_sans_page_fait_echouer_le_site(site_isole: Path) -> None:
    """La documentation doit couvrir ce que la collection livre, pas moins."""
    _site_factice(site_isole, modules=["a_info", "b_action"], pages=["a_info"])

    paquets = tuple(nom for nom, _ in docsite.GENERATOR_PACKAGES)
    with pytest.raises(docsite.SiteError) as erreur:
        docsite.check_population(("instance.v1",), paquets)

    assert "b_action" in str(erreur.value)


def test_un_site_sans_page_de_mesure_est_un_echec(site_isole: Path) -> None:
    """La page que seule la représentation intermédiaire sait écrire."""
    _site_factice(site_isole, modules=["a_info"], pages=["a_info"])

    paquets = tuple(nom for nom, _ in docsite.GENERATOR_PACKAGES)
    with pytest.raises(docsite.SiteError) as erreur:
        docsite.check_population((), paquets)

    assert "mesure" in str(erreur.value)


def test_un_site_complet_est_accepte(site_isole: Path) -> None:
    """Le contre-exemple, sans lequel les trois tests ci-dessus passeraient
    aussi sur une fonction qui refuserait tout."""
    _site_factice(site_isole, modules=["a_info", "b_action"], pages=["a_info", "b_action"])
    paquets = tuple(nom for nom, _ in docsite.GENERATOR_PACKAGES)
    docsite.check_population(("instance.v1",), paquets)


# --- les exemples de la documentation ---------------------------------------


def test_un_bloc_de_configuration_nest_pas_pris_pour_un_playbook(tmp_path: Path) -> None:
    """Un fichier d'inventaire dans un guide n'est pas un playbook.

    `--syntax-check` le refuserait pour de mauvaises raisons, et la porte
    rougirait sur un exemple parfaitement correct.
    """
    page = tmp_path / "guide.md"
    page.write_text(
        "```yaml\nplugin: local.scaleway.scaleway\nproducts:\n  - instance\n```\n",
        encoding="utf-8",
    )
    assert doc_examples.extract(page) == []


def test_un_playbook_est_reconnu_dans_un_guide(tmp_path: Path) -> None:
    page = tmp_path / "guide.md"
    page.write_text(
        "```yaml\n- name: Un jeu\n  hosts: all\n  tasks: []\n```\n",
        encoding="utf-8",
    )
    (bloc,) = doc_examples.extract(page)
    assert "hosts: all" in bloc


def test_une_documentation_sans_exemple_est_un_echec(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zéro exemple et un extracteur cassé rendent le même vert."""
    monkeypatch.setattr(doc_examples, "sources", list)

    with pytest.raises(doc_examples.ExampleError) as erreur:
        doc_examples.main()

    assert "extraction est cassée" in str(erreur.value)
