"""Le quickstart est une porte d'entrée : ce qu'il promet doit tenir sans compte.

`SCW_API_URL` est honoré de bout en bout, et c'était présenté comme une
propriété du runtime. C'est aussi la seule porte gratuite du projet, et elle
n'était annoncée nulle part (#182).

Ces tests tiennent ce qu'une page d'accueil ne peut pas se permettre de rater :
une commande qui ne marche pas, une image qui bouge sous une étiquette, un
identifiant inventé à côté de la source qui les sert, et surtout la moitié
honnête, ce que l'émulateur ne prouve pas.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[3]
QUICKSTART = RACINE / "quickstart"
LISEZ_MOI = QUICKSTART / "README.md"
COMPOSE = QUICKSTART / "compose.yaml"
IMAGE = QUICKSTART / "Containerfile"
ENTREE = QUICKSTART / "entrypoint.sh"
PLAYBOOKS = RACINE / "ansible_collections" / "stephrobert" / "scaleway" / "playbooks"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


# --- les commandes de la page marchent-elles ------------------------------


def test_chaque_playbook_cite_par_la_page_existe() -> None:
    """Une commande d'accueil qui échoue coûte le visiteur, pas une minute."""
    texte = LISEZ_MOI.read_text(encoding="utf-8")
    livres = {chemin.stem for chemin in PLAYBOOKS.glob("*.yml")}

    cites = set(re.findall(r"stephrobert\.scaleway\.([a-z0-9_]+)", texte))
    assert cites, "la page ne cite plus aucun playbook de la collection"

    absents = sorted(cites - livres)
    assert absents == [], f"la page appelle des playbooks qui n'existent pas : {absents}"


def test_chaque_playbook_local_cite_par_la_page_existe() -> None:
    """Les playbooks du quickstart lui-même, ceux qui créent et qui montrent."""
    texte = LISEZ_MOI.read_text(encoding="utf-8")

    locaux = set(re.findall(r"ansible-playbook ([a-z0-9_]+\.yml)", texte))
    assert locaux, "la page ne cite plus aucun playbook local"

    absents = sorted(nom for nom in locaux if not (QUICKSTART / nom).is_file())
    assert absents == [], f"la page appelle des fichiers absents : {absents}"


# --- ce qui ne doit pas bouger sous les pieds du visiteur -----------------


def test_chaque_image_est_epinglee_par_condensat() -> None:
    """Une étiquette se réécrit, un condensat non.

    C'est la règle que `.plumber.yaml` applique aux workflows. Ce fichier-ci
    n'est lu par aucun scanner du dépôt : sans ce test, la règle s'arrêterait
    là où commence le fichier que les visiteurs exécutent.
    """
    services = _compose()["services"]
    epinglees = [(nom, service["image"]) for nom, service in services.items() if "image" in service]
    assert epinglees, "plus aucun service ne tire d'image : le test ne mesure plus rien"

    for nom, image in epinglees:
        assert "@sha256:" in image, f"{nom} tire `{image}` par étiquette"


def test_limage_de_lemulateur_est_batie_sur_un_condensat() -> None:
    """Même règle pour ce qu'on construit que pour ce qu'on tire."""
    contenu = IMAGE.read_text(encoding="utf-8")
    bases = re.findall(r"^FROM (\S+)", contenu, flags=re.MULTILINE)

    assert bases, "le Containerfile ne part plus d'aucune image"
    for base in bases:
        assert "@sha256:" in base, f"image de base épinglée par étiquette : {base}"


def test_le_binaire_de_lemulateur_est_verifie_avant_de_servir() -> None:
    """Un binaire téléchargé sans empreinte est un binaire qu'on espère.

    L'empreinte est écrite dans le fichier plutôt que téléchargée à côté :
    vérifier un binaire contre le `checksums.txt` tiré du même endroit ne
    prouve que leur cohérence mutuelle.
    """
    contenu = IMAGE.read_text(encoding="utf-8")

    empreintes = re.findall(r"^ARG FEINT_SHA256_(\w+)=([0-9a-f]{64})$", contenu, flags=re.M)
    assert len(empreintes) >= 2, (
        "une seule architecture épinglée : un poste Apple Silicon n'est pas un cas rare"
    )
    assert "sha256sum -c -" in contenu, "rien ne vérifie l'empreinte au moment de la construction"


# --- les identifiants ne s'inventent pas ----------------------------------


