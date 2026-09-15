# `stephrobert.scaleway.fleet_diff`

Say what changed between two observed snapshots of a fleet.

A report that announces the same count every morning stops being read by the third morning. The useful question is why there are two more today, and answering it takes two snapshots rather than one.

It creates nothing and changes nothing.

## Using it from your own playbook

```yaml
- ansible.builtin.include_role:
    name: stephrobert.scaleway.fleet_diff
  vars:
    scaleway_fleet_diff_baseline: yesterday.json

- ansible.builtin.assert:
    that: scaleway_fleet_diff_level != 'action_required'
```

The comparison is left in `scaleway_fleet_diff_result` and the level it earned in
`scaleway_fleet_diff_level`, so a calling playbook acts on them rather than
reading them off the screen.

## Where the baseline comes from

This collection stores nothing. A snapshot is produced by `fleet_report` and kept
wherever you want it: a CI artifact, object storage, a git repository, a file.

```bash
ansible-playbook stephrobert.scaleway.fleet_report -e snapshot_to=today.json
ansible-playbook stephrobert.scaleway.fleet_diff -e baseline=today.json
```

The playbook writes the file, not the role: redirecting the playbook's output
would capture Ansible's own decoration rather than JSON.

## A zone is only compared when both snapshots measured it

This is the defect the role exists not to commit. A zone that did not answer, and
a zone that was simply not read this time, would both make everything it holds
look removed, and the report would be perfectly plausible.

Such scopes come out under `scopes_not_compared`, each with which of the two cases
it is, and the resources they hold are counted rather than silently dropped.

## Three levels, and only one of them asks you to read

```text
quiet             nothing new
changed           something appeared, went away or moved
action_required   something could not be measured
```

The level is computed, never passed in. A caller able to force it could produce a
report that calls itself calm when it is not, and that is the one line this
report may not write.

A timestamp that moved on its own does not make a change: it is a witness rather
than a property, and a diff line showing only a timestamp gives nobody an action.
Those resources are counted under `changed_outside_this_shape`, neither hidden
nor presented as actionable.

## Options

| name | type | default |
|---|---|---|
| `scaleway_fleet_diff_baseline` | str | none, required |
| `scaleway_fleet_diff_current` | str | empty, meaning read now |
| `scaleway_fleet_diff_zones` | list | the zones the contract declares |
| `scaleway_fleet_diff_output` | str | `text` |

Every option is validated by Ansible before the first task, from
`meta/argument_specs.yml`. The descriptions live there, and this page does
not repeat them: two sources of one contract end up disagreeing.

## The playbook and the role are the same operation

`ansible-playbook stephrobert.scaleway.fleet_diff` calls this role and passes what
the command line carried. The playbook is the ergonomics, the role is the
operational API, and a test refuses any playbook that reimplements its role.
