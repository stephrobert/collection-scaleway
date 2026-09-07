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
- [Decision records](adr/index.md): what was decided, when, and what it costs.
  History lives here so the code can say the invariant and nothing else.

```{toctree}
:caption: Understand
:maxdepth: 2

architecture/generator
architecture/scaleway-contracts
architecture/runtime
```

```{toctree}
:caption: Decisions
:maxdepth: 1

adr/index
adr/001-no-operation-is-unknown-in-silence
adr/002-day-2-only
adr/003-a-put-reads-before-it-writes
adr/004-no-sanity-run-without-a-target
adr/005-generated-documentation-behind-a-gate
adr/006-the-emulator-is-a-proof-not-the-proof
adr/007-measured-numbers-live-in-derived-blocks
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
best-practices
```
