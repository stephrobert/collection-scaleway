# ADR-002. Day-2 only: Terraform provisions, Ansible operates

**Status**: accepted, 2 September 2026. Still in force.

## Context

The Scaleway API exposes the full lifecycle of every resource, and a generator
that reads the contract can emit a module for each. That is what "complete
coverage" would mean, and it is the wrong target.

Two tools already exist for provisioning, and both do it better than an Ansible
module built on a `state: present/absent` pattern copied from the SDK. The
official collection is built that way, and its modules describe their parameters
as `description: snapshot_id`.

## Decision

```text
Terraform provisions the resources. Ansible operates the resources that exist.
```

An operation that creates, deletes or wires resources has no place here, even
when the generator can produce it. Such operations are classified `LIFECYCLE`
and excluded, with their reason.

This settles every design ambiguity downstream, and it decides the coverage
metric too:

```text
Day-2 coverage = (AUTO + OVERRIDE) / (INFO + ACTION + MANAGE + WORKFLOW)
```

`LIFECYCLE` and `IGNORE` are **not** in the denominator. They are not automated
work, they are discarded work, and the report counts them separately so the gap
stays visible.

## Consequences

The collection is smaller than the API, deliberately, and the report says by how
much and why. A ratio with no denominator is undefined, not zero: `coverage()`
returns `None` and the report prints `n/a`, never `0.0 %`.

A coverage figure is meaningless without naming its denominator, and three
distinct things get confused if they are not named apart:

| stage | source | what it says |
|---|---|---|
| classified | the report, offline | no rule asks for it to be written by hand |
| carried by a module | the generation summary, offline | a module exists and calls it |
| called by the example | `scripts/example_coverage.py`, offline | the playbook names the module |
| played against a target | a run's artefact, `build/example/` | a run actually exercised it |

The last two are not the same: a playbook can name a module that a skipped task
or an unemulated route never exercises.

## What this record does not decide

Whether a managing module may write blindly. That is [ADR-003](003-a-put-reads-before-it-writes.md).
