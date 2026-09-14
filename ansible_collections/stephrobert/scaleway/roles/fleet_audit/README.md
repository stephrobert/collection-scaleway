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

## The rules, and what each one reads

Every rule names the field it judges, and that field comes from the common shape
rather than from a product's own vocabulary. Adding a product adds a normaliser,
never a line inside a rule.

| rule | it reads | it answers |
|---|---|---|
| `required_tags` | `tags` | which machine is missing an owner |
| `allowed_zones` | `zone` | what is running where it should not |
| `public_ip` | `public_addresses` | what is exposed |
| `stopped_since` | `state` | what has been off long enough to question |
| `planned_maintenance` | `planned_maintenance` | which machine has a maintenance window coming |
| `end_of_service` | `end_of_service` | which one runs on a type that is being retired |
| `required_actions` | `allowed_actions` | what you can still do to it, in its current state |
| `upgrade_available` | `upgrade_available` | which cluster is behind |
| `expires_within` | `expires_at` | which certificate, or which cluster's version, expires soon |
| `version_drift` | `versions_behind` | how far behind, counted rather than guessed |
| `unhealthy_conditions` | `health_conditions` | which node is under pressure |

## Which products it reads

```yaml
scaleway_fleet_audit_products:
  - instance
  - k8s_cluster
  - k8s_node
  - lb_certificate
```

Instance alone by default, which is what this audit read before the others
existed. Each product is a family of API calls on a billed account, so it is
never read for you.

**A rule judging a field no read product carries fails the run**, naming the
rule, the field, and which products carry it. A rule that judges nothing is a
silence, not a compliance: it produces a green report where nobody checked
anything, and nothing in that report would say so.

**A field a product does not have is not an empty field.** A cluster has no
allowed actions and a machine has no minor version to catch up on; the rule
skips those resources rather than calling them compliant, because counting them
as compliant would inflate the pass count with resources nobody looked at.

**Kubernetes is regional where Instance is zonal**, and the regions are derived
from the zones you asked for rather than listed a second time. A region that did
not answer is named with the product it did not answer for: one that answers for
clusters and not for versions is not the same situation as a silent one.

## One thing that is measured and not contracted

`scaleway.k8s.v1.Node` declares neither `conditions` nor `public_ip_v4` nor
`public_ip_v6`, and the real API returns all three, measured on 14 September
2026. `unhealthy_conditions` reads a field nothing watches: the day upstream
stops returning it, no golden goes red and no drift report says so.

So its **absence means unmeasured, never healthy**. A rule reading absence as
good news would report a healthy fleet over zero fields read, and the report
would be perfectly plausible.

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

## What is new, what persists, what is resolved

Run daily, an audit shows the same warnings every morning, and people stop
reading it by the third morning. That is the failure mode of a recurring tool,
and it is more dangerous than an outage because it does not show.

Hand back what the previous run found, and the role sorts this run's findings
into three sets computed from their stable identities, with nothing guessed:

```yaml
- ansible.builtin.include_role:
    name: stephrobert.scaleway.fleet_audit
  vars:
    scaleway_fleet_audit_previous: "{{ lookup('file', 'yesterday.json') | from_json }}"
```

```text
Fleet posture changes

NEW
  FAIL instance/db-01  public_ip
PERSISTING
  WARN instance/web-03  required_tags
       first seen 2026-09-10T06:00:00Z
RESOLVED
  instance/web-04  required_tags
level: action_required
```

**A finding that vanished is not a finding that was resolved.** A zone that did
not answer makes everything it held disappear, and announcing that as resolved
tells somebody their problem is fixed when nobody looked. Those come out under
`NOT CONCLUDED`, with which of the two cases it is.

**A suppressed finding is not resolved either.** An exception changes a status,
it does not make the problem go away, so it stays in `persisting` with its
status.

**This collection keeps no history.** `first_seen` is stamped on a new finding
and carried over on a persisting one, so the date goes back as far as you kept
your reports. Where you keep them is yours to decide. When a kept report carries
none, the report says the date is unknown rather than inventing one, and there
is no "since the last run" field at all: nothing here can derive when the
previous run happened.

`scaleway_fleet_audit_level` is computed, never passed in: `quiet` when nothing
is new, `changed` when something moved, `action_required` on a new failing
finding or on anything that could not be concluded, and `baseline` on a first
run, which is neither calm nor alarming because there is nothing to compare to.

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
| `scaleway_fleet_audit_products` | list | `[instance]` |
| `scaleway_fleet_audit_output` | str | `text` |
| `scaleway_fleet_audit_policy` | dict | none |

Every option is validated by Ansible before the first task, from
`meta/argument_specs.yml`. The descriptions live there, and this page does
not repeat them: two sources of one contract end up disagreeing.

## The playbook and the role are the same operation

`ansible-playbook stephrobert.scaleway.fleet_audit` calls this role and passes what
the command line carried. The playbook is the ergonomics, the role is the
operational API, and a test refuses any playbook that reimplements its role.
