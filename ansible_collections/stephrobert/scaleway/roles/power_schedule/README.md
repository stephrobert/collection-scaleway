# `stephrobert.scaleway.power_schedule`

Bring a named inventory group to a power state.

Reads each machine of the group first, then acts only on those not already where they should be. The action module is a trigger and not a state, so idempotence lives here rather than in the module.

Machines in a transient state are named and left alone. A machine that could not be read fails the run, because a power state nobody could read is not a power state that is fine.

## Using it from your own playbook

```yaml
- ansible.builtin.include_role:
    name: stephrobert.scaleway.power_schedule
  vars:
    scaleway_power_schedule_selector:
      tags: [production, web]
    scaleway_power_schedule_desired_state: "off"
```

`scaleway_power_schedule_group: X` is the shorthand for
`scaleway_power_schedule_selector: {group: X}`. Passing both is refused, because
the answer would depend on the reading order.

## Options

| name | type | default |
|---|---|---|
| `scaleway_power_schedule_selector` | dict | `{}` |
| `scaleway_power_schedule_group` | str | empty |
| `scaleway_power_schedule_desired_state` | str | empty |

Every option is validated by Ansible before the first task, from
`meta/argument_specs.yml`. The descriptions live there, and this page does
not repeat them: two sources of one contract end up disagreeing.

## The playbook and the role are the same operation

`ansible-playbook stephrobert.scaleway.power_schedule` calls this role and passes what
the command line carried. The playbook is the ergonomics, the role is the
operational API, and a test refuses any playbook that reimplements its role.
