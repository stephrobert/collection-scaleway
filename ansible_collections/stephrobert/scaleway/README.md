# stephrobert.scaleway

Ansible **Day-2** collection for Scaleway. It provisions nothing: it operates
what already exists.

> Terraform provisions resources. Ansible operates existing resources.

That boundary decides everything else. You will not find `create` or `delete`
here. You will find what you need to **query, act on, and maintain the state
of** resources another tool created.

## What it does

* **Instance**: servers, IP addresses, security groups, placement groups,
  private NICs, snapshots, volumes, images;
* **Load Balancer**: load balancers, backends, frontends, ACLs, certificates,
  routes, subscribers, and health statistics;
* **Dynamic inventory**: Instances, Elastic Metal and Apple Silicon discovered
  together, with their private-network addresses;
* **check mode** and **`--diff`** on management modules;
* **idempotence**: a management module reads, compares, and writes only the
  difference;
* **`SCW_API_URL`** honoured end to end, so the collection can be exercised
  against a local emulator with no account and no spend.

## Requirements

| | version |
|---|---|
| `ansible-core` | >= 2.17 |
| Python (controller) | >= 3.12 |
| Scaleway SDK | >= 2.9.0 |

The `ansible-core` lower bound is measured, not assumed: 2.16 fails two
`ansible-test sanity` checks, and CI exercises every version declared here.

## Install

```bash
ansible-galaxy collection install stephrobert.scaleway
pip install 'scaleway>=2.9.0'
```

## Authentication

Through the environment, through the Scaleway configuration file, or through
module parameters, in that order of precedence:

```bash
export SCW_ACCESS_KEY=...
export SCW_SECRET_KEY=...
export SCW_DEFAULT_PROJECT_ID=...
```

`SCW_PROFILE` selects a profile from `~/.config/scw/config.yaml`. The
`access_key` and `secret_key` parameters of every module are marked `no_log`.

## Sixty seconds

An inventory, then a playbook that reboots what it found:

```yaml
# production.scaleway.yml
plugin: stephrobert.scaleway.scaleway
products:
  - instance
states:
  - running
group_by:
  - product
  - zone
  - tags
```

```yaml
# reboot.yml
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

```bash
ansible-playbook -i production.scaleway.yml reboot.yml
```

The inventory sets `scaleway_id`, `scaleway_zone` and `scaleway_product`, which
is all any module needs behind `delegate_to: localhost`.

### Query

```yaml
- name: Every server in a zone, all pages walked
  stephrobert.scaleway.instance_server_info:
    zone: fr-par-1
  register: servers
```

### Maintain state

```yaml
- name: These tags on this server, and nothing else
  stephrobert.scaleway.instance_server:
    zone: fr-par-1
    server_id: "{{ scaleway_id }}"
    tags: [production, web]
