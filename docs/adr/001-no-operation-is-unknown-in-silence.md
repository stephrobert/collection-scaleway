# ADR-001. No operation is UNKNOWN in silence

**Status**: accepted, 2 September 2026. Still in force.

## Context

Scaleway's portal added 453 SDK methods and removed 26 over twelve months.
Nobody tracks that from memory, and a collection written by hand is stale before
it ships. The official `scaleway/ansible` repository is the demonstration: sixty
modules written, fifty-five excluded from the build.

The tempting design is a generator that emits what it understands and skips the
rest. It produces a green build on the day it is written, and it is silent
exactly where it should speak: a new operation nobody classified looks identical
to an operation that does not exist.

## Decision

Every operation in the contract produces an entry in the plan. An operation no
rule settles is classified `UNKNOWN`, and `report --strict` exits 2 on it.

Three consequences follow, and none is negotiable:

* **no filtering.** A `continue` inside a parsing loop is almost always an
  operation evaporating.
* **no rule widened to make something fit.** Widening a rule to absorb an
  awkward operation moves the silence rather than removing it.
* **an override carries a reason.** The loader refuses a classification change
  without `reason`, and refuses an unknown field: a typo would otherwise produce
  a silently inert override.

## Consequences

The build goes red when the upstream API moves, which is the point, and it goes
red on the maintainer's schedule rather than on a user's playbook. `mise run
sync:api` followed by `mise run check` is how upstream drift arrives: as a diff,
never as a result that changes on its own.

Exit codes are part of the contract with CI: `0` success, `1` error, `2`
unclassified operation or orphan override.

## What this record does not decide

Whether an operation should be generated at all. That is [ADR-002](002-day-2-only.md).
