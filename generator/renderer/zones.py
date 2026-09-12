"""Les zones que chaque produit déclare, écrites depuis le contrat.

Deux produits ne servent pas les mêmes zones, et rien ne le disait au runtime :
le rapport de parc demandait au Load Balancer des zones que son contrat ne
déclare pas, et rapportait deux zones « non mesurées » à chaque exécution
propre. Un signal qui crie au loup est un signal que personne ne lit, et
`zones_unmeasured` porte l'affirmation la plus répétée de ce dépôt (#222).

**Écrit, jamais recopié.** Mettre les huit zones du Load Balancer dans un rôle
en ferait une seconde source du contrat, fausse le jour où le produit ouvre une
zone. Le contrat les porte, le générateur les lit, et `check:generated` tient le
fichier produit.
"""

from __future__ import annotations

EN_TETE = '''# -*- coding: utf-8 -*-
# This file is generated. Do not edit manually.
"""Les zones que chaque produit déclare, lues dans les contrats versionnés.

Deux produits ne servent pas les mêmes zones. Le rapport de parc demandait au
Load Balancer des zones que son contrat ne déclare pas, et rendait deux zones
« non mesurées » à chaque exécution propre : une mesure qui n'en était pas une,
là où `zones_unmeasured` porte précisément la distinction entre « rien n'a été
mesuré » et « rien n'a été trouvé » (#222).

Recopier ces listes ailleurs en ferait une seconde source, fausse le jour où un
produit ouvre une zone.
"""

from __future__ import annotations

#: Les zones déclarées par le contrat de chaque produit généré.
ZONES: dict[str, tuple[str, ...]] = {
'''


def render_zones(zones: dict[str, tuple[str, ...]]) -> str:
    """Le fichier que le générateur dépose dans `module_utils`."""
    lignes = [EN_TETE]
    for produit in sorted(zones):
        valeurs = ", ".join(f'"{zone}"' for zone in zones[produit])
        lignes.append(f'    "{produit}": ({valeurs},),\n')
    lignes.append("}\n")
    return "".join(lignes)