```

The module reads the resource, compares, and writes only the difference. A
second run reports no change.

## Included content

<!-- compteurs:début, produits par scripts/readme_counters.py -->
### Instance (26 modules)

| module | what it does |
|---|---|
| `instance_dashboard_info` | Gather information about Scaleway Instance dashboards |
| `instance_image` | Manage a Scaleway Instance image |
| `instance_image_info` | Gather information about Scaleway Instance images |
| `instance_ip` | Manage a Scaleway Instance ip |
| `instance_ip_info` | Gather information about Scaleway Instance ips |
| `instance_placement_group` | Manage a Scaleway Instance placement group |
| `instance_placement_group_info` | Gather information about Scaleway Instance placement groups |
| `instance_placement_group_server_info` | Gather information about Scaleway Instance placement group servers |
| `instance_security_group` | Manage a Scaleway Instance security group |
| `instance_security_group_info` | Gather information about Scaleway Instance security groups |
| `instance_security_group_rule` | Manage a Scaleway Instance security group rule |
| `instance_security_group_rule_info` | Gather information about Scaleway Instance security group rules |
| `instance_server` | Manage a Scaleway Instance server |
| `instance_server_action` | Perform an action on a Scaleway Instance server |
| `instance_server_compatible_type_info` | Gather information about Scaleway Instance server compatible types |
| `instance_server_info` | Gather information about Scaleway Instance servers |
| `instance_server_private_nic` | Manage a Scaleway Instance server private nic |
| `instance_server_private_nic_info` | Gather information about Scaleway Instance server private nics |
| `instance_server_type_availability_info` | Gather information about Scaleway Instance server type availabilities |
| `instance_server_type_info` | Gather information about Scaleway Instance server types |
| `instance_server_user_data_info` | Gather information about Scaleway Instance server user data |
| `instance_snapshot` | Manage a Scaleway Instance snapshot |
| `instance_snapshot_info` | Gather information about Scaleway Instance snapshots |
| `instance_volume` | Manage a Scaleway Instance volume |
| `instance_volume_info` | Gather information about Scaleway Instance volumes |
| `instance_volume_type_info` | Gather information about Scaleway Instance volume types |

### Load Balancer (21 modules)

| module | what it does |
|---|---|
| `lb_acl` | Manage a Scaleway Lb acl |
| `lb_acl_info` | Gather information about Scaleway Load Balancer acls |
| `lb_backend` | Manage a Scaleway Lb backend |
| `lb_backend_info` | Gather information about Scaleway Load Balancer backends |
| `lb_backend_stat_info` | Gather information about Scaleway Load Balancer backend stats |
| `lb_certificate` | Manage a Scaleway Lb certificate |
| `lb_certificate_info` | Gather information about Scaleway Load Balancer certificates |
| `lb_frontend` | Manage a Scaleway Lb frontend |
| `lb_frontend_acl_info` | Gather information about Scaleway Load Balancer frontend acls |
| `lb_frontend_info` | Gather information about Scaleway Load Balancer frontends |
| `lb_ip` | Manage a Scaleway Lb ip |
| `lb_ip_info` | Gather information about Scaleway Load Balancer ips |
| `lb_load_balancer` | Manage a Scaleway Lb load balancer |
| `lb_load_balancer_info` | Gather information about Scaleway Load Balancer load balancers |
| `lb_load_balancer_private_network_info` | Gather information about Scaleway Load Balancer load balancer private networks |
| `lb_load_balancer_stat_info` | Gather information about Scaleway Load Balancer load balancer stats |
| `lb_load_balancer_type_info` | Gather information about Scaleway Load Balancer load balancer types |
| `lb_route` | Manage a Scaleway Lb route |
| `lb_route_info` | Gather information about Scaleway Load Balancer routes |
| `lb_subscriber` | Manage a Scaleway Lb subscriber |
| `lb_subscriber_info` | Gather information about Scaleway Load Balancer subscribers |

### Inventory plugins

| plugin | what it discovers |
|---|---|
| `scaleway` | Instances, Elastic Metal and Apple Silicon, with their private-network addresses |
<!-- compteurs:fin -->

### What the action module refuses

`instance_server_action` accepts `poweron`, `poweroff`, `reboot` and
`stop_in_place`. It refuses `terminate`, `backup` and `enable_routed_ip`: the
first deletes the Instance and its volumes, the second creates an image, the
third migrates the network stack with no way back. The contract puts all seven
in the same enum; accepting them would have let the resource lifecycle in
through an action's door.

## Dynamic inventory

```bash
ansible-inventory -i production.scaleway.yml --graph
```

The file name must end in `scaleway.yml` or `scw.yml`, otherwise Ansible
ignores the source.

The full guide, covering how `ansible_host` is chosen per private network, name
collisions, and Ansible's trap around strict mode:
[docs/guides/dynamic-inventory.md](https://github.com/stephrobert/collection-scaleway/blob/main/docs/guides/dynamic-inventory.md).

## Shipped playbooks

They are called by their fully qualified name once the collection is installed:

```bash
ansible-playbook stephrobert.scaleway.inventaire_serveurs -e zone=fr-par-1
ansible-playbook stephrobert.scaleway.detail_dun_serveur -e zone=fr-par-1
ansible-playbook stephrobert.scaleway.arreter_un_serveur -e zone=fr-par-1 -e server_id=<uuid>
```

See [playbooks/README.md](playbooks/README.md).

## Compatibility

| collection | `ansible-core` | Python | Scaleway SDK |
|---|---|---|---|
| 0.1.x | 2.17, 2.18, 2.19, 2.20 | >= 3.12 | >= 2.9.0 |

All four `ansible-core` versions are tested by CI on every change. A version
declared and never tested is a promise with no proof.

## Versioning

This collection follows **semantic versioning**, which Ansible requires of
collections:

* **patch** (`0.1.1`): bug fixes only;
* **minor** (`0.2.0`): backward-compatible features and new modules;
* **major** (`1.0.0`): may contain breaking changes.

**Before `1.0.0`, treat the interfaces as evolving.** The split between action
operations and management operations is still maturing, and the collection is
growing quickly. The changelog is maintained by `antsibull-changelog` and lives
in [changelogs/](changelogs/).

## Where these modules come from

This collection is **produced by a generator** that reads the OpenAPI documents
Scaleway publishes. Module code is not written by hand, and **is not fixed by
hand**: a fix belongs to the contract, to a classification rule, or to an
override, and the file you are looking at will be rewritten by the next
generation run.

So report a defect on the repository rather than patching a module:
[stephrobert/collection-scaleway](https://github.com/stephrobert/collection-scaleway).
The generator's architecture and its coverage methodology are documented there.

## Reporting a defect

[github.com/stephrobert/collection-scaleway/issues](https://github.com/stephrobert/collection-scaleway/issues)

What helps most: the collection version, the `ansible-core` version, the task
you ran, and what the API answered.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
