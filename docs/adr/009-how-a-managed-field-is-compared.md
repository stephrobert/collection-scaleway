# ADR-009. How a managed field is compared, and who decides

**Status**: accepted, 7 September 2026. Still in force.

## Context

A managing module reads the resource, compares, and writes only the difference
([ADR-003](003-a-put-reads-before-it-writes.md)). The comparison was strict
equality, and the runtime said so about itself:

> the comparison is strict. A field the API reorders or normalises will report
> `changed` on every run.

```text
requested          returned by the API
tags:              tags:
  - production       - web
  - web              - production

strict equality  -> changed, every run
set comparison   -> unchanged
```

A module that reports `changed` on every run is not idempotent, whatever
`changed` displays, and it cannot be used in a handler. The fault is worse than
noise: it teaches the reader to ignore `changed`.

## Decision

Every managed parameter carries a comparison strategy, computed in the **Ansible
model** and applied by the runtime.

**The type decides what it can. An override decides the rest. Nothing is
guessed.** Measured on both vendored contracts: no array declares `uniqueItems`,
and no array description mentions ordering. Deducing `set` from the shape of an
array would therefore be a guess, and rule 3 of this repository forbids it.

| source | strategies |
|---|---|
| the IR type | `scalar`, `ordered_list` for an array, `mapping` for an object |
| an override, with its reason | `set`, `normalized_string`, `object_id`, `normalized_object` |

`ordered_list` is a **fallback**, not a decision. Adopting `set` by default
would silence a `changed` that may be right, and a module that hides a real
change is worse than one that announces an extra.

An override may not restate what the type already decides: two sources for one
decision diverge, and nothing would say so.

The runtime **fails** on a strategy it does not know rather than falling back to
strict equality. A silent fallback would give a module that believes it compares
one way and compares another, which is the original fault made invisible.

## Consequences

The generation summary publishes how many parameters fall under each strategy.
That is what makes the fallback visible: until someone counts them, nobody
wonders whether one of them deserves `set`.

No `set` override is posed on the real contracts yet, and that is deliberate.
Nothing has been observed that would justify one: Scaleway's tags come from a
protobuf repeated field, which preserves order, so posing `set` would be a guess
in the other direction. `mise run example:reel` against the real account is what
would settle it, and the mechanism is ready for the day it does.

A `set` comparison sorts rather than building a real set. A real set would call
`[a, a, b]` and `[a, b]` equal, and they are not: one carries two tags, the
other one.

## What this record does not decide

Whether the write actually produced the requested state. Comparing before
writing says what to send; checking afterwards is a different question, and it
needs this one answered first.
