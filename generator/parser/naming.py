"""Normalisation des noms entre le vocabulaire de l'API et celui d'Ansible.

Toutes les règles sont explicites et testées. Un cas qu'elles traitent mal se
corrige par un override, jamais par une exception glissée ici : la table des
irréguliers est courte, et elle doit le rester pour qu'un lecteur sache ce que
le générateur fait sans l'exécuter.
"""

from __future__ import annotations

import re

#: Sigles que le découpage camelCase ne saurait pas retrouver seul.
#: `PrivateNICs` se découpe en `Private` + `NICs` uniquement parce que `NIC`
#: est déclaré ici ; sans cette table on obtient `private_ni_cs`.
ACRONYMS: tuple[str, ...] = (
    "NICs",
    "NIC",
    "IPs",
    "IPv6",
    "IPv4",
    "IPAM",
    "IDs",
    "ID",
    "ACLs",
    "ACL",
    "SSH",
    "DNS",
    "URL",
    "TTL",
    "VPC",
    "SQL",
    # `/k8s/v1/...` : le chemin réel du produit que le portail nomme
    # `kubernetes`. Il finit par un `s` sans être un pluriel, comme `DNS`.
    "K8S",
)

#: Pluriels que la règle générale casserait.
IRREGULAR_SINGULARS: dict[str, str] = {
    "data": "data",
    "status": "status",
    "quotas": "quota",
}

#: Mots que la table ci-dessus déclare identiques au singulier et au pluriel.
INVARIABLE_WORDS: frozenset[str] = frozenset(
    word for word, singular in IRREGULAR_SINGULARS.items() if word == singular
)

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def split_words(name: str) -> list[str]:
    """Découpe un identifiant en mots, en respectant les sigles déclarés.

    >>> split_words("ListPrivateNICs")
    ['list', 'private', 'nics']
    >>> split_words("security_group_rules")
    ['security', 'group', 'rules']
    """
    placeholder = name
    holes: dict[str, str] = {}
    for index, acronym in enumerate(ACRONYMS):
        if acronym in placeholder:
            token = f"\x00{index}\x00"
            holes[token] = acronym
            # Les délimiteurs sont indispensables : sans eux, le sigle absorbe
            # la frontière camelCase qui le précède et `PrivateNICs` ressort en
            # un seul mot.
            placeholder = placeholder.replace(acronym, f"_{token}_")

    placeholder = placeholder.replace("-", "_")
    placeholder = _CAMEL_BOUNDARY.sub("_", placeholder)

    words: list[str] = []
    for chunk in placeholder.split("_"):
        if not chunk:
            continue
        for token, acronym in holes.items():
            chunk = chunk.replace(token, acronym)
        words.append(chunk.lower())
    return words


def snake_case(name: str) -> str:
    """`ListPrivateNICs` -> `list_private_nics`."""
    return "_".join(split_words(name))


def _est_un_sigle_invariable(lowered: str) -> bool:
    """Un sigle écrit tout en capitales ne se dépluralise pas.

    `DNS` finit par un `s` sans être un pluriel, et la règle générale en faisait
    `dn`. Le sigle était pourtant **déjà déclaré** dans `ACRONYMS` : le cas était
    connu d'un côté du code et ignoré de l'autre, et il suffit de le lire.

    La distinction se fait sur la casse de la déclaration, qui porte déjà
    l'information : `DNS` et `K8S` sont des sigles entiers, tandis que `IPs`,
    `NICs`, `IDs` et `ACLs` sont les **pluriels** de sigles et doivent, eux,
    perdre leur `s`. Comparer en capitales suffit à les séparer.
    """
    return lowered.upper() in ACRONYMS


def singularize(word: str) -> str:
    """Singularise un mot anglais avec les seules règles dont l'IR a besoin.

    >>> singularize("servers"), singularize("policies"), singularize("addresses")
    ('server', 'policy', 'address')
    >>> singularize("dns"), singularize("k8s"), singularize("ips")
    ('dns', 'k8s', 'ip')
    """
    lowered = word.lower()
    if lowered in IRREGULAR_SINGULARS:
        return IRREGULAR_SINGULARS[lowered]
    if _est_un_sigle_invariable(lowered):
        return lowered
    if lowered.endswith("ies") and len(lowered) > 4:
        return lowered[:-3] + "y"
    for suffix in ("sses", "shes", "ches", "xes", "zes"):
        if lowered.endswith(suffix):
            return lowered[:-2]
    if lowered.endswith("ss") or not lowered.endswith("s"):
        return lowered
    return lowered[:-1]


def singularize_phrase(phrase: str) -> str:
    """Singularise chaque mot d'une expression snake_case.

    `servers_types` -> `server_type`, car Scaleway écrit ses collections au
    pluriel jusque dans les mots intermédiaires.
    """
    return "_".join(singularize(word) for word in phrase.split("_") if word)


def pluralize(word: str) -> str:
    """Pluralise un mot anglais, avec les seules règles dont la doc a besoin.

    L'IR est au singulier ; une phrase de documentation qui parle d'une
    collection est au pluriel. Les invariables sont ceux que la table des
    irréguliers déclare identiques au singulier et au pluriel : `data` et
    `status` s'y trouvent, `quotas` non, car son singulier `quota` se pluralise
    normalement.

    >>> pluralize("server"), pluralize("policy"), pluralize("address")
    ('servers', 'policies', 'addresses')
    """
    lowered = word.lower()
    if lowered in INVARIABLE_WORDS:
        return lowered
    if lowered.endswith("y") and len(lowered) > 1 and lowered[-2] not in "aeiou":
        return lowered[:-1] + "ies"
    if lowered.endswith(("s", "sh", "ch", "x", "z")):
        return lowered + "es"
    return lowered + "s"


def pluralize_phrase(phrase: str) -> str:
    """Pluralise le dernier mot d'une expression snake_case, en mots séparés.

    `server_type` -> `server types` : c'est la tête de l'expression qui porte
    le nombre, et la documentation se lit en mots, pas en snake_case.
    """
    words = [word for word in phrase.split("_") if word]
    if not words:
        return phrase
    return " ".join([*words[:-1], pluralize(words[-1])])
