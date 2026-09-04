"""Télécharge les contrats OpenAPI Scaleway suivis par le générateur.

Le portail developers publie un document par produit et par version, et c'est
le lien « Download schema » de chaque page. Il n'existe ni dépôt public ni
index machine-readable : `specs/scaleway/products.txt` est cet index, tenu à la
main, et c'est un fait sur Scaleway, pas un choix de conception.

Le téléchargement est séparé de la génération : les contrats sont versionnés
dans le dépôt, la génération les lit sur disque, et une évolution de l'API
apparaît comme un diff dans une revue plutôt que comme un résultat qui change
tout seul entre deux exécutions.

    python scripts/sync_specs.py            # met à jour tous les contrats suivis
    python scripts/sync_specs.py instance   # un seul produit
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "specs" / "scaleway"
PRODUCTS_FILE = SPEC_ROOT / "products.txt"

BASE_URL = "https://www.scaleway.com/en/developers/api"
TIMEOUT_SECONDS = 30


#: Sous-répertoire des contrats suivis mais non générés.
TRACKED_ONLY_DIR = "suivis"


@dataclass(frozen=True)
class Product:
    """Une ligne de l'index, telle que le portail la nomme."""

    slug: str
    product: str
    version: str
    #: Suivi pour la dérive, sans module, sans rapport, sans golden.
    tracked_only: bool = False

    @property
    def target(self) -> Path:
        """Où le contrat se range. Le générateur ne voit pas `suivis/`."""
        parent = SPEC_ROOT / TRACKED_ONLY_DIR if self.tracked_only else SPEC_ROOT
        return parent / f"{self.product}.{self.version}.yml"


def read_products() -> list[Product]:
    """Lit l'index : `<slug-portail> [<produit>] <version> [suivi]`.

    Le marqueur `suivi` se retire **avant** de compter les champs : sans ça,
    `ipam v1 suivi` se lirait comme `<slug> <produit> <version>` et le contrat
    s'appellerait `v1.suivi.yml`. Un index qui se trompe silencieusement de
    fichier est pire qu'un index qui refuse la ligne.
    """
    entries: list[Product] = []
    for line in PRODUCTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        tracked_only = fields[-1] == "suivi"
        if tracked_only:
            fields = fields[:-1]
        if len(fields) == 2:
            slug, version = fields
            product = slug
        elif len(fields) == 3:
            slug, product, version = fields
        else:
            raise SystemExit(f"{PRODUCTS_FILE} : ligne mal formée : {line!r}")
        entries.append(Product(slug, product, version, tracked_only))
    return entries


def download(slug: str, version: str) -> bytes:
    url = f"{BASE_URL}/{slug}/{version}/schema.yml"
    request = urllib.request.Request(url, headers={"User-Agent": "scaleway-ansible-generator"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise SystemExit(f"{url} : HTTP {response.status}")
        payload: bytes = response.read()
        return payload


def main(argv: list[str]) -> int:
    wanted = set(argv[1:])
    failures = 0
    for entry in read_products():
        slug, product, version = entry.slug, entry.product, entry.version
        if wanted and product not in wanted and slug not in wanted:
            continue
        target = entry.target
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload = download(slug, version)
        except (urllib.error.URLError, urllib.error.HTTPError) as error:
            # Un 404 signale un slug qui a changé, pas un contrat vide : ne
            # jamais laisser un fichier périmé derrière un échec silencieux.
            print(f"échec : {slug}/{version} : {error}", file=sys.stderr)
            failures += 1
            continue
        previous = target.read_bytes() if target.is_file() else b""
        target.write_bytes(payload)
        etat = "inchangé" if payload == previous else "mis à jour"
        print(f"{target.relative_to(ROOT)} : {len(payload)} octets, {etat}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
