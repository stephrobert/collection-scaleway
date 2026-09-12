# -*- coding: utf-8 -*-
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
    "instance": ("fr-par-1", "fr-par-2", "fr-par-3", "it-mil-1", "nl-ams-1", "nl-ams-2", "nl-ams-3", "pl-waw-1", "pl-waw-2", "pl-waw-3",),
    "lb": ("fr-par-1", "fr-par-2", "nl-ams-1", "nl-ams-2", "nl-ams-3", "pl-waw-1", "pl-waw-2", "pl-waw-3",),
}
