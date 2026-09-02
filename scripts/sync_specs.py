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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "specs" / "scaleway"
PRODUCTS_FILE = SPEC_ROOT / "products.txt"

BASE_URL = "https://www.scaleway.com/en/developers/api"
TIMEOUT_SECONDS = 30


def read_products() -> list[tuple[str, str, str]]:
    """Lit l'index : `<slug-portail> <produit> <version>`, commentaires ignorés."""
    entries: list[tuple[str, str, str]] = []
    for line in PRODUCTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) == 2:
            slug, version = fields
            product = slug
        elif len(fields) == 3:
            slug, product, version = fields
        else:
            raise SystemExit(f"{PRODUCTS_FILE} : ligne mal formée : {line!r}")
        entries.append((slug, product, version))
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
    for slug, product, version in read_products():
        if wanted and product not in wanted and slug not in wanted:
            continue
        target = SPEC_ROOT / f"{product}.{version}.yml"
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
