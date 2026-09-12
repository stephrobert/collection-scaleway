# collection-scaleway

**This site is the complete documentation for `stephrobert.scaleway`.** Use it
to operate the collection, to understand how it is generated from Scaleway's
versioned API contracts, and to contribute to the generator safely. Galaxy
remains the distribution channel; GitHub holds the code and the issues.

Two paths, and they do not need each other.

**[Use the collection](guides/using-the-collection.md)**
: Install it, authenticate, list your resources, run a Day-2 operation, and
  check that a second run reports no change. The
  [task playbooks](guides/shipped-playbooks.md), the
  [dynamic inventory](guides/dynamic-inventory.md) and the
  [module reference](guides/module-reference.md) continue from there.

**[Build the collection](architecture/generator.md)**
: The pipeline from contract to module, the [runtime](architecture/runtime.md),
  the [contracts](architecture/scaleway-contracts.md) and their measured limits,
  and the [decisions](adr/index.md) that were taken with what each of them
  costs.

The boundary that settles every design ambiguity:

> Terraform provisions resources. Ansible operates existing resources.

```{note}
This repository does not contain a hand-written Ansible collection: it contains
the **generator that writes it**. We do not follow the API by hand, we measure
it. Scaleway added 453 SDK methods and removed 26 in twelve months: a
hand-written collection is stale before it is published.
```

```{toctree}
:caption: Use the collection
:maxdepth: 2

guides/quickstart
guides/using-the-collection
guides/shipped-playbooks
guides/scheduling
guides/dynamic-inventory
```

```{toctree}
:caption: Reference
:maxdepth: 2

guides/module-reference
collections/stephrobert/scaleway/index
```

```{toctree}
:caption: Understand the project
:maxdepth: 2

architecture/generator
architecture/runtime
architecture/scaleway-contracts
mesure/index
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
adr/008-a-constraint-is-translated-or-named
adr/009-how-a-managed-field-is-compared
adr/010-postconditions-are-checked-not-announced
adr/011-a-product-is-admitted-not-merely-added
adr/012-an-explicit-null-is-refused-never-ignored
adr/013-when-a-module-appeared-is-recorded-not-computed
adr/014-the-runtime-owns-its-http-transport
adr/015-a-claim-about-the-real-api-is-a-recorded-exchange
adr/016-a-clearable-field-is-cleared-with-the-empty-value
adr/017-the-launcher-removes-what-blocks-its-own-destruction
adr/018-a-retry-policy-belongs-to-the-operation
adr/019-a-name-filter-narrows-a-listing
adr/020-a-plan-describes-the-moment-it-was-computed
```

```{toctree}
:caption: Generator internals
:maxdepth: 2

api/index
```

```{toctree}
:caption: Project quality
:maxdepth: 1

scorecard
best-practices
```

```{toctree}
:caption: Collection index
:maxdepth: 1
:hidden:

collections/index
```
