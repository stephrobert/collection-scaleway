"""Le verdict du contrôle de résidu doit atteindre l'appelant.

**Le contrôle marchait, et sa conclusion était jetée.** Un tir réel du
16 septembre 2026 a laissé une adresse réservée sur le compte facturé. Le
lanceur l'a vu, l'a écrit dans son artefact (« non vérifié »), l'a affiché en
clair, et il est sorti en 0.

La cause tient en une règle de Python : `return` évalue sa valeur sur-le-champ,
et un `finally` qui modifie ensuite la variable ne change rien à ce qui a déjà
été rendu. Le `return` était dans le `try`, et les deux `code = 1` de la
destruction et du résidu dans le `finally`.

C'est la pire des deux pannes possibles, parce qu'elle ressemble à un succès :
un tir qui laisse des ressources derrière lui devient indiscernable d'un tir
propre, pour quiconque lit le code de sortie plutôt que le journal qui le
précède.

Ce fichier ne lance rien : il lit le code, par AST. Faire tourner le lanceur
demanderait un compte Scaleway, et c'est précisément ce qu'on ne veut pas dans
un test unitaire.
"""

from __future__ import annotations

import ast
from pathlib import Path

LANCEUR = Path(__file__).resolve().parents[3] / "scripts" / "example.py"


def _main() -> ast.FunctionDef:
    arbre = ast.parse(LANCEUR.read_text(encoding="utf-8"))
    return next(
        noeud for noeud in arbre.body if isinstance(noeud, ast.FunctionDef) and noeud.name == "main"
    )


def _essai_avec_finally(fonction: ast.FunctionDef) -> ast.Try:
    """Le `try`/`finally` qui encadre le déploiement et sa destruction."""
    return next(
        noeud for noeud in ast.walk(fonction) if isinstance(noeud, ast.Try) and noeud.finalbody
    )


def test_le_verdict_de_la_destruction_nest_pas_court_circuite() -> None:
    """Un `return` dans le `try` fige la valeur avant que le `finally` parle.

    La garde porte sur la **forme**, et c'est assumé : le comportement demande un
    compte facturé. Ce que la forme garantit est exactement ce qui manquait, et
    rien de plus.
    """
    essai = _essai_avec_finally(_main())

    retours = [
        noeud
        for morceau in essai.body
        for noeud in ast.walk(morceau)
        # Un `return` dans une fonction imbriquée appartient à celle-ci, pas au
        # `try` : le compter ferait rougir la garde sur du code sans rapport.
        if isinstance(noeud, ast.Return)
        and not any(
            isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda)
            for parent in ast.walk(morceau)
            if parent is not morceau and noeud in ast.walk(parent)
        )
    ]

    assert retours == [], (
        f"{len(retours)} `return` dans le corps du `try` : le `finally` pose "
        "`code = 1` quand la destruction échoue ou que du résidu subsiste, et "
        "Python a déjà figé la valeur rendue. Le contrôle sortirait alors en 0 "
        "sur un compte où il reste des ressources facturées."
    )


def test_le_finally_decide_encore_du_code_de_sortie() -> None:
    """Sans cette écriture-là, le test précédent serait vrai et vide.

    Un `try` dont le `finally` ne toucherait plus à `code` passerait la garde
    ci-dessus sans rien garantir : c'est la moitié qui manque, et elle est aussi
    facile à perdre en refactorant.
    """
    essai = _essai_avec_finally(_main())

    ecritures = [
        cible.id
        for morceau in essai.finalbody
        for noeud in ast.walk(morceau)
        if isinstance(noeud, ast.Assign)
        for cible in noeud.targets
        if isinstance(cible, ast.Name) and cible.id == "code"
    ]

    assert ecritures, (
        "le `finally` ne décide plus du code de sortie. La destruction et le "
        "contrôle de résidu s'y jouent : s'ils n'y écrivent plus `code`, leur "
        "verdict ne sort plus du programme."
    )
