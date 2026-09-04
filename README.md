# collection-scaleway

A generator of **Day-2** Ansible modules for the Scaleway APIs, and the
collection it produces.

Responsibility is split, and that boundary decides everything else:

> Terraform provisions resources. Ansible operates existing resources.

So the generator produces neither `create` nor `delete`: it produces
information modules, one-shot action modules, and Day-2 state management
modules.

## Using the collection

This is the deliverable, and it installs without knowing anything about what
follows.

```bash
ansible-galaxy collection install stephrobert.scaleway
pip install 'scaleway>=2.9.0'
export SCW_ACCESS_KEY=... SCW_SECRET_KEY=...
```

An inventory discovers the fleet, a playbook acts on it:

```yaml
# production.scaleway.yml
plugin: stephrobert.scaleway.compute
products: [instance]
states: [running]
group_by: [product, zone, tags]
```

```yaml
- name: Reboot production servers
  hosts: scw_tag_production
  gather_facts: false

  tasks:
    - name: Reboot, and wait for the target state
      stephrobert.scaleway.instance_server_action:
        server_id: "{{ scaleway_id }}"
        zone: "{{ scaleway_zone }}"
        action: reboot
      delegate_to: localhost
```

The inventory sets `scaleway_id` and `scaleway_zone`, which is all any of the
46 modules needs behind `delegate_to: localhost`.

The rest, requirements, module tables, compatibility and versioning, lives in
the collection's own README:
[ansible_collections/stephrobert/scaleway/](ansible_collections/stephrobert/scaleway/README.md).

## State and coverage

The numbers in this block are **derived**, not copied: `mise run readme`
rewrites them from the sources of record, and CI fails when they have aged. A
number copied by hand ages silently, and reads exactly like a measurement.

Step 3 complete on the module side, step 5 complete on the inventory side. The
chain runs from contract to module, the module runs, and the collection ships a
dynamic inventory plugin that discovers three products behind one model.

