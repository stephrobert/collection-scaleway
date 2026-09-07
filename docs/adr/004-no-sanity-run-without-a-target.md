# ADR-004. An `ansible-test sanity` that examined nothing is a failure

**Status**: accepted, 1 September 2026. Still in force.

## Context

The first version of this repository kept the collection at the root and
assembled a copy elsewhere for `ansible-test`. `ansible-test sanity` ran, exited
0, and examined **zero files**. The build was green, and it measured nothing.

The failure mode is general, and this repository has hit it more than once: a
control whose scope silently collapses to nothing reports the same green as a
control that passed. Nothing was measured is not nothing was wrong.

## Decision

Three rules, each aimed at that failure:

* **the collection lives where Ansible requires it**, under
  `ansible_collections/stephrobert/scaleway/`. `ansible-test`, `antsibull-docs`
  and `ansible-playbook` work in place, with no assembled copy. The price is
  that both the path and `galaxy.yml` declare the namespace and Ansible reads
  both, so `load_collection` **requires them to agree**.
* **a control that examined nothing fails.** `scripts/sanity.py` refuses a run
  with no target; the package check refuses an archive with no module and a
  `plugins/` directory that exists and holds nothing; `mise run histoire`
  refuses to run over an empty file list.
* **a control that cannot say where it strikes fails.** The falsification
  harness refuses an ambiguous pattern rather than mutating the first match: a
  mutation that does not know where it strikes proves nothing.

## Consequences

Every gate in this repository states the size of what it examined, and the
number is read from the run rather than from a constant. `50 module(s)
interrogé(s)` is the useful half of the message; `ok` alone is not.

`mise run falsify` is the general form of the same rule applied to guards: a
guard whose removal leaves every test green is a comment. It runs after any
added guard, validation or refusal.

## What this record does not decide

What makes generated documentation acceptable. That is
[ADR-005](005-generated-documentation-behind-a-gate.md).
