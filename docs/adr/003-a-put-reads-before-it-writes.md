# ADR-003. A managing module reads before it writes

**Status**: accepted, 3 September 2026. Still in force.

## Context

Scaleway's update operations are `PUT`, not `PATCH`. The contract says so
plainly on the Load Balancer's write operations:

> Note that the request type is PUT and not PATCH. You must set all parameters.

Taken literally by a module, that sentence produces two defects at once. A user
who sets one field silently clears every field they did not mention. And a
module that sends its `PUT` on every run reports `changed=true` forever, which
makes `changed` a polite lie and makes the module useless in a handler.

## Decision

A managing module reads the resource, normalises it, compares it with what the
user asked for, and **writes only if there is a difference**. The fields the
user did not give are filled from what was read.

Normalisation happens before comparison: enums, lists, `None`, ordering, nested
structures. Two representations of the same state must compare equal, or the
module writes on every run for a reason no user can see.

In check mode, it compares and reports without writing. The `--diff` output
shows both sides through the same reader, and secret parameters are masked on
both sides, and a mask on one side only turns every run into a spurious difference.

Because the module behaves this way, the contract's sentence is **true of the
API and false of the module**. Publishing it alongside the generator's own
sentence would publish a contradiction, so the generator strips it.

## Consequences

A managing module costs one extra read per run. That is the price of an
idempotent module, and it is not negotiable: a module that always writes is not
idempotent whatever `changed` displays.

Some operations cannot be handled this way, and they are refused explicitly
rather than approximated: complete replacements of a sub-collection or a
sub-object, such as `UpdatePlacementGroupServers`, `UpdateHealthCheck` and
`SetAcls`. [ADR-002](002-day-2-only.md) excludes them anyway.

## What this record does not decide

How the module proves it behaved this way. A second run returning
`changed=false` is the proof, and it runs against the emulator,
[ADR-006](006-the-emulator-is-a-proof-not-the-proof.md).
