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

## When the answer is "yes, but that one is on purpose"

A policy that is actually used meets the case within a week: this bastion *must*
carry a public address. If the only way out is to delete the rule, the rule is
lost for the whole fleet in order to excuse one machine, and the system loses
its value on the day it would be worth the most.

```yaml
scaleway_fleet_audit_policy:
  rules:
    public_ip:
      severity: fail
  exceptions:
    - rule: public_ip
      reason: entry point for the operators, reviewed with security
      owner: platform-team
      expires_at: "2026-12-31"
      selector:
        id: b20294e8-d0b9-471e-a78f-bbce79e7ca74
```

**An exception changes a status, it never deletes a finding.** The finding stays
in `scaleway_fleet_audit_findings` with `status: suppressed` and the
`suppressed_by` that covers it, and it is counted apart in
`scaleway_fleet_audit_suppressed`. A finding that was erased is a problem nobody
knows about any more, which is exactly what writing the exception, rather than
removing the rule, is meant to avoid.

`reason`, `owner` and `expires_at` are each required, and each stops one thing:
without a reason it is a rule quietly switched off, without an owner there is
nobody to ask whether it still holds, and without an expiry it is not an
exception but a change to the policy written in the wrong place.

The `selector` names exactly one of `id`, `name` or `tags` (with
`match: all|any`). Two criteria ask two questions and the answer would depend on
the order they are read in. A `name` carried by two resources is refused rather
than resolved: two machines can share a name in one zone, so covering both would
excuse a resource nobody named.

**An expired exception becomes a finding of severity `fail`, not a refusal.**
Refusing the whole policy over one stale line would switch off the audit on the
day an exception expires, which is the opposite of what you want. It comes out
in `scaleway_fleet_audit_expired_exceptions`, and it is what makes the run fail.

An exception that matches nothing is reported in
`scaleway_fleet_audit_exceptions_without_target` and nothing else: an exception
left behind by a destroyed machine is housekeeping, not a policy error.

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
