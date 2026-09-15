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

## The nodes of a Kubernetes pool, same grammar

```yaml
- ansible.builtin.include_role:
    name: stephrobert.scaleway.rolling_reboot
  vars:
    scaleway_rolling_reboot_selector:
      kind: k8s_node
      group: production
    scaleway_rolling_reboot_batch_size: 1
```

Somebody who knows how to roll through machines knows how to roll through nodes,
and learns nothing new. That is the whole point of having made roles an
operational API.

**`kind` says what is being rolled through, not how it is designated.** It is
not a criterion: the selector still carries exactly one of `group`, `name` or
`tags`, and the same grammar validates both.

**`group` means the pool.** A pool groups nodes the way an inventory group
groups machines. What changes is where the list comes from: the API, not the
inventory, which serves Instance, Elastic Metal and Apple Silicon and nothing
from Kubernetes.

**`tags` is not accepted for nodes.** Measured: `scaleway.k8s.v1.Node` carries
none. `scaleway.k8s.v1.Pool` does, and passing a pool's tags off as its nodes'
would add a hop you cannot see.

**The wait observes what the contract declares.** A node passes through
`rebooting` between two `ready`, where an Instance passes through `stopping`
between two `running`. Neither is a duration, and neither is written in this
role: the action module observes it, and an override carries the mapping.

**A region that did not answer stops the roll.** Rolling through a fleet that is
only partly known is how a roll takes down what it could not see, which is the
same refusal this role already holds for an unreadable machine.

**`ReplaceNode` is not called here, and will not be.** Seen from the node it is
lifecycle, seen from the pool it is not, and this role reboots: replacing a node
destroys and recreates it, which is not the gesture that was asked.

## Options

| name | type | default |
|---|---|---|
| `scaleway_rolling_reboot_selector` | dict | `{}` |
| `scaleway_rolling_reboot_zones` | list | none |
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
