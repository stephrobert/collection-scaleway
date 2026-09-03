# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""La taxonomie des échecs de découverte.

Le plugin officiel écrit trois fois `except ScalewayException: pass`. Un jeton
sans droit, un produit absent d'une zone et une panne d'API y produisent le
même résultat : un inventaire incomplet, silencieux, et un code de retour 0.

Ces trois situations n'ont pourtant pas la même gravité :

* **l'authentification** est fatale partout. Aucun provider ne peut travailler,
  et continuer ne produirait qu'un inventaire vide qui se présente comme
  complet ;
* **le droit refusé sur un produit** est tolérable : un jeton peut légitimement
  n'avoir accès qu'à une partie du parc. C'est un avertissement, et il doit
  être visible ;
* **le produit absent d'une région** n'est pas une erreur du tout. Apple
  Silicon n'existe pas dans toutes les zones, et le dire à chaque exécution
  serait du bruit permanent.
"""

from __future__ import annotations


class InventoryError(Exception):
    """Un échec de découverte, classé."""


class AuthenticationFailed(InventoryError):
    """Les identifiants sont refusés : rien ne peut être découvert."""


class PermissionDenied(InventoryError):
    """Le jeton n'a pas le droit sur cette ressource, mais en a d'autres."""


class ProductUnavailable(InventoryError):
    """Le produit n'existe pas à cet endroit. Ce n'est pas une panne."""


class DiscoveryFailed(InventoryError):
    """L'API a échoué pour une raison qui n'est ni un droit ni une absence."""


def classify(status_code: int | None, message: str = "") -> type[InventoryError]:
    """Range un échec d'API dans la bonne catégorie, d'après son statut HTTP.

    Le statut est ce que l'API dit d'elle-même. S'en remettre au texte du
    message serait deviner, et un message change sans prévenir.

    Une exception, et elle a coûté cher : Scaleway rend parfois 401 pour un
    droit manquant, pas seulement pour des identifiants refusés. Le test du
    message est donc conservé, mais il cherche `permission` et non `denied`.

    `denied` était présent dans le corps 401 **normal** de Scaleway, celui d'un
    refus d'authentification :

        {"message": "denied authentication", "type": "denied_authentication"}

    Résultat : aucun jeton révoqué ne levait jamais `AuthenticationFailed`. La
    moitié fatale de cette taxonomie ne servait à rien, et un inventaire vide
    sortait avec un code de retour 0, exactement le défaut qu'elle existe pour
    empêcher.
    """
    if status_code in (401, 403) and "permission" in message.lower():
        return PermissionDenied
    if status_code == 401:
        return AuthenticationFailed
    if status_code == 403:
        return PermissionDenied
    if status_code in (404, 501):
        return ProductUnavailable
    return DiscoveryFailed
