# ADR-010. A write is checked, not announced

**Status**: accepted, 7 September 2026. Still in force.

## Context

The chain was already sound:

```text
READ -> COMPARE -> WRITE -> READ
```

The second read is a good decision, and the runtime said why it exists: the API
normalises, completes, and sometimes refuses in silence. But after that read,
the module announced `changed=true` without looking at what it had just read.

A value the API did not apply therefore went unnoticed. It came back on the next
playbook as a `changed=true` that never settles, and nobody connects that symptom
to its cause: the module writes, the API ignores, the module writes again, for
as long as the playbook runs.

## Decision

```text
READ -> NORMALIZE -> COMPARE -> WRITE -> READ -> NORMALIZE -> VERIFY
```

After the second read, every field the playbook asked for is compared against
what the API returns. A divergence fails the module, naming the field, the
requested value and the observed one:

```yaml
failed: true
changed: true
failed_postconditions:
  tags:
    requested: [production, web]
    observed: [production]
```

**`changed` stays true**, and that is the delicate part. The API accepted the
request: the resource moved. A failure that hid `changed` would tell a replayed
playbook that nothing happened while the machine had in fact changed.

The check uses **the same comparison as the outbound decision**
([ADR-009](009-how-a-managed-field-is-compared.md)). Comparing as a set to
decide whether to write and then strictly to verify would fail on an ordering
the first comparison had just accepted.

Two families of field stay out, for two different reasons:

* **secrets**, which the API never returns. Comparing them would compare a value
  to `None` and conclude "not honoured" on every run, which looks like a
  measurement and is not one;
* fields an **override** excludes, with its reason. The case this anticipates is
  an API that applies a field asynchronously: failing on it would fail a correct
  playbook on a delay rather than on an error.

## Consequences

No field is excluded today. Nothing of the sort has been observed, and the
mechanism exists so that the day it is, the answer is an override with a reason
rather than an edit to the runtime under pressure.

The exclusion carries a `reason` like every other decision here. Without it, the
escape hatch would become the convenient way to silence an inconvenient check,
and the check would be decorative.

A module can now fail where it used to succeed. That is the point: the failure
was already there, spread over every future run of the playbook, in a form
nobody could diagnose.

## What this record does not decide

Whether the module should retry. A retry policy depends on the nature of the
operation, and it is its own question.
