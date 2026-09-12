# ADR-020. A plan describes the moment it was computed, and is never replayed

**Status**: accepted, 12 September 2026. Still in force.

## Context

Check mode has been honest since 0.6.0: the report distinguishes a rehearsal
from a run, after a defect where `power_schedule` said `acted on` while nothing
had been sent, and an operator read that their machines were off while they were
still running.

What check mode produced was a sentence. A sentence does not travel through an
approval chain, and the obvious next step is the one every infrastructure tool
eventually offers:

```text
pull request
      ↓
plan
      ↓
human approval
      ↓
the same operation, executed
```

The temptation in that shape is to make the last arrow *apply the plan*: to keep
what was computed and replay it, so that what was approved is exactly what runs.
Terraform does that, with a state file and a dependency graph behind it.

This collection has neither, and more importantly it holds a rule that makes the
replay wrong: **the inventory can be served from its cache, and a cached state is
not a state.** Every operation here reads each machine before acting, because a
decision to power a machine off is worth one read. A replay would throw that
away: between the plan and the execution, a machine is locked by a maintenance,
another was stopped by somebody else, a third no longer exists.

## Decision

A plan describes the fleet **as it was read**, at the instant it was computed. It
carries that instant, in `started_at` and `completed_at`.

Executing the operation **reads again**. The plan is not an input to the
execution: it is a rendering of the same structure the operation returns, and
nothing consumes it to decide.

An approval chain therefore approves an *intention*, not a set of instructions.
What runs after the approval is the same operation, which will refuse, skip or
act on what it finds at that moment, and will report what it actually did.

## Consequences

* **What ran can differ from what was approved**, and the operation's own report
  is the only account of what happened. That is a cost, and it is deliberate:
  the alternative is acting on a fleet that has moved;
* a reviewer reading a plan must understand it as a photograph, not a contract.
  The rendered plan says so, in the text itself, rather than leaving it to
  documentation somebody may not read;
* there is no plan file, no plan identifier, and nothing to store. A plan that
  could be stored would invite being replayed;
* a chain that needs the two to match exactly is not served by this collection,
  and should provision with a tool built on a state file.

## What this record does not decide

How an operation reports what it did: that is the result contract, one structure
for every operation, whose fields and refusals are its own subject. This record
only says that the plan is a rendering of it in check mode, and never an input.
