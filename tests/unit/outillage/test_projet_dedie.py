"""L'exercice réel désigne son projet, il ne le devine pas.

`examples/stack/variables.tf` porte `project_id = null`, et rien ne le
renseignait : le fournisseur retombait sur `SCW_DEFAULT_PROJECT_ID` puis sur le
fichier de configuration. Pour qui clone ce dépôt, quarante-cinq ressources
facturées s'installaient donc dans le projet par défaut de son profil, qui peut
être celui de sa production (#191).

Le parcours Scaleway en donne la raison décisive, et elle n'est pas
organisationnelle : **une politique IAM a besoin d'une frontière, et le projet
est la seule qui existe.** Les jeux de permissions ont une portée `projects`,
et rien d'autre.
"""

from __future__ import annotations

import argparse
from typing import Any

import example
import pytest


def _arguments(projet: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(cible="reel", garder=False, enregistrer=None, projet=projet)


@pytest.fixture()
def api_qui_repond(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Une API qui nomme le projet demandé, et note ce qu'on lui a demandé."""
    demandes: list[str] = []

    def _api(env: dict[str, str], chemin: str) -> Any:
        demandes.append(chemin)
        return {"id": chemin.rsplit("/", 1)[-1], "name": "collection-scaleway-lab"}

    monkeypatch.setattr(example, "api", _api)
    return demandes


# --- ce que la garde refuse -----------------------------------------------


def test_aucun_projet_designe_est_refuse() -> None:
    """Ne rien désigner n'autorise pas à choisir pour l'opérateur."""
    with pytest.raises(example.ExempleError) as erreur:
        example.projet_vise({}, _arguments())

    message = str(erreur.value)
    assert "aucun projet Scaleway désigné" in message
    # Le message dit le danger précis, pas « projet manquant ».
    assert "par défaut de votre profil" in message


def test_le_refus_donne_la_marche_a_suivre() -> None:
    """Un refus qui n'apprend rien coûte une recherche à chaque fois."""
    with pytest.raises(example.ExempleError) as erreur:
        example.projet_vise({}, _arguments())

    # Les retours à la ligne du message sont de la mise en forme : un test qui
    # en dépendrait rougirait le jour où quelqu'un replie une phrase.
    message = " ".join(str(erreur.value).split())
    assert "scw account project create" in message
    assert "SCW_EXAMPLE_PROJECT_ID" in message
    # Et la raison pour laquelle le projet se crée hors bande.
    assert "ne peut pas se donner sa propre frontière" in message


def test_le_defaut_du_profil_ne_designe_rien(api_qui_repond: list[str]) -> None:
    """`SCW_DEFAULT_PROJECT_ID` est précisément ce qu'on refuse d'hériter.

    La variable de l'exercice est distincte exprès : retomber sur le défaut du
    profil est le danger, pas la solution de repli.
    """
    with pytest.raises(example.ExempleError):
        example.projet_vise(
            {"SCW_DEFAULT_PROJECT_ID": "11111111-2222-3333-4444-555555555555"}, _arguments()
        )

    assert api_qui_repond == [], "aucun appel ne doit partir sur un projet non désigné"


def test_un_projet_illisible_est_refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ne pas savoir n'est pas savoir que ça va.

    C'est la même règle que le contrôle de résidu applique à `scw` : une
    commande qui ne répond pas ne prouve pas qu'il ne reste rien.
    """

    def _api(env: dict[str, str], chemin: str) -> Any:
        raise RuntimeError("404")

    monkeypatch.setattr(example, "api", _api)

    with pytest.raises(example.ExempleError) as erreur:
        example.projet_vise({}, _arguments(projet="inconnu"))

    assert "n'a pas pu être lu" in str(erreur.value)
    assert "refuse de déployer dans un projet qu'il ne sait pas nommer" in str(erreur.value)


def test_un_projet_sans_nom_est_refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(example, "api", lambda env, chemin: {"id": "x"})

    with pytest.raises(example.ExempleError) as erreur:
        example.projet_vise({}, _arguments(projet="x"))

    assert "ne porte pas de nom" in str(erreur.value)


# --- ce qu'elle laisse passer, et ce qu'elle rend -------------------------


def test_un_projet_designe_en_argument_est_nomme(api_qui_repond: list[str]) -> None:
    """Nommer le projet change ce que l'opérateur voit avant de payer."""
    identifiant, nom = example.projet_vise({}, _arguments(projet="abc-123"))

    assert identifiant == "abc-123"
    assert nom == "collection-scaleway-lab"
    assert api_qui_repond == ["/account/v3/projects/abc-123"]


def test_la_variable_denvironnement_designe_aussi(api_qui_repond: list[str]) -> None:
    identifiant, _ = example.projet_vise({example.PROJET_ENV: "depuis-env"}, _arguments())

    assert identifiant == "depuis-env"


def test_largument_lemporte_sur_la_variable(api_qui_repond: list[str]) -> None:
    """Ce qui est écrit sur la ligne de commande est le plus explicite des deux."""
    identifiant, _ = example.projet_vise(
        {example.PROJET_ENV: "depuis-env"}, _arguments(projet="depuis-argument")
    )

    assert identifiant == "depuis-argument"


def test_les_espaces_autour_dun_identifiant_ne_le_rendent_pas_vide() -> None:
    """Un copier-coller traîne une espace, et un identifiant vide n'en est pas un."""
    with pytest.raises(example.ExempleError):
        example.projet_vise({example.PROJET_ENV: "   "}, _arguments())
