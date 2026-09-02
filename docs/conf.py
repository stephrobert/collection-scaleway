# -*- coding: utf-8 -*-
"""Configuration du site de documentation.

Ce fichier est versionné, mais **le site ne l'est pas** : `scripts/site.py`
assemble une arborescence jetable sous `build/site-src/` à partir de trois
sources, puis Sphinx la construit vers `build/site/`. Rien de dérivé n'entre
dans le dépôt, donc rien de dérivé ne peut y devenir périmé.

Un seul moteur pour deux formats, et ce n'est pas un goût : `antsibull-docs` ne
sait produire que du reStructuredText, mesuré sur `antsibull-docs collection
--help`. Un moteur qui ne lirait pas le RST imposerait deux sites, ou une
conversion avec perte. Les pages produites restent donc en RST, personne ne les
édite ; tout ce qui s'écrit à la main reste en Markdown.
"""

from __future__ import annotations

project = "collection-scaleway"
copyright = "2026, Stéphane Robert"
author = "Stéphane Robert"

#: La langue du site, celle du projet. Elle décide aussi de la segmentation de
#: l'index de recherche : un site français indexé en anglais ne trouve pas
#: « générateur » quand on tape « generateur ».
language = "fr"

extensions = [
    # Les guides et les pages de mesure sont en Markdown.
    "myst_parser",
    # Les docstrings du générateur, rendues telles quelles.
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    # Les pages d'antsibull renvoient vers deux étiquettes du site officiel
    # d'Ansible, `common_return_values` et `ansible_configuration_settings`.
    # Sans intersphinx, ce sont deux références non résolues, donc deux
    # avertissements, donc un échec sous `-W`. Mesuré : trois occurrences.
    "sphinx.ext.intersphinx",
    # Les rôles `:ansopt:`, `:ansval:` et `:ansplugin:` que les pages
    # d'antsibull emploient. Sans cette extension, chaque option documentée
    # devient un rôle inconnu, donc un avertissement, donc un échec sous `-W`.
    "sphinx_antsibull_ext",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

#: MyST : ce qu'on active est ce qu'on utilise, pas le catalogue complet.
#: `linkify` est absent volontairement : il transforme une URL nue en lien,
#: et il coûte un paquet de plus au verrou pour un service que les liens
#: explicites rendent déjà.
myst_enable_extensions = ["deflist", "colon_fence"]
myst_heading_anchors = 3

html_theme = "sphinx_ansible_theme"
html_title = "collection-scaleway"
html_short_title = "collection-scaleway"
html_last_updated_fmt = "%d/%m/%Y"
#: GitHub Pages sert le site sous le nom du dépôt. L'URL canonique le dit, pour
#: qu'un moteur de recherche ne considère pas deux adresses comme deux sites.
html_baseurl = "https://stephrobert.github.io/collection-scaleway/"

#: Ce que le thème d'Ansible attend. Les pages d'antsibull s'y insèrent sans
#: retouche, ce qui est la raison de le choisir.
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 3,
    "style_external_links": True,
}

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "member-order": "bysource",
}
#: Les annotations sont dans les signatures, pas recopiées dans le texte.
autodoc_typehints = "signature"
#: Le générateur importe PyYAML et Jinja2 ; ils sont au verrou, donc rien à
#: simuler. Cette liste reste vide à dessein : un mock cache un import cassé.
autodoc_mock_imports: list[str] = []

#: Le seul accès réseau de la construction. Il résout les renvois des pages
#: d'antsibull vers la documentation officielle d'Ansible ; sans lui, elles
#: pointeraient dans le vide, ce qui est pire qu'un site plus lent à bâtir.
intersphinx_mapping = {
    "ansible": ("https://docs.ansible.com/ansible/latest/", None),
}
#: Un site injoignable ne doit pas faire échouer la construction sans le dire :
#: intersphinx émet alors un avertissement, que `-W` transforme en échec.
intersphinx_timeout = 30

nitpicky = False
