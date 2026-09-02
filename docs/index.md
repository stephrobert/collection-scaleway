# collection-scaleway

Ce dépôt ne contient pas une collection Ansible écrite à la main : il contient
le **générateur qui l'écrit**, les contrats versionnés qu'il lit, et les
décisions qui transforment une API technique en interface Ansible cohérente.

```{note}
On ne suit pas l'API à la main, on la mesure. Scaleway a ajouté 453 méthodes
SDK et en a retiré 26 en douze mois : une collection écrite à la main est
périmée avant d'être publiée.
```

La frontière qui tranche toutes les ambiguïtés de conception :

> Terraform provisionne les ressources. Ansible exploite les ressources
> existantes.

## Par où commencer

- [Architecture du générateur](architecture/generateur.md) : le pipeline, les
  décisions structurantes, et ce que le projet ne fait pas.
- [L'inventaire dynamique](guides/inventaire-dynamique.md) : le guide d'usage
  du plugin, et le piège d'Ansible sur le mode strict.
- [Les contrats Scaleway](architecture/contrats-scaleway.md) : la source, ses
  limites mesurées, sa surveillance.

```{toctree}
:caption: Comprendre
:maxdepth: 2

architecture/generateur
architecture/contrats-scaleway
architecture/runtime
```

```{toctree}
:caption: Utiliser
:maxdepth: 2

guides/inventaire-dynamique
```

```{toctree}
:caption: Mesure
:maxdepth: 2

mesure/index
```

```{toctree}
:caption: Référence de la collection
:maxdepth: 2

collections/index
```

```{toctree}
:caption: Le générateur
:maxdepth: 2

api/index
```

```{toctree}
:caption: Le dépôt
:maxdepth: 1

scorecard
```
