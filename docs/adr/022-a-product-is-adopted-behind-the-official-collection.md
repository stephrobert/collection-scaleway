# ADR-022. A product is adopted behind the official collection, not opposite it

**Status**: accepted, 14 September 2026. Still in force.

## Context

ADR-013 settled how a product enters this collection: on the recurring operation
it unblocks, never on the number of modules that can be generated. That rule
answers "is this product worth it" and leaves a second question open, which the
first product to overlap with `scaleway.scaleway` made unavoidable: **where does
this put us relative to the collection Scaleway publishes itself?**

Answering it needed the same treatment every other claim in this repository
gets, because the intuitive answer is wrong by an order of magnitude.

**Measured on 13 and 14 September 2026, on `scaleway.scaleway` 2.7.2 as Galaxy
serves it**, reproducible with `mise run sync:officielle`:

```text
 60  modules written in their repository
  5  modules shipped in the archive
 55  excluded, named one by one in their build_ignore
```

The five shipped are `k8s_cluster`, `k8s_pool`, `secret`, `secret_version` and
`vpc_private_network`, plus an inventory plugin and a secrets lookup. Every one
of the five is built on `state: present/absent`, measured by reading their code
rather than inferred from their names.

Counting their repository rather than their archive gives 60 where the honest
number is 5, and a report carrying 60 reads exactly like a report carrying 5.
This is why the measurement is a script and a versioned file rather than a
sentence in a document.

Two further facts came out of the same measurement:

* thirteen resources are named by both collections, and **none of the thirteen
  is shipped by them**. They are all among their fifty-five excluded files. On
  modules, the two collections do not overlap at all;
* the only real overlap is the inventory plugin. Both serve Instance, Elastic
  Metal and Apple Silicon. Theirs carries six options, ours twenty-six.

What that leaves is a gap rather than a competition. They create things nobody
then operates: somebody creates a cluster with their module and has nothing to
answer "is it healthy, is it drifting, is its version going end of life".

## Decision

A candidate product is adopted **behind** the official collection rather than
opposite it. The adoption criterion, complete, is now:

1. the product improves an operation that already exists, or unblocks a
   remarkable recurring one (ADR-013);
2. **and preferably, the official collection already provisions it**, so our
   operations arrive after theirs rather than in their place;
3. **and we do not take back what it serves well.** What we forbid ourselves is
   named, with its reason, in `CE_QUON_LEUR_LAISSE`.

Criterion 2 is a price, never a refusal. Refusing a product the official
collection ignores would refuse most of their own repository, and both products
this collection already ships fall on that side.

Criterion 3 carries a guard rather than a promise: each thing we forbid
ourselves names what serves it instead, and the measurement is cross-checked
against what their archive actually ships. An abandoned prohibition reads
exactly like a standing decision, and nobody would notice the day their lookup
stops being published.

"They create it, we operate it" is a boundary a user understands in one
sentence, and it does not look like a fork.

The measurement lives in `specs/officielle/`, the way contracts live in
`specs/scaleway/`: their collection will move, and the move arrives as a diff
rather than as a result that changes on its own. Only `mise run sync:officielle`
reaches the network; `mise run admission` reads what was written.

## Consequences

**A product they provision is worth more to us than a product they ignore**,
which is a deliberate inversion of the obvious instinct. It means preferring
ground that is already occupied, on the grounds that occupation by a
provisioning tool is exactly what creates day-2 work.

**The criterion can be wrong about a specific product**, and it is the weaker of
the two: it is preference, not a gate. A product nobody provisions but which
unblocks a remarkable operation still enters on criterion 1 alone.

**The measurement has to be refreshed.** A versioned file that nobody refreshes
ages silently, and this one describes somebody else's release cadence rather
than ours. The admission report says `non mesurée` rather than assuming, so the
failure mode is a visible gap and not a plausible number.

**We give up ground we could take.** `AccessSecretVersion` is within reach and
we will not write it, because their lookup does exactly that and a second path
to the same value doubles the surface a secret can leak through.

## What this record does not decide

ADR-013 keeps the primary criterion, and this record only adds to it.

Which product comes next is not decided here: that is the milestone's business,
and the measurement above is what it argues from. Nor does this record decide
anything about the inventory plugin, where the two collections genuinely meet;
what we take from theirs, and what we do not, is settled issue by issue.
