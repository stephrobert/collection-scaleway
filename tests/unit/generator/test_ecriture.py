"""Un artefact versionné n'est jamais laissé à moitié écrit.

`Path.write_text` tronque puis écrit, et entre les deux le fichier est vide.
Mesuré le 14 septembre 2026 en guettant la taille d'un module pendant sa
régénération : cinquante-six lectures hors taille finale, toutes tronquées, aux
tailles `0`, `4096`, `8192` et `12288` pour un fichier de 12809 octets.

`mise run check` lance la suite de tests dans le même graphe que `generate` et
`golden:update`, qui réécrivent la collection entière et les golden. La fenêtre
n'est pas théorique : elle s'ouvre soixante-neuf fois par passage.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

import pytest

from generator.ecriture import PREFIXE, SUFFIXE, ecrire


def test_le_contenu_arrive_en_entier(tmp_path: Path) -> None:
    cible = tmp_path / "artefact.py"

    ecrire(cible, "le contenu attendu\n")

    assert cible.read_text(encoding="utf-8") == "le contenu attendu\n"


def test_un_lecteur_concurrent_ne_voit_jamais_un_fichier_tronque(tmp_path: Path) -> None:
    """**Le défaut mesuré, et la garde qui le ferme.**

    Le guetteur lit la taille sans relâche pendant l'écriture. Avec
    `write_text`, il voyait le fichier à zéro octet ; ici il ne doit voir que
    l'ancienne taille ou la nouvelle, jamais un entre-deux.
    """
    cible = tmp_path / "artefact.py"
    ancien, neuf = "a" * 4096, "b" * 40960
    cible.write_text(ancien, encoding="utf-8")

    vues: list[int] = []
    arret = threading.Event()

    def guetter() -> None:
        while not arret.is_set():
            try:
                vues.append(cible.stat().st_size)
            except FileNotFoundError:
                # Un fichier qui disparaît est aussi un entre-deux : le
                # renommage ne doit jamais laisser la cible absente.
                vues.append(-1)

    guetteur = threading.Thread(target=guetter, daemon=True)
    guetteur.start()
    for _ in range(20):
        ecrire(cible, neuf)
        ecrire(cible, ancien)
    arret.set()
    guetteur.join(timeout=2)

    assert vues, "le guetteur n'a rien lu, le contrôle ne mesure rien"
    assert set(vues) <= {len(ancien), len(neuf)}, (
        f"tailles intermédiaires vues : {sorted(set(vues) - {len(ancien), len(neuf)})}"
    )


def test_une_ecriture_interrompue_ne_laisse_pas_la_cible_a_moitie(tmp_path: Path) -> None:
    """Un `Ctrl-C` au mauvais moment laissait un artefact tronqué sur le disque."""
    cible = tmp_path / "artefact.py"
    cible.write_text("ce qui était là\n", encoding="utf-8")

    class Interruption(BaseException):
        """Ni `Exception` ni `KeyboardInterrupt` : ce qu'aucun `except` n'attrape.

        C'est la famille de `KeyboardInterrupt`, et c'est pourquoi le `except`
        de `ecrire` porte sur `BaseException` : un `Ctrl-C` pendant une
        régénération est exactement le cas qu'on couvre.
        """

    def exploser(*_args: object, **_kwargs: object) -> None:
        raise Interruption()

    # Interrompu **après** l'écriture des octets et **avant** le renommage :
    # c'est la seule fenêtre où la cible pourrait rester à moitié écrite.
    reel = os.fsync
    os.fsync = exploser  # type: ignore[assignment]
    try:
        with pytest.raises(Interruption):
            ecrire(cible, "ce qui n'arrivera pas")
    finally:
        os.fsync = reel  # type: ignore[assignment]

    assert cible.read_text(encoding="utf-8") == "ce qui était là\n"


def test_une_ecriture_interrompue_ne_laisse_pas_de_reliquat(tmp_path: Path) -> None:
    """Un fichier provisoire abandonné se prendrait pour un artefact."""
    cible = tmp_path / "artefact.py"

    class Interruption(BaseException):
        pass

    def exploser(*_args: object, **_kwargs: object) -> None:
        raise Interruption()

    reel = os.replace
    os.replace = exploser  # type: ignore[assignment]
    try:
        with pytest.raises(Interruption):
            ecrire(cible, "peu importe")
    finally:
        os.replace = reel  # type: ignore[assignment]

    reliquats = [c.name for c in tmp_path.iterdir() if c.name.startswith(PREFIXE)]
    assert reliquats == []


def test_le_provisoire_vit_dans_le_repertoire_de_destination(tmp_path: Path) -> None:
    """Un renommage entre systèmes de fichiers copie, donc il n'est pas atomique.

    Le contrôle lit le code par AST plutôt que d'observer un provisoire qui
    n'existe qu'un dixième de milliseconde : `dir=` doit nommer le répertoire de
    la cible, et rien d'autre.
    """
    import ast
    import inspect

    from generator import ecriture

    source = ast.parse(inspect.getsource(ecriture))
    appel = next(
        n
        for n in ast.walk(source)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "mkstemp"
    )
    dossier = next(m for m in appel.keywords if m.arg == "dir")

    assert "parent" in ast.unparse(dossier.value)


def test_le_repertoire_manquant_est_cree(tmp_path: Path) -> None:
    """Le golden écrit sous `tests/fixtures/<produit>/`, qui peut ne pas exister."""
    cible = tmp_path / "pas" / "encore" / "la" / "artefact.json"

    ecrire(cible, "{}\n")

    assert cible.read_text(encoding="utf-8") == "{}\n"


def test_le_provisoire_nest_pas_visible_a_qui_enumere_les_artefacts(tmp_path: Path) -> None:
    """**Une fenêtre d'apparition vaut une fenêtre de troncature.**

    La première version nommait le provisoire avec le suffixe de la cible, donc
    `.py` pour un module. Il tombait dans le glob `plugins/modules/*.py`, un test
    qui énumère les modules le trouvait, et il avait disparu au moment de le
    lire : `FileNotFoundError` sur un fichier que le glob venait de rendre.

    Le lecteur ne voyait plus un fichier à moitié écrit ; il voyait un fichier
    qui n'existe plus. C'est le même défaut à l'envers.
    """
    cible = tmp_path / "artefact.py"
    vus: list[str] = []
    arret = threading.Event()

    def enumerer() -> None:
        while not arret.is_set():
            vus.extend(chemin.name for chemin in tmp_path.glob("*.py"))

    guetteur = threading.Thread(target=enumerer, daemon=True)
    guetteur.start()
    for _ in range(30):
        ecrire(cible, "le contenu\n")
    arret.set()
    guetteur.join(timeout=2)

    assert vus, "l'énumérateur n'a rien vu, le contrôle ne mesure rien"
    assert set(vus) == {"artefact.py"}, (
        f"le glob des artefacts a rendu autre chose : {sorted(set(vus))}"
    )


def test_le_suffixe_du_provisoire_nest_pas_celui_de_la_cible(tmp_path: Path) -> None:
    """Le contrôle porte sur la déclaration, que la fenêtre soit ouverte ou non.

    Le test précédent dépend d'une course ; celui-ci tient même le jour où la
    machine est trop rapide pour l'ouvrir.
    """
    assert SUFFIXE not in (".py", ".json", ".yml", ".md")
