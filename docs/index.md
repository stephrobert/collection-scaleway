# collection-scaleway

This repository does not contain a hand-written Ansible collection: it contains
the **generator that writes it**, the versioned contracts it reads, and the
decisions that turn a technical API into a coherent Ansible interface.

```{note}
We do not follow the API by hand, we measure it. Scaleway added 453 SDK methods
and removed 26 in twelve months: a hand-written collection is stale before it
is published.
```

The boundary that settles every design ambiguity:

> Terraform provisions resources. Ansible operates existing resources.

## Where to start

- [Generator architecture](architecture/generator.md): the pipeline, the
  structural decisions, and what this project does not do.
- [The dynamic inventory](guides/dynamic-inventory.md): the plugin's usage
  guide, and Ansible's trap around strict mode.
- [The Scaleway contracts](architecture/scaleway-contracts.md): the source, its
  measured limits, and how it is watched.

```{toctree}
:caption: Understand
:maxdepth: 2

architecture/generator
architecture/scaleway-contracts
architecture/runtime
```

```{toctree}
:caption: Use
:maxdepth: 2

guides/dynamic-inventory
```

```{toctree}
:caption: Measurement
:maxdepth: 2

mesure/index
```

```{toctree}
:caption: Collection reference
:maxdepth: 2

collections/index
```

```{toctree}
:caption: The generator
:maxdepth: 2

api/index
```

```{toctree}
:caption: The repository
:maxdepth: 1

scorecard
```
