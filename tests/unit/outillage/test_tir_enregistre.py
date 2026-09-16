"""Un tir facturé qui ne mesure rien n'a pas à être possible.

`scripts/example.py` porte cette phrase depuis longtemps, dans le refus qu'il
oppose à un proxy absent :

> L'exercice s'arrête plutôt que de parler au cloud sans enregistrer : un run
> facturé qui ne mesure rien...

Elle ne pouvait pas être tenue. Le refus ne se déclenchait que si
`--enregistrer` avait été donné, et rien n'exigeait cette option : sans elle, le
tir partait, créait de vraies ressources, et ne laissait qu'un code de sortie.

Mesuré le 16 septembre 2026 : cinq tirs réels se sont succédé sans
enregistrement, dont trois pour trancher une question d'ordre d'une liste que la
transcription aurait répondue du premier coup. Une assertion ne rend qu'un
booléen ; la transcription rend ce que l'API a répondu.

`--enregistrer` choisit désormais **où**, plus **si**.
"""

from __future__ import annotations

import ast
from pathlib import Path

LANCEUR = Path(__file__).resolve().parents[3] / "scripts" / "example.py"


def _source() -> ast.Module:
    return ast.parse(LANCEUR.read_text(encoding="utf-8"))


def test_la_cible_reelle_enregistre_sans_quon_le_demande() -> None:
    """Le proxy démarre sur le chemin par défaut quand personne n'en donne un.

    La garde porte sur la forme : faire tourner le lanceur demanderait un compte
    facturé, ce qui est exactement ce qu'un test unitaire ne fait pas. Ce
    qu'elle garantit est étroit et suffit : `demarrer_proxy` n'est plus sous une
    condition qui dépend de l'option.
    """
    appels_sous_condition = [
        noeud
        for noeud in ast.walk(_source())
        if isinstance(noeud, ast.If)
        for descendant in ast.walk(noeud.test)
        if isinstance(descendant, ast.Attribute) and descendant.attr == "enregistrer"
        # Le `if not arguments.enregistrer:` qui calcule le défaut est légitime :
        # ce qui ne l'est pas est de conditionner le démarrage du proxy.
        for corps in noeud.body
        for appel in ast.walk(corps)
        if isinstance(appel, ast.Call)
        and isinstance(appel.func, ast.Name)
        and appel.func.id == "demarrer_proxy"
    ]

    assert appels_sous_condition == [], (
        "`demarrer_proxy` est de nouveau sous une condition qui lit "
        "`arguments.enregistrer` : un tir réel repartirait sans transcription, "
        "et ne rendrait qu'un booléen sur un compte facturé."
    )


def test_le_chemin_par_defaut_porte_sa_date() -> None:
    """`preuve_tir` et `preuve_reelle` lisent la date dans le nom du fichier.

    Un nom sans date ferait refuser la transcription par les deux, après le tir,
    c'est-à-dire au pire moment.
    """
    fonction = next(
        noeud
        for noeud in _source().body
        if isinstance(noeud, ast.FunctionDef) and noeud.name == "transcription_par_defaut"
    )
    source = ast.unparse(fonction)

    assert "%Y-%m-%d" in source, (
        "le chemin de transcription par défaut ne porte plus sa date : les "
        "outils qui la relisent la refuseront, une fois le tir payé."
    )