<!-- compteurs:début, produits par scripts/readme_counters.py -->
```text
instance v1: 74 operations discovered
  INFO 26 · ACTION 3 · MANAGE 10 · WORKFLOW 1 · LIFECYCLE 19 · IGNORE 15 · UNKNOWN 0
  Day-2 40 · AUTO 39 · MANUAL 1 · classified for automatic generation 97.5% (39/40)

collection stephrobert.scaleway: 50 modules written out of 52 planned
  instance_dashboard_info                Gather information about Scaleway Instance dashboards
  instance_image                         Manage a Scaleway Instance image
  instance_image_info                    Gather information about Scaleway Instance images
  instance_ip                            Manage a Scaleway Instance ip
  instance_ip_action                     Perform an action on a Scaleway Instance ip
  instance_ip_info                       Gather information about Scaleway Instance ips
  instance_placement_group               Manage a Scaleway Instance placement group
  instance_placement_group_info          Gather information about Scaleway Instance placement groups
  instance_placement_group_server_info   Gather information about Scaleway Instance placement group servers
  instance_security_group                Manage a Scaleway Instance security group
  instance_security_group_info           Gather information about Scaleway Instance security groups
  instance_security_group_rule           Manage a Scaleway Instance security group rule
  instance_security_group_rule_info      Gather information about Scaleway Instance security group rules
  instance_server                        Manage a Scaleway Instance server
  instance_server_action                 Perform an action on a Scaleway Instance server
  instance_server_compatible_type_info   Gather information about Scaleway Instance server compatible types
  instance_server_info                   Gather information about Scaleway Instance servers
  instance_server_private_nic            Manage a Scaleway Instance server private nic
  instance_server_private_nic_info       Gather information about Scaleway Instance server private nics
  instance_server_type_availability_info Gather information about Scaleway Instance server type availabilities
  instance_server_type_info              Gather information about Scaleway Instance server types
  instance_server_user_data_info         Gather information about Scaleway Instance server user data
  instance_snapshot                      Manage a Scaleway Instance snapshot
  instance_snapshot_action               Perform an action on a Scaleway Instance snapshot
  instance_snapshot_info                 Gather information about Scaleway Instance snapshots
  instance_volume                        Manage a Scaleway Instance volume
  instance_volume_info                   Gather information about Scaleway Instance volumes
  instance_volume_type_info              Gather information about Scaleway Instance volume types
  lb_acl                                 Manage a Scaleway Lb acl
  lb_acl_info                            Gather information about Scaleway Load Balancer acls
  lb_backend                             Manage a Scaleway Lb backend
  lb_backend_info                        Gather information about Scaleway Load Balancer backends
  lb_backend_stat_info                   Gather information about Scaleway Load Balancer backend stats
  lb_certificate                         Manage a Scaleway Lb certificate
  lb_certificate_info                    Gather information about Scaleway Load Balancer certificates
  lb_frontend                            Manage a Scaleway Lb frontend
  lb_frontend_acl_info                   Gather information about Scaleway Load Balancer frontend acls
  lb_frontend_info                       Gather information about Scaleway Load Balancer frontends
  lb_ip                                  Manage a Scaleway Lb ip
  lb_ip_info                             Gather information about Scaleway Load Balancer ips
  lb_load_balancer                       Manage a Scaleway Lb load balancer
  lb_load_balancer_action                Perform an action on a Scaleway Load Balancer load balancer
  lb_load_balancer_info                  Gather information about Scaleway Load Balancer load balancers
  lb_load_balancer_private_network_info  Gather information about Scaleway Load Balancer load balancer private networks
  lb_load_balancer_stat_info             Gather information about Scaleway Load Balancer load balancer stats
  lb_load_balancer_type_info             Gather information about Scaleway Load Balancer load balancer types
  lb_route                               Manage a Scaleway Lb route
  lb_route_info                          Gather information about Scaleway Load Balancer routes
  lb_subscriber                          Manage a Scaleway Lb subscriber
  lb_subscriber_info                     Gather information about Scaleway Load Balancer subscribers
  compute (inventory)                    instance, elastic_metal, apple_silicon
  44 modules called by the example playbook out of 50 (88.0%), which is not the same as played
  494 unit tests · 106 mutations proven by /falsify
  CI: 5 jobs, Générateur · collection · Archive · Intégration · Plateforme d'exemple
  ansible-test sanity, playbooks and inventory against the emulator:
  reported by `mise run sanity` and `mise run integration`
```
<!-- compteurs:fin -->

**What the inventory cost the core.** Adding Elastic Metal and Apple Silicon
after Instance took twelve lines in the `discovery.py` registry, and none in
the normalised model, the address selection, the groups, the host name, the
network join or the plugin. That is the measurement of step 5, and a test holds
it: no layer of the core names a product in its code.

