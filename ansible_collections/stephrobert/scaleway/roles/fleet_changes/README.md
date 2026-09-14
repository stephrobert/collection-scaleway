# `stephrobert.scaleway.fleet_changes`

What moved in a Scaleway fleet, aggregated, and quiet when nothing did.

Read-only. It creates nothing and changes nothing, and it compares nothing of
its own either: it includes `fleet_audit` and `fleet_diff` and aggregates what
they left behind. A second comparison written here would drift from the first,
and a test refuses it.

What makes a recurring tool useful is not what it can do: it is that somebody
wants to read it again tomorrow.

## Using it from your own playbook

```yaml
- ansible.builtin.include_role:
    name: stephrobert.scaleway.fleet_changes
  vars:
    scaleway_fleet_changes_snapshot: yesterday.json
    scaleway_fleet_changes_findings: "{{ lookup('file', 'yesterday-findings.json') | from_json }}"
```

```text
Fleet posture changes                 action_required

Infrastructure changes     3
New audit findings         2
Resolved findings          4
Persistent failures        1
Expired exceptions         1
Unmeasured zones           0
Findings not concluded     0
fail     2 (+1)
warn     6 (-3)
```

## No composite score

There is no `Cloud score: 83/100`. It looks good and loses everything: a
composite number cannot be traced back to what moved it. Every line above counts
one named thing, and each is explainable on its own.

## The level is computed, never passed in

| level | what it means |
|---|---|
| `quiet` | nothing new |
| `changed` | something moved, and it is informative |
| `action_required` | a new failing finding, an expired exception, or something that could not be measured |
| `baseline` | nothing was kept from an earlier run, so there is nothing to compare to |

A caller able to force the level could produce a report that calls itself calm
when it is not, which is exactly what a recurring tool must not be able to do.

**A new failing finding is counted, not the delta.** A `fail` that appears while
another resolves leaves the count unchanged, and deciding on the delta would
silence the new one behind its neighbour's good news.

**Something that could not be measured ranks with a new failing finding.** A
zone nobody could read is not good news, and presenting it as a calm fleet is
the green over zero files examined.

**A finding that persists does not demand action every morning.** It was already
reported yesterday, and raising it again at the same rank is exactly the noise
this is meant to remove.

## Two runs on an unchanged fleet

The second one prints one line and stops. That property is played by a test
rather than promised in a page: a rule no check verifies is an intention.

## What you keep, and where

This collection stores nothing. Both sides of the comparison are handed back by
you, from a CI artifact, object storage, a git repository or a file:

```text
scaleway_fleet_changes_snapshot   a file `fleet_report -e output=snapshot` wrote
scaleway_fleet_changes_findings   what `scaleway_fleet_audit_changes.current` held
```

Leaving the snapshot empty does not report "no infrastructure change": it
reports `not compared`, because not having looked is not the same as nothing
having moved.

## Options

| name | type | default |
|---|---|---|
| `scaleway_fleet_changes_zones` | list | none |
| `scaleway_fleet_changes_snapshot` | str | `""` |
| `scaleway_fleet_changes_findings` | list | none |
| `scaleway_fleet_changes_output` | str | `text` |

Every option is validated by Ansible before the first task, from
`meta/argument_specs.yml`. The descriptions live there, and this page does not
repeat them: two sources of one contract end up disagreeing.

**There is no policy option here.** The policy goes on
`scaleway_fleet_audit_policy`, which this role does not touch, so whatever you
set reaches the audit untouched. A second name for one thing is a second name
that ends up disagreeing with the first.

## The playbook and the role are the same operation

`ansible-playbook stephrobert.scaleway.fleet_changes` calls this role and passes
what the command line carried. The playbook is the ergonomics, the role is the
operational API, and a test refuses any playbook that reimplements its role.
