# `stephrobert.scaleway.rolling_reboot`

Reboot a named inventory group in batches.

Reboots one batch at a time and waits for each batch to come back before touching the next. A machine that is not running is left alone and named: a rolling reboot that starts machines has done something nobody asked for.

The waiting is observation, never a duration. The action module watches each machine leave C(running) and return, and refuses to conclude when it never saw it change.

## Using it from your own playbook

```yaml
- ansible.builtin.include_role:
    name: stephrobert.scaleway.rolling_reboot
  vars:
    scaleway_rolling_reboot_selector:
      group: scw_tag_production
    scaleway_rolling_reboot_batch_size: 2
```

The waiting is observation, never a duration: each machine is watched leaving
`running` and coming back.

## Options

| name | type | default |
|---|---|---|
| `scaleway_rolling_reboot_selector` | dict | `{}` |
| `scaleway_rolling_reboot_group` | str | empty |
| `scaleway_rolling_reboot_batch_size` | int | `1` |
| `scaleway_rolling_reboot_wait_timeout` | int | `300` |

Every option is validated by Ansible before the first task, from
`meta/argument_specs.yml`. The descriptions live there, and this page does
not repeat them: two sources of one contract end up disagreeing.

## The playbook and the role are the same operation

`ansible-playbook stephrobert.scaleway.rolling_reboot` calls this role and passes what
the command line carried. The playbook is the ergonomics, the role is the
operational API, and a test refuses any playbook that reimplements its role.
