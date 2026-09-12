# `stephrobert.scaleway.fleet_report`

Report on a Scaleway fleet, without touching it.

Instances by state, by zone and by tag, plus the load balancers. It creates nothing and changes nothing, which is what makes it safe to run first on an account you do not know.

It never counts a zone it could not read. A zone that does not answer is named as unmeasured rather than contributing a zero, and the totals are C(null) rather than C(0) when no zone answered at all.

The report is left in C(scaleway_fleet_report_result) so a calling playbook can use it rather than read it.

## Using it from your own playbook

```yaml
- ansible.builtin.include_role:
    name: stephrobert.scaleway.fleet_report
  vars:
    scaleway_fleet_report_zones: [fr-par-1, fr-par-2]

- ansible.builtin.assert:
    that: scaleway_fleet_report_result.zones_unmeasured | length == 0
```

The report is left in `scaleway_fleet_report_result`, so a calling playbook acts
on it rather than reading it off the screen.

## Options

| name | type | default |
|---|---|---|
| `scaleway_fleet_report_zones` | list | none |
| `scaleway_fleet_report_output` | str | `text` |

Every option is validated by Ansible before the first task, from
`meta/argument_specs.yml`. The descriptions live there, and this page does
not repeat them: two sources of one contract end up disagreeing.

## The playbook and the role are the same operation

`ansible-playbook stephrobert.scaleway.fleet_report` calls this role and passes what
the command line carried. The playbook is the ergonomics, the role is the
operational API, and a test refuses any playbook that reimplements its role.
