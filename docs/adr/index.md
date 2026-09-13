# Architecture decision records

A decision record says what was decided, when, against what alternatives, and
what it costs. It is **historical by construction**: it carries a date, and it
is never rewritten to match today. When a decision is reversed, a new record
supersedes the old one and says so; the old one stays.

## Why this directory exists

The comments in this repository explain a great deal, and that is what makes
them worth reading: *"we had found that…"*, *"at the start there were fifteen
modules…"*. The reasoning carries across; **the number goes stale**. Three
docstrings still said "575 tests" when there were six hundred and thirteen;
another said "46 modules" when the collection publishes fifty. None was wrong
the day it was written.

So the rule, and `mise run histoire` is its executable form:

> A number counting things in this repository does not belong in a sentence.
> If it is true, something must go red when it changes: an assertion, a
> golden, a derived block. If it is history, it belongs in a decision record,
> which carries its date.

Code says the **current** invariant. This directory says what happened.

## The records

| record | decision |
|---|---|
| [ADR-001](001-no-operation-is-unknown-in-silence.md) | No operation disappears; what no rule settles is `UNKNOWN` and fails the build |
| [ADR-002](002-day-2-only.md) | Terraform provisions, Ansible operates: no create, no delete, no wiring |
| [ADR-003](003-a-put-reads-before-it-writes.md) | A managing module reads the resource, computes the difference, and writes only that |
| [ADR-004](004-no-sanity-run-without-a-target.md) | `ansible-test sanity` that examined zero files is a failure, not a pass |
| [ADR-005](005-generated-documentation-behind-a-gate.md) | Generated documentation is refused, not merely reported, when it is unusable |
| [ADR-006](006-the-emulator-is-a-proof-not-the-proof.md) | The local emulator proves the shape of a run, never the real cloud |
| [ADR-007](007-measured-numbers-live-in-derived-blocks.md) | A measured number is derived, an assertion, or dated history, never a sentence |
| [ADR-008](008-a-constraint-is-translated-or-named.md) | A contract constraint is translated, or counted, or measured absent, never guessed |
| [ADR-009](009-how-a-managed-field-is-compared.md) | The type decides the comparison it can, an override decides the rest, nothing is guessed |
| [ADR-010](010-postconditions-are-checked-not-announced.md) | After writing, what was asked is compared with what is observed, and a gap fails the module |
| [ADR-011](011-a-product-is-admitted-not-merely-added.md) | A product passes a gate before entering the index, and enters with its price known |
| [ADR-012](012-an-explicit-null-is-refused-never-ignored.md) | An explicit `null` on a clearable field fails the module, and never passes for an omitted option (superseded by ADR-016) |
| [ADR-013](013-when-a-module-appeared-is-recorded-not-computed.md) | When a module, option or return appeared is read from a journal, never from the current version |
| [ADR-014](014-the-runtime-owns-its-http-transport.md) | The runtime composes its own HTTP request, and no private attribute of a third-party library is shipped |
| [ADR-015](015-a-claim-about-the-real-api-is-a-recorded-exchange.md) | A claim about the real API is a recorded exchange, not a green assertion |
| [ADR-016](016-a-clearable-field-is-cleared-with-the-empty-value.md) | A clearable field is cleared with the empty value of its type, and an explicit `null` is refused with that value named |
| [ADR-017](017-the-launcher-removes-what-blocks-its-own-destruction.md) | On a failed destruction the launcher removes what blocks it, once, only within the run's own platform, and says what it removed |
| [ADR-018](018-a-retry-policy-belongs-to-the-operation.md) | A retry policy belongs to the operation: a read replays, a write only when the server says it did nothing, an action never |
| [ADR-019](019-a-name-filter-narrows-a-listing.md) | An API name filter narrows a listing, it never selects: the exact comparison is local, and two matches refuse |
| [ADR-020](020-a-plan-describes-the-moment-it-was-computed.md) | A plan describes the fleet as it was read, and is never replayed: the execution reads again |
| [ADR-021](021-a-snapshot-is-keyed-by-kind-and-identifier.md) | A snapshot resource is keyed on its kind and its identifier, never on its name: two machines can carry one name in a zone |
