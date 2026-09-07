# ADR-007. A measured number is derived, never typed

**Status**: accepted, 6 September 2026. Still in force.

## Context

This repository's thesis is that you measure instead of assuming. Its own
documents did not follow it.

The README announced 366 unit tests and 46 mutations. Measured at the same
instant: 420 tests and 73 mutations. A commit message announced 373 for 376. A
counter read only `instance.v1` and announced "25 modules written out of 30
planned" above a list of 46 lines, and the control that exists to refuse a
stale counter declared it conformant, because it compared the block to what the
script produced, and the script produced the wrong number.

Then the rule was applied to the README alone, and an audit of 0.3.0 found eight
false counters elsewhere in `docs/`: "41 Day-2 candidates" where the measurement
says 40, "40 AUTO" where it says 39, "out of 46 modules" where the collection
carries 50, "575 unit tests" and "49 unit tests" frozen on the day the sentence
was written.

Two scripts carried the same table of these findings in their docstrings, with
**different** numbers in each: 595/158 in one, 577/151 in the other. Neither was
wrong the day it was written.

## Decision

Every measured number in a published document lives inside a **derived block**,
written by `scripts/readme_counters.py` and refused by `mise run readme:check`
when it no longer matches the measurement. `scripts/chiffres.py` refuses a
measured counter written outside such a block, in every watched document and not
only the README.

A derived block must be computable **offline**. A number that depends on a run,
what a real target actually played, does not go in one; `mise run
coverage:example` publishes it separately, and says "no run recorded" rather than
"0 %" when there is none.

Numbers about the past, meaning what a document used to say, what an audit found, how
many defects a first fuzzing pass turned up, go in a decision record, which
carries its date. `mise run histoire` refuses them in a code comment.

## Consequences

Three places may hold a number, and each says something different: an assertion,
which goes red when the fact changes; a derived block, regenerated from the
measurement; a decision record, which is dated and never updated. A sentence in
a comment is none of the three.

Regenerating a derived block without reading its diff cancels the whole
mechanism, in exactly the way regenerating a golden without reading its diff
does.

## What this record does not decide

Whether the measured thing is worth measuring. That is the report's business,
and [ADR-002](002-day-2-only.md) names its denominator.
