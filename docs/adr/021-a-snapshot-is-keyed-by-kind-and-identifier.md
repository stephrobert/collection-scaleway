# ADR-021. A snapshot is keyed by kind and identifier, never by name

**Status**: accepted, 13 September 2026. Still in force.

## Context

The collection could say what a fleet holds. It could not say what had changed
since the last look, and that second question is the one that makes somebody run
a tool again tomorrow. Answering it means comparing two reads, and comparing
means choosing a key.

Two candidates existed, and they produce different reports for the same event:

```text
keyed on id     a replaced machine shows up as REMOVED then NEW
keyed on name   the same machine shows up as CHANGED, and the replacement
                disappears from the report
```

Neither is wrong in the abstract, so the choice was measured rather than argued.

**On a real Scaleway account, 13 September 2026, residue verified at zero.** Two
Instances were created with the same name in the same zone. Both creations were
accepted, the API returned two distinct identifiers, and `ListServers` listed
both under that one name. So a name does not identify a machine on this provider.

The same probe measured two further facts the design depends on:

* an Instance identifier survives a power off followed by a power on, unchanged;
* `modification_date` does not move on its own. Three reads over roughly two
  minutes on a machine nobody touched returned the same value. It did move during
  the `starting` to `running` transition, which is a real state change.

The first attempt at that third measurement was wrong, and the mistake is worth
recording: the two reads straddled the `starting` to `running` transition, so the
date moved because the state had genuinely changed. A result that moves does not
say why it moved.

Offline, on the versioned contracts, two more facts:

* every mention of uniqueness in the Instance contract is about an identifier.
  Not one is about a name;
* several resources that carry an identifier carry no `name` field at all, and
  most carry no change date, so a comparison cannot depend on either.

## Decision

**A snapshot resource is keyed on the pair `(kind, id)`.** The name stays in the
snapshot as a readable label and is never part of the key.

Consequences that are not negotiable:

* a resource without a `kind` or without an `id` is **refused**, at the
  normaliser and again at the snapshot. Normalising it anyway would put into a
  snapshot something no comparison can track, and the diff would show it
  appearing and disappearing on every run;
* two resources sharing a key are **refused**, not silently deduplicated.
  Keeping "the last one" would decide on the user's behalf, and the cause of the
  duplication would stay hidden;
* two different products may share an identifier. The key is the pair, so this is
  a valid fleet and not a duplicate;
* resources are **sorted by key**. The order in which zones answer is not a
  property of the fleet, and a snapshot carrying it would make a diff report
  changes nobody made;
* the snapshot carries the zones that did not answer. Nothing measured is not
  nothing found, and a diff computed without that would announce the
  disappearance of a whole fleet the day a zone goes quiet;
* the comparison reads the normalised fields, not a change date, because most
  resources have none.

## Consequences

**A replaced machine reads as a removal and an addition, not as a change.** That
is the truth, and it is also less convenient: somebody watching a fleet where
machines are routinely replaced will see two lines where they expected one. The
alternative hides replacements entirely, which is worse.

**The key depends on the provider keeping identifiers stable, and that is
measured per product rather than assumed.** The contract states it for Instance.
A product whose identifier is not promised stable does not enter a snapshot
without that being written down.

**A snapshot cannot be compared across schema versions.** Reading one whose
`schema_version` is unknown is refused, because comparing two shapes where one
carries an extra field would produce changes that never happened. The cost is a
migration step the day the shape changes.

## What this record does not decide

How the comparison is rendered, and what counts as noise in it, is not decided
here. Nor is where a snapshot is stored: the collection produces it and stores
nothing, and that limit is the decision rather than a first step towards a CMDB.

ADR-020 says why a plan computed from a read is never replayed. The same
reasoning applies to a snapshot: it describes the moment it was captured, and an
operation that acts on it reads the fleet again.
