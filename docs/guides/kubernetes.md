# Operating a Kapsule cluster

Scaleway's own collection creates Kubernetes clusters. This one operates the
ones that exist: it reads them, judges them, changes their settings and reboots
their nodes, and it never creates or destroys one.

That boundary is the whole reason this page exists, and it is worth one sentence
before anything else:

```text
They create it. We operate it.
```

If you are looking for `state: present` on a cluster, you want
`scaleway.scaleway.k8s_cluster`, and this page will not argue with that.

## What you came here to do

| what you need | where |
|---|---|
| see what exists, without changing anything | [Read before you touch anything](#read-before-you-touch-anything) |
| find out what is drifting, expiring or unhealthy | [Audit a version before it audits you](#audit-a-version-before-it-audits-you) |
| change a cluster's or a pool's settings | [Change what a cluster or a pool holds](#change-what-a-cluster-or-a-pool-holds) |
| move to a newer Kubernetes version | [Upgrade a version](#upgrade-a-version) |
| restart nodes without dropping the service | [Reboot nodes in waves](#reboot-nodes-in-waves) |
| control who reaches the API server | [Control-plane ACLs](#control-plane-acls) |
| rotate credentials | [Rotate the admin token](#rotate-the-admin-token) |
| know what this will never do | [What is deliberately not supported](#what-is-deliberately-not-supported) |
| know what has actually been run | [What has actually run against the real cloud](#what-has-actually-run-against-the-real-cloud) |

## Why there is a second collection at all

`scaleway.scaleway` ships `k8s_cluster` and `k8s_pool`, both built on
`state: present/absent`. They provision well. What they do not answer is the
question you have the morning after:

> is this cluster healthy, is it drifting, is its version going end of life,
> and can I reboot its nodes without taking the service down?

[ADR-022](../adr/022-a-product-is-adopted-behind-the-official-collection.md)
carries the measurement of what that collection actually ships, on the date it
was taken, and the decision that follows from it. The short version: on modules,
the two collections do not overlap at all.

## Read before you touch anything

Everything here is read-only, and check mode changes nothing anywhere in this
collection.

```yaml
- name: What clusters exist in this region
  stephrobert.scaleway.k8s_cluster_info:
    region: fr-par
  register: clusters

- name: One cluster in particular
  stephrobert.scaleway.k8s_cluster_info:
    region: fr-par
    cluster_id: "{{ cluster }}"

- name: The pools it holds
  stephrobert.scaleway.k8s_cluster_pool_info:
    region: fr-par
    cluster_id: "{{ cluster }}"

- name: The nodes those pools hold
  stephrobert.scaleway.k8s_cluster_node_info:
    region: fr-par
    cluster_id: "{{ cluster }}"
```

**Kubernetes is regional where Instance is zonal.** `fr-par` is a region and
`fr-par-1` a zone; the API rejects one where it wants the other, and nothing in
the string tells them apart. Everything in this collection that compares two
reads carries the type beside the name for that reason.

## Audit a version before it audits you

Scaleway places the tracking of deprecations and upgrades on the customer side
of its shared responsibility model. `fleet_audit` gives you somewhere to put
that.

```yaml
- name: Audit the clusters and their nodes
  ansible.builtin.include_role:
    name: stephrobert.scaleway.fleet_audit
  vars:
    scaleway_fleet_audit_products:
      - k8s_cluster
      - k8s_node
    scaleway_fleet_audit_policy:
      rules:
        version_drift:
          severity: warn
          max_minor_behind: 1
        expires_within:
          severity: fail
          days: 90
        upgrade_available:
          severity: warn
        unhealthy_conditions:
          severity: fail
```

`version_drift` counts, it does not estimate: the catalogue of offered versions
is read, and the join happens at the seam rather than inside a rule.
`expires_within` answers the same question for a certificate and for the version
a cluster runs, because it is the same question.

Three refusals are worth knowing before you rely on the green:

**A drift that cannot be counted is not "up to date".** A cluster whose version
is not in the catalogue, or is a major apart from the newest offered, comes out
as not concluded. A major apart is a different question, and counting it in the
same number would make it disappear behind a negative.

**A scope that did not answer is never compliant.** It is named as unmeasured,
with its type, and it makes the run ask for action.

**Node health conditions are measured and not contracted.** The contract
declares neither `conditions` nor `public_ip_v4` nor `public_ip_v6`, and the
real API returns all three, measured 14 September 2026. A rule reading their
absence as good news would report a healthy fleet over zero fields read, so
their absence means unmeasured and never healthy.

## Change what a cluster or a pool holds

`k8s_cluster` and `k8s_pool` read, compare, and write only what differs. Running
them twice reports `changed` then `ok`.

```yaml
- name: Tag the cluster
  stephrobert.scaleway.k8s_cluster:
    region: fr-par
    cluster_id: "{{ cluster }}"
    tags: [env=prod, team=platform]

- name: Tag the pool
  stephrobert.scaleway.k8s_pool:
    region: fr-par
    pool_id: "{{ pool }}"
    tags: [role=workers]
```

**What is proven and what is not.** The table at the end of this page says both
modules reached the real API, which proves the MANAGE path runs: it reads, it
compares, it sends one write. It does not prove that every option compares
correctly. `autoscaler_config`, `auto_upgrade`, `admission_plugins` and
`open_id_connect_config` on the cluster, `autoscaling`, `autohealing`,
`kubelet_args` and `upgrade_policy` on the pool are exactly where an API injects
defaults, normalises and reorders, and that is where idempotence breaks without
anything looking wrong. Issue #278 tracks measuring them field by field, and
until it closes, run these with `--check` first on anything you care about.

**Renaming a cluster is not a cosmetic change.** Scaleway redeploys the control
plane, which can interrupt workloads for several minutes. Do not do it during
peak hours because the parameter looked harmless.

**Labels and taints are not here yet.** `SetPoolLabels`, `SetPoolTaints` and
`SetPoolStartupTaints` are classified and planned, and the generator sets them
aside with a measured reason: the resource derived from the last path segment
names the action rather than the thing it acts on. `GetPool` already returns
them, so the read exists; issue #277 carries the work.

## Upgrade a version

The audit finds the drift; this is what closes it. The two modules exist and
neither is called by any example, for a reason the last section of this page
measures rather than asserts.

```yaml
- name: Upgrade the control plane, and nothing else
  stephrobert.scaleway.k8s_cluster_upgrade_action:
    region: fr-par
    cluster_id: "{{ cluster }}"
    version: "1.37.0"
    upgrade_pools: false

- name: Upgrade one pool, which replaces its nodes
  stephrobert.scaleway.k8s_pool_upgrade_action:
    region: fr-par
    pool_id: "{{ pool }}"
    version: "1.37.0"
```

**Upgrading a pool drains and replaces its nodes.** That is the contract's own
wording, not a caution added here: the nodes you have are not upgraded in place,
they are drained and replaced, and everything running on them is rescheduled.
Plan it like a rolling reboot with a longer tail, not like a setting change.

**`upgrade_pools: true` does that to every pool at once.** It is one boolean on
the cluster call, and it is the difference between upgrading a control plane and
replacing every node you have. Left explicit above for that reason.

**The version is constrained, and the API decides.** A cluster accepts a higher
patch of its current minor, or the next minor, and nothing further; a pool only
accepts a version that matches its cluster's. Read
`k8s_cluster_available_version_info` before choosing rather than guessing from
the catalogue of all versions.

**Run it in check mode first.** An action module in check mode sends nothing and
reports what it would trigger, without even building a client.

## Reboot nodes in waves

The same grammar as machines, because somebody who knows one knows the other:

```yaml
- name: Roll through one pool's nodes
  ansible.builtin.include_role:
    name: stephrobert.scaleway.rolling_reboot
  vars:
    scaleway_rolling_reboot_selector:
      kind: k8s_node
      group: production
    scaleway_rolling_reboot_batch_size: 1
```

`kind` says what is being rolled through, not how it is designated: the selector
still carries exactly one criterion. For nodes, `group` means the **pool**, which
groups nodes the way an inventory group groups machines, and the list comes from
the API rather than the inventory, which serves no Kubernetes.

**The wait observes, it never sleeps.** The contract declares `rebooting`
between two `ready`, and the module watches the node leave its state before
accepting that it came back. A batch that does not come back stops the roll and
names what was left to do.

**Raise the timeout for nodes.** The default is 300 seconds, inherited from
machines, and a machine only has to reboot. A node is drained, rebooted, and
then has to **rejoin the cluster**, and that last part is what overruns. Measured
across two real runs on the same day: one node came back inside the default, the
next did not. Pass `scaleway_rolling_reboot_wait_timeout` generously; a roll that
gives up on a node that was going to return has to be restarted by hand, and one
that waits a little longer costs nothing.

**The drain is Scaleway's, not ours.** `RebootNode` drains the node and
reschedules its Pods; this collection never calls `kubectl` and never will. But
the operation succeeding depends on available capacity and on your workloads'
constraints: pod disruption budgets and cluster topology stay yours.

**`tags` is not accepted for nodes.** Measured: `scaleway.k8s.v1.Node` carries
none. Pools do, and passing a pool's tags off as its nodes' would add a hop you
cannot see.

## Control-plane ACLs

```yaml
- name: The ACLs currently in force
  stephrobert.scaleway.k8s_cluster_acl_info:
    region: fr-par
    cluster_id: "{{ cluster }}"

- name: Allow the operator network in
  stephrobert.scaleway.k8s_cluster_acl_action:
    region: fr-par
    cluster_id: "{{ cluster }}"
    acls:
      - ip: 10.0.0.0/8
        description: operator network
```

**This adds, it does not declare.** The natural Ansible question is "here are the
ACLs I want", and `SetClusterACLRules` exists in the contract for exactly that.
It is not shipped yet, for the same reason as labels and taints, and #277
carries it.

## Rotate the admin token

```yaml
- name: Rotate the admin token
  stephrobert.scaleway.k8s_cluster_reset_admin_token_action:
    region: fr-par
    cluster_id: "{{ cluster }}"
```

It invalidates the current kubeconfig. Anything using it stops working until it
fetches a new one, and this collection does not fetch it for you: see below.

## What is deliberately not supported

**The kubeconfig.** `GetClusterKubeConfig` returns administrative credentials in
a return value, and nothing here can mark a return value sensitive today. A
generated module would have put it in the task result, which lands in logs, in
callback plugins and in CI artefacts. The override carries that reason.

**User data.** `GetUserData` and `ListUserData` are excluded: the response shape
is insufficiently described in the contract, and the content is yours and may be
secret. Same missing capability as the kubeconfig.

**Creating and destroying clusters.** Terraform provisions, Ansible operates.
This is not a gap to be filled later.

## What has actually run against the real cloud

On a real account, in a dedicated project destroyed afterwards with residue
verified at zero. The run was recorded, and the recording is a versioned file:
this table is read out of it, never written by hand. It separates what this
collection emitted from what Terraform emitted, by user agent.

<!-- compteurs:preuve-kapsule:début, produits par scripts/readme_counters.py -->
| module | run of 2026-09-21 |
|---|---|
| `k8s_cluster` | reached |
| `k8s_cluster_acl_action` | reached |
| `k8s_cluster_acl_info` | reached |
| `k8s_cluster_available_type_info` | reached |
| `k8s_cluster_available_version_info` | reached |
| `k8s_cluster_info` | reached |
| `k8s_cluster_node_info` | reached |
| `k8s_cluster_pool_info` | reached |
| `k8s_cluster_reset_admin_token_action` | reached |
| `k8s_cluster_set_type_action` | not reached |
| `k8s_cluster_type_info` | reached |
| `k8s_cluster_upgrade_action` | not reached |
| `k8s_node_info` | shared route only |
| `k8s_node_reboot_action` | reached |
| `k8s_node_replace_action` | not reached |
| `k8s_pool` | reached |
| `k8s_pool_info` | shared route only |
| `k8s_pool_upgrade_action` | not reached |
| `k8s_version_info` | reached |
<!-- compteurs:preuve-kapsule:fin -->

**`shared route only` is not a softer yes.** Two modules can carry the same
read: `GET /nodes/{id}` belongs to the unitary info module and to the reboot's
wait, `GET /pools/{id}` to the info module and to the MANAGE module that reads
before it writes. The request went out, and nothing in the recording says which
one sent it. Crediting whichever came first alphabetically would have turned a
measurement into a coin toss.

**The rows that say not reached.** Most of them are one refusal: setting a
cluster type and upgrading a cluster or a pool change what the account is billed
for, and an example does not make that decision on behalf of whoever runs it.
`k8s_node_replace_action` is different, and saying so matters: replacing a node
is available as a primitive and not qualified as an operation, because nothing
yet observes the replacement finishing. Issue #279 carries it.

**The emulator does not serve `/k8s/v1`.** There is no middle tier for
Kubernetes: unit tests, then the real cloud. That is why this table exists at
all, and why it carries a date.

## Kapsule and Kosmos

They share this API. Everything above was exercised against **Kapsule**.

```text
Kapsule   qualified against the real cloud, on the date above
Kosmos    contract-compatible where the API is the same, never run here
```

Nothing in this collection refuses Kosmos, and nothing here has measured it.
Saying otherwise would be a promise nobody has checked.
