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
