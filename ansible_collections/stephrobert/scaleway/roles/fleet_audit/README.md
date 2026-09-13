# `stephrobert.scaleway.fleet_audit`

Judge a Scaleway fleet against a policy.

Read-only. It creates nothing, changes nothing and reboots nothing: an audit that corrected things would cross the boundary this collection exists to hold, where Terraform provisions and Ansible operates.

Every rule names the field it reads, and a rule the evaluation cannot settle is refused rather than reported as compliant. A zone that did not answer is named as unmeasured, never counted as conforming.

The run fails when a rule of severity C(fail) is broken, so a schedule that never fails visibly is not what you end up with.

## Using it from your own playbook

```yaml
- ansible.builtin.include_role:
    name: stephrobert.scaleway.fleet_audit
  vars:
    scaleway_fleet_audit_policy:
      rules:
        required_tags:
          severity: fail
          keys: [owner, environment]
```

The findings are left in `scaleway_fleet_audit_findings`, so a pipeline opens a
ticket rather than reading a report. The shipped policy is a starting point made
only of warnings; replacing it is the point.

## Each finding keeps its identity between runs

A finding carries an `id` that is recomputed on every run and comes out the same
tomorrow for the same problem on the same resource:

```text
public_ip:instance:b20294e8-d0b9-471e-a78f-bbce79e7ca74
```

Nothing random, nothing timestamped, or everything would be new each morning.

**It is built on the resource identifier, never on its name.** Two machines can
carry the same name in one zone, and the API then returns two distinct
identifiers for it; an identity built on names would stick one machine's finding
onto another, and the next day's report would say "resolved" for the wrong one.

A renamed rule produces different identities, and that is intended: it is no
longer the same rule, so it is no longer the same finding.

The field a rule judges is not part of the identity. Each rule judges exactly
one field, so the field is derivable from the rule and distinguishes nothing more
than the rule already does. It stays on the finding as information.

## Options

| name | type | default |
|---|---|---|
| `scaleway_fleet_audit_zones` | list | none |
| `scaleway_fleet_audit_output` | str | `text` |
| `scaleway_fleet_audit_policy` | dict | none |

Every option is validated by Ansible before the first task, from
`meta/argument_specs.yml`. The descriptions live there, and this page does
not repeat them: two sources of one contract end up disagreeing.

## The playbook and the role are the same operation

`ansible-playbook stephrobert.scaleway.fleet_audit` calls this role and passes what
the command line carried. The playbook is the ergonomics, the role is the
operational API, and a test refuses any playbook that reimplements its role.
