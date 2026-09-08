"""L'ordre que l'API rend, mesuré et non supposé (#119, ADR-009).

ADR-009 pose qu'un tableau reste comparé **dans l'ordre** tant que personne n'a
observé l'API le réordonner, et que `set` ne s'adopte jamais tout seul. Ce
fichier est la trace du jour où quelqu'un a observé.

Mesuré le 8 septembre 2026 contre le compte Scaleway réel, à travers
`feint proxy`, transcription conservée :

```text
seq 277  CreateFrontend  envoyé [cfcb677d, 28856172]  rendu [cfcb677d, 28856172]
seq 286  UpdateFrontend  envoyé [cfcb677d, 28856172]  rendu [cfcb677d, 28856172]
seq 288  GetFrontend                                  rendu [28856172, cfcb677d]
seq 467  GetFrontend                                  rendu [28856172, cfcb677d]
```

L'écriture répond dans l'ordre demandé, la relecture l'inverse, et elle est
stable. Sans l'override, `lb_frontend` comparait `[a, b]` à `[b, a]` et rendait
`changed` à chaque exécution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from generator.ansible.collection import load_collection
from generator.ansible.introductions import load_introductions
from generator.ansible.models import build_module_specs
from generator.plan import build_plan

ROOT = Path(__file__).resolve().parents[3]
SPECS = ROOT / "specs" / "scaleway"


@pytest.fixture(scope="module")
def runtime(collection_root: Path) -> Any:
    from ansible_collections.stephrobert.scaleway.plugins.module_utils import scaleway

    return scaleway


#: Ce que la transcription a montré, dans l'ordre où l'API l'a dit.
DEMANDE = ["cfcb677d", "28856172"]
RENDU_PAR_LA_LECTURE = ["28856172", "cfcb677d"]


def test_les_certificats_dun_frontend_se_comparent_sans_ordre() -> None:
    """La stratégie que la mesure impose, et qu'aucun type ne pouvait décider."""
    plan = build_plan("lb", "v1", spec_root=SPECS)
    specs, _ = build_module_specs(plan, load_collection(), introductions=load_introductions())
    frontend = next(item for item in specs if item.name == "lb_frontend")
    assert dict(frontend.comparisons)["certificate_ids"] == "set"


def test_les_autres_listes_du_meme_module_restent_dans_lordre() -> None:
    """Le contre-exemple : la mesure ne vaut que pour le champ mesuré.

    Un override posé sur un champ ne se propage pas aux voisins, et c'est ce
    qui distingue une décision d'une généralisation.
    """
    plan = build_plan("lb", "v1", spec_root=SPECS)
    specs, _ = build_module_specs(plan, load_collection(), introductions=load_introductions())
    ip = next(item for item in specs if item.name == "lb_ip")
    assert dict(ip.comparisons)["tags"] == "ordered_list"


def test_lordre_inverse_que_lapi_rend_ne_declenche_aucune_ecriture(runtime: Any) -> None:
    """Le comportement que l'override achète, sur les valeurs mesurées."""
    assert runtime._identique("set", DEMANDE, RENDU_PAR_LA_LECTURE) is True


def test_la_comparaison_dans_lordre_aurait_rendu_changed(runtime: Any) -> None:
    """Le défaut, reproduit : sans override, le module réécrivait à chaque fois."""
    assert runtime._identique("ordered_list", DEMANDE, RENDU_PAR_LA_LECTURE) is False


def test_un_certificat_de_plus_reste_un_changement(runtime: Any) -> None:
    """`set` ici conserve les multiplicités : ce n'est pas un ensemble au sens strict.

    Un vrai ensemble dirait que `[a, a, b]` et `[a, b]` sont la même chose, et
    le module annoncerait `ok` sur un état qu'il n'a pas écrit.
    """
    assert runtime._identique("set", [*DEMANDE, "cfcb677d"], RENDU_PAR_LA_LECTURE) is False