Elastic Metal and Apple Silicon are proven against simulated responses: the
emulator serves neither, and will not soon (feint#631, feint#632). Instance is
proven end to end.

## Developing the generator

Everything below is for whoever wants to **change what produces** the
collection. A user never needs any of it.

```bash
mise run setup                 # development environment
mise run report                # coverage report for Instance
mise run generate              # write the modules into plugins/modules
mise run check                 # what a pull request has to pass
mise run sanity                # what Ansible says about the produced file
mise run docs                  # judge the docs with antsibull-docs, then build the pages
mise run package               # build the archive, install it, and question it
mise run integration           # the playbooks, examples included, against an emulator
mise run security              # actionlint, zizmor and poutine on the workflows
mise run security:trust        # plumber, the pipeline's trust policy
mise run lock                  # recompute the dependency lock
```

```bash
python -m generator inspect instance     # what the contract declares
python -m generator classify instance    # the decision, operation by operation
python -m generator report instance --strict
python -m generator generate instance --module instance_server_info
```

## Two products, two locations

```text
.                                     the producer
├── generator/                        reads the contract, decides, writes the module
├── scripts/                          the check runners
├── specs/scaleway/                   the versioned contracts
└── ansible_collections/stephrobert/scaleway/    the deliverable, and nothing else
```

The collection sits where Ansible requires it. This is not tidiness:
`ansible-test`, `antsibull-docs` and `ansible-playbook` work **in place**, with
no copy assembled elsewhere. The first layout put the collection at the root,
and the copy it then had to build produced an `ansible-test sanity` that was
green over **zero files examined**.

## How it works

| stage | code | what it produces |
|---|---|---|
| source | `generator/source/` | the versioned OpenAPI contract in `specs/` |
| parser | `generator/parser/` | the canonical IR, with no Ansible and no SDK |
| classifier | `generator/classifier/` | INFO, ACTION, MANAGE, WORKFLOW, LIFECYCLE, IGNORE, UNKNOWN |
| overrides | `generator/overrides/` | the human decisions, each with its reason |
| report | `generator/report/` | text, JSON and Markdown |
| model | `generator/ansible/models.py` | the single source of the `argument_spec` and the docs |
| renderer | `generator/renderer/`, `generator/templates/` | the files under `plugins/modules/` |
| runtime | `ansible_collections/stephrobert/scaleway/plugins/module_utils/` | client, errors, pagination, check mode |

The source of truth is the OpenAPI 3.1 document Scaleway publishes per product
on its developers portal. What it carries, what it does not, and how this
repository notices that it moved are documented in
[docs/architecture/scaleway-contracts.md](docs/architecture/scaleway-contracts.md).

## Four rules that outrank the rest

1. **No operation disappears.** What no rule settles is `UNKNOWN`, and
   `report --strict` exits with code 2.
2. **The metric does not dress itself up.** Coverage relates `AUTO + OVERRIDE`
   to Day-2 operations only; LIFECYCLE and IGNORE are counted apart, not erased.
3. **Generation is deterministic.** Same contract, same output, byte for byte.
   Two golden files hold it: `tests/fixtures/instance/expected_ir.json` for what
   the parser reads, `tests/fixtures/widget/expected_modules/` for what the
   renderer writes.
4. **A green that measured nothing is refused.** `ansible-test` skips all its
   targets and exits 0 when git lists nothing for it; `mise run sanity` refuses
   that particular exit. Every guard in this repository is proven by
   neutralising it, and the count is in the block above, not written here by
   hand: `mise run falsify`.

## The quality of the deliverable

The collection follows the Ansible community
[inclusion checklist](https://github.com/ansible-collections/ansible-inclusion/blob/main/collection_checklist.md),
and every item is held by a command rather than an intention:

| requirement | what holds it |
|---|---|
| license shipped with the collection | `LICENSE`, and `mise run package` refuses an archive that forgets it |
| **measured** minimum ansible-core version | CI matrix over 2.17 to 2.20; 2.16 fails, and the bound says so |
| changelog, preferably `changelogs/changelog.yaml` | fragments and `antsibull-changelog`, judged by `mise run check` |
| documentation to standard | `ansible-test sanity` **and** `antsibull-docs`, which sees what the first lets through |
| CI on every pull request and on a schedule | four jobs, plus a weekly trigger |
| no stray files in the repository | `mise run check:worktree` fails if a build leaves an untracked file |
| dependencies declared for an execution environment | `meta/execution-environment.yml` and `meta/ee-requirements.txt` |
| supply chain held | actions pinned by SHA, dependencies locked with hashes, four workflow scanners at the gate |

The archive is not merely built: `mise run package` inspects its contents,
installs it into a throwaway directory, then asks `ansible-doc` for its
documentation and has `ansible-playbook` resolve every playbook. A file present
in an archive is not a module Ansible can load.

## Documentation

* [Generator architecture](docs/architecture/generator.md)
* [The Scaleway contracts](docs/architecture/scaleway-contracts.md): the source, its limits, how it is watched
* [The collection runtime](docs/architecture/runtime.md)
* [The dynamic inventory](docs/guides/dynamic-inventory.md), and Ansible's trap around strict mode
* [What OpenSSF Scorecard says, and what it does not](docs/scorecard.md)
* [SECURITY.md](SECURITY.md): how to report a vulnerability, and what the repository already holds
* [The shipped playbooks](ansible_collections/stephrobert/scaleway/playbooks/README.md), played on every `mise run integration`

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
