"""Une sortie Terraform qui traverse vers un module se dépouille de sa portée.

La règle était écrite dans `CLAUDE.md` et rien ne l'exécutait. Mesuré sur le
compte réel le 2026-09-10 : quatre sorties sur cinq la violaient, `GetFrontend`
rendait 400 `invalid_arguments` sur l'une d'elles, et le bloc de mesure #119
n'a jamais tourné jusqu'au bout là où il est le seul à pouvoir tourner.
"""

from __future__ import annotations

import pytest

from scripts.example import ExempleError, refuser_une_sortie_portee

ZONE = "fr-par-1/afc7e83d-6a06-4f07-a5f6-fa27bda73b8c"
REGION = "fr-par/a3121446-44db-4160-a498-8f14c419e265"
NU = "d455b580-a72a-471b-b993-4accc3cdfec3"


def _sorties(**valeurs: object) -> dict[str, dict[str, object]]:
    return {nom: {"value": valeur} for nom, valeur in valeurs.items()}


def test_une_sortie_zonale_est_refusee() -> None:
    with pytest.raises(ExempleError) as erreur:
        refuser_une_sortie_portee(_sorties(frontend_tls=ZONE))

    message = str(erreur.value)
    assert "frontend_tls" in message
    assert "fr-par-1" in message
    # Le message dit quoi faire : la règle vit dans `outputs.tf`, pas ici.
    assert "outputs.tf" in message


def test_une_sortie_regionale_est_refusee_aussi() -> None:
    """`fr-par/<uuid>` n'a pas de chiffre de zone, et casse tout autant."""
    with pytest.raises(ExempleError):
        refuser_une_sortie_portee(_sorties(reseau=REGION))


def test_une_liste_est_regardee_element_par_element() -> None:
    """`certificats_mesure` est une liste, et c'est elle qui a coûté la mesure."""
    with pytest.raises(ExempleError) as erreur:
        refuser_une_sortie_portee(_sorties(certificats_mesure=[NU, ZONE]))

    assert "certificats_mesure" in str(erreur.value)


def test_un_identifiant_nu_passe() -> None:
    refuser_une_sortie_portee(_sorties(image_doree=NU, certificats=[NU, NU]))


def test_ce_qui_n_est_pas_un_identifiant_passe() -> None:
    """Une URL, une adresse, un compte : la garde ne doit pas les confondre."""
    refuser_une_sortie_portee(
        _sorties(
            application_url="http://51.15.1.2/",
            bastion_ip="51.15.1.2",
            run_id="68379ab59",
            attendu={"total": 5},
            reseau_web="acs-68379ab59-web",
            vide="",
        )
    )


def test_toutes_les_fautives_sont_nommees_pas_seulement_la_premiere() -> None:
    """Corriger une sortie pour découvrir la suivante au run d'après coûte cher."""
    with pytest.raises(ExempleError) as erreur:
        refuser_une_sortie_portee(_sorties(un=ZONE, deux=REGION))

    message = str(erreur.value)
    assert "un" in message and "deux" in message