def test_aucun_identifiant_nest_ecrit_dans_le_quickstart() -> None:
    """C'est la règle du harnais d'intégration, et elle vaut ici aussi.

    Les écrire créerait une seconde source de ce que l'émulateur accepte, et
    les deux divergeraient le jour où feint changerait d'avis.
    """
    interdits = ("SCW_SECRET_KEY=", "SCW_ACCESS_KEY=", "SCW_DEFAULT_PROJECT_ID=")
    fautifs: list[str] = []
    for chemin in sorted(QUICKSTART.rglob("*")):
        if not chemin.is_file() or chemin.suffix == ".md":
            continue
        contenu = chemin.read_text(encoding="utf-8")
        fautifs += [
            f"{chemin.relative_to(RACINE)} : {motif}" for motif in interdits if motif in contenu
        ]

    assert fautifs == [], f"identifiants écrits au lieu d'être demandés à feint : {fautifs}"


def test_les_identifiants_viennent_de_lemulateur() -> None:
    """Et la source est nommée, pas devinée."""
    assert "feint env scaleway" in ENTREE.read_text(encoding="utf-8"), (
        "le point d'entrée n'interroge plus feint : d'où viennent les identifiants ?"
    )


# --- la moitié honnête ----------------------------------------------------

#: Ce que l'émulateur n'applique pas, tel que le dépôt l'a déjà mesuré, et la
#: phrase qui doit le porter sur la page d'accueil. Chacun a coûté un cycle
#: complet sur le cloud réel avant d'être compris.
LIMITES: tuple[tuple[str, str], ...] = (
    ("n'applique pas les ACL de VPC", "does not apply VPC ACLs"),
    ("ne pousse pas non plus de\nroute par défaut", "does not push a default route over DHCP"),
)


def test_la_page_dit_ce_que_lemulateur_ne_prouve_pas() -> None:
    """Un émulateur qui ment sans le dire enseigne un faux vert.

    Les deux moitiés sont tenues ensemble : la mesure vit dans
    `examples/README.md`, la page d'accueil doit la porter. Deux documents qui
    divergent valent moins qu'un seul.
    """
    mesure = (RACINE / "examples" / "README.md").read_text(encoding="utf-8")
    accueil = LISEZ_MOI.read_text(encoding="utf-8")

    for francais, anglais in LIMITES:
        assert francais in mesure, (
            f"« {francais} » a disparu de examples/README.md : ce test tenait "
            "la page d'accueil à une mesure qui n'y est plus"
        )
        assert anglais in accueil, (
            f"la page d'accueil ne dit pas « {anglais} », que le dépôt a pourtant mesuré"
        )


def test_la_page_ne_promet_pas_que_tout_est_servi() -> None:
    """Le compte de ce que l'émulateur sert dépend du jour : il se mesure.

    Écrire « tant de modules sur tant » figerait dans une page publiée un
    nombre qu'aucun contrôle ne recalcule, et `chiffres.py` le refuse pour
    cette raison. La page renvoie donc à la commande qui le mesure.
    """
    accueil = LISEZ_MOI.read_text(encoding="utf-8")

    assert "coverage:diff" in accueil, (
        "la page ne dit plus comment mesurer ce que l'émulateur ne sert pas"
    )


def test_lemulateur_nest_publie_que_sur_la_boucle_locale() -> None:
    """Il accepte n'importe quel identifiant : ce n'est pas un service.

    Le drapeau qui le sort de la boucle locale est nécessaire **dans** le
    conteneur, pour que les autres services le joignent. Ce que la composition
    publie vers l'hôte, lui, ne doit jamais quitter 127.0.0.1.
    """
    emulateur = _compose()["services"]["emulateur"]

    for publication in emulateur.get("ports", []):
        assert str(publication).startswith("127.0.0.1:"), (
            f"port publié hors de la boucle locale : {publication}"
        )


def test_la_flotte_survit_au_conteneur() -> None:
    """Un conteneur recréé ne doit pas coûter le parc.

    Mesuré : sans `--state`, l'émulateur garde sa flotte en mémoire, et le
    parcours a rendu « 5 créées » puis « 0 Instance » à la commande suivante.
    Mesuré aussi : avec l'état dans un volume, le conteneur change et la flotte
    reste. Ce test tient les deux moitiés ensemble, parce qu'un chemin d'état
    hors du volume rendrait la persistance décorative.
    """
    entree = ENTREE.read_text(encoding="utf-8")
    etat = re.search(r"--state (\S+)", entree)
    assert etat, "l'émulateur ne persiste plus son état : une flotte vivra en mémoire"

    monte = {
        publication.split(":")[1]
        for publication in _compose()["services"]["emulateur"]["volumes"]
        if ":" in str(publication)
    }
    dossier = etat.group(1).rsplit("/", 1)[0]
    assert dossier in monte, (
        f"l'état est écrit dans {dossier}, qui n'est pas un volume de la "
        f"composition ({sorted(monte)}) : il disparaîtrait avec le conteneur"
    )
