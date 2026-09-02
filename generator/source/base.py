"""Accès à la source structurée décrivant les APIs Scaleway.

La source retenue est documentée dans `docs/architecture/contrats-scaleway.md` : un
document OpenAPI 3.1 par produit et par version, publié sur le portail
developers. Le générateur ne l'interroge jamais sur le réseau pendant une
génération : il lit une copie versionnée dans `specs/`, et le
téléchargement est une opération séparée (`mise run sync:api`).

Cette séparation est ce qui rend la génération déterministe et reproductible
hors ligne, et ce qui permet à la CI de détecter une dérive d'API comme un
diff de fichier plutôt que comme un échec intermittent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

#: Racine des documents versionnés, relative à la racine du dépôt.
DEFAULT_SPEC_ROOT = Path(__file__).resolve().parents[2] / "specs" / "scaleway"


class SpecNotFoundError(FileNotFoundError):
    """Le document demandé n'est pas présent dans la copie versionnée."""


@dataclass(frozen=True)
class SpecDocument:
    """Un document de contrat brut, tel que lu sur disque."""

    product: str
    version: str
    path: Path
    document: dict[str, Any]

    @property
    def slug(self) -> str:
        return f"{self.product}.{self.version}"


class SpecSource(Protocol):
    """Fournit les documents de contrat au parser."""

    def load(self, product: str, version: str) -> SpecDocument: ...

    def available(self) -> list[tuple[str, str]]: ...


@dataclass(frozen=True)
class VendoredSpecSource:
    """Lit les documents dans l'arborescence `specs/scaleway/<produit>.<version>.yml`."""

    root: Path = DEFAULT_SPEC_ROOT

    def load(self, product: str, version: str) -> SpecDocument:
        path = self.root / f"{product}.{version}.yml"
        if not path.is_file():
            raise SpecNotFoundError(
                f"contrat absent : {path}. Lancer `mise run sync:api` pour le télécharger."
            )
        with path.open(encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
        if not isinstance(document, dict):
            raise ValueError(f"{path} ne contient pas un document OpenAPI")
        return SpecDocument(product=product, version=version, path=path, document=document)

    def available(self) -> list[tuple[str, str]]:
        """Liste les couples (produit, version) présents sur disque, triés."""
        found: list[tuple[str, str]] = []
        for path in sorted(self.root.glob("*.yml")):
            product, _, version = path.stem.rpartition(".")
            if product and version:
                found.append((product, version))
        return found
