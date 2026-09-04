# The Scaleway dynamic inventory

`stephrobert.scaleway.compute` builds an Ansible inventory from a Scaleway
account. It discovers machines product by product, then links them to their
private networks and their VPCs.

Everything this document claims is measured: the unit tests live in
[tests/unit/inventory/](https://github.com/stephrobert/collection-scaleway/blob/main/tests/unit/inventory/),
and the scenario played on every `mise run integration` is
[tests/integration/feint/inventaire.scaleway.yml](https://github.com/stephrobert/collection-scaleway/blob/main/tests/integration/feint/inventaire.scaleway.yml).

## The configuration file

Ansible recognises an inventory plugin by the **file name**. It must end in
`scaleway.yml` or `scw.yml`, otherwise it is silently ignored:

```bash
ansible-inventory -i production.scaleway.yml --graph
```

The minimum fits on one line, and the usual Scaleway profile decides the rest:

```yaml
plugin: stephrobert.scaleway.compute
```

## Credentials

Credentials are read from the environment, from the Scaleway configuration
file, or from the inventory file, in that order:

```bash
export SCW_ACCESS_KEY=... SCW_SECRET_KEY=...
```

`SCW_API_URL` is honoured: pointing it at a local emulator builds an inventory
with no account and no spend. That is how this plugin is actually tested.

## Products

Three hosting products are discovered:

| `products` | what gets listed |
|---|---|
| `instance` | Instances |
| `elastic_metal` | Elastic Metal servers |
| `apple_silicon` | Apple Silicon machines |

`all`, the default, means **those three**, not every existing Scaleway API. An
unknown name is refused rather than ignored: a misspelled product would produce
a silently partial inventory.

```yaml
plugin: stephrobert.scaleway.compute
products:
  - instance
  - elastic_metal
```

## Zones and regions

Without `zones`, each product queries the ten zones it declares. A zone where
the product does not exist removes itself, because the API says so.

`regions` only serves the network index: it is derived from the zones, and only
needs writing to widen it.

```yaml
zones:
  - fr-par-1
  - fr-par-2
```

## Machine names

`hostnames` gives the sources of `inventory_hostname`, in order:

```yaml
hostnames:
  - tag:role      # reads a "role=web" tag
  - name
  - id
```

Accepted are `name`, `id`, `public_ipv4`, `public_ipv6`, `private_ipv4`,
`private_ipv6` and `tag:KEY`. The names `hostname`, `vpc_ipv4` and `vpc_ipv6`
used by the official collection are still understood, so an existing
configuration keeps working.

**Collisions do not lose a machine.** A Scaleway name is unique neither within
a zone nor within a project: two machines can be called `web01`. The second
then receives `web01_fr-par-1`, and the third `web01_<identifier>`. Every
disambiguation is reported by a warning, and the result is the same from one
run to the next.

## Where Ansible reaches the machine

`ansible_host` is chosen in the order of the requested families:

```yaml
address_priority:
  - private_ipv4
  - public_ipv4
  - private_ipv6
  - public_ipv6
```

That is the default order: a controller managing a Scaleway fleet is most often
inside the VPC, and a private address does not depend on a public IP being
allocated. A workstation outside the VPC simply reverses the list.

A machine on several private networks is reached through the network you name,
not through whichever comes first:

```yaml
address:
  private_network: backend    # a name, or an identifier
```

`scaleway_address_source` carries, on each machine, the family retained or the
reason for the failure. `-vvvv` gives the full line, along the lines of
`web01: 10.10.0.5 via private_ipv4, network backend`.

**A machine with no address stays in the inventory.** It has no SSH route, but
it remains drivable through the API with `delegate_to: localhost`, which is the
common Day-2 case. `require_address: true` asks for the opposite.

## Groups

`group_by` chooses the axes of the `scw_*` groups:

```yaml
group_by:
  - product          # scw_product_instance
  - project          # scw_project_<identifier>
  - region           # scw_region_fr_par
  - zone             # scw_zone_fr_par_1
  - state            # scw_state_running
  - tags             # scw_tag_env_prod
  - vpc              # scw_vpc_socle
  - private_network  # scw_private_network_backend
```

Names are sanitised for Ansible: `production/web` becomes `production_web`,
`pré-prod` becomes `pre_prod`, and `2024` becomes `_2024` rather than `_024`,
which is what Ansible would make of it on its own.

The product is an **axis**, not an injected tag: `scaleway_tags` carries what
Scaleway carries, and nothing else.

`compose`, `groups` and `keyed_groups` work, because they are called and not
merely documented:

```yaml
compose:
  ansible_user: scaleway_apple_silicon.ssh_username | default('root')
keyed_groups:
  - prefix: type
    key: scaleway_instance.commercial_type
```

## Filtering

```yaml
organizations:
  - 99999999-9999-4999-8999-999999999999
tags:
  - env=production
tags_match: all      # "any" by default; the API can only express "any"
states:
  - running
exclude:
  tags:
    - canary
  states:
    - stopping
```

What can be filtered API-side is filtered API-side, so as not to transfer what
will be thrown away. The rest is decided locally, and `-vvv` says why each
excluded machine was excluded.

`organizations` is passed to the API when **exactly one** is requested, never in
a loop: several organisations would multiply the calls by the zones, the states
and the projects. Local filtering remains the guarantee in every case, and it is
not decorative: an API ignoring that parameter would return the whole fleet, and
the inventory would silently be wider than asked.

## Cache

```yaml
cache: true
cache_plugin: jsonfile
cache_connection: ~/.ansible/tmp/scaleway
```

The cache key covers **everything that changes the result**: the profile, the
API URL, the products, the zones, the projects, the filters, the name sources,
the address policy and the group axes. Two different configurations never share
an inventory, even from the same directory.

## Strict mode, and a trap that is not ours

`strict: true`, the default, fails the inventory when a provider fails, instead
of returning an incomplete fleet. Failures are classified:

| what happens | what the plugin makes of it |
|---|---|
| credentials refused | fatal, immediately, without trying the other zones |
| missing permission on a product | named error; a token may hold only part of the fleet |
| product absent from a zone | warning, because that is not an outage |
| any other API failure | named error, with the product and the zone |

**But Ansible downgrades that failure to a warning.** Measured: against an
unreachable endpoint, the plugin raises with a message naming the cause, and
`ansible-inventory` still exits **0** with an empty inventory. An inventory
source that cannot be parsed is not an error for Ansible by default. For a
failure to stop a CI run, you have to ask:

```bash
export ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED=True
```

or, in `ansible.cfg`:

```ini
[inventory]
any_unparsed_is_failed = True
```

Without that, `strict: true` writes the reason and blocks nothing. This check is
played both ways on every `mise run integration`.

## The variables set on each machine

| variable | contents |
|---|---|
| `scaleway_id` | the identifier, the one the collection's modules expect |
| `scaleway_product` | `instance`, `elastic_metal` or `apple_silicon` |
| `scaleway_name` | the Scaleway name, before disambiguation |
| `scaleway_zone`, `scaleway_region` | the location |
| `scaleway_state` | the state as the API returns it |
| `scaleway_project_id`, `scaleway_organization_id` | the scope |
| `scaleway_tags` | the Scaleway tags, and nothing else |
| `scaleway_public_ipv4`, `scaleway_public_ipv6` | every address, not the first |
| `scaleway_private_ipv4`, `scaleway_private_ipv6` | the same, across all networks |
| `scaleway_private_networks` | per network: identifier, name, VPC, addresses, MAC |
| `scaleway_address_source` | why this `ansible_host` |
| `scaleway_<product>` | what belongs to that product alone |
| `scaleway_raw` | the raw response, only with `include_raw: true` |

`scaleway_<product>` files what is specific to each API under its own prefix,
instead of pouring it into the global namespace: `commercial_type` for
Instance, `offer_name` for Elastic Metal, `ssh_username` for Apple Silicon.

## Chaining onto the collection's modules

That is what the inventory is for, and the three identity variables are enough,
with no extra lookup:

```yaml
- name: Shut down the pre-production machines
  hosts: scw_tag_env_preprod
  gather_facts: false
  tasks:
    - name: Power off
      stephrobert.scaleway.instance_server_action:
        zone: "{{ scaleway_zone }}"
        server_id: "{{ scaleway_id }}"
        action: poweroff
        wait: true
      delegate_to: localhost
```

## Diagnosing

```bash
ansible-inventory -i production.scaleway.yml --graph
ansible-inventory -i production.scaleway.yml --list -vvv    # the report
ansible-inventory -i production.scaleway.yml --list -vvvv   # and every address
```

The report gives the number of API calls, the number of IPAM addresses indexed,
the number of machines per product, then every warning and every exclusion.

One reading detail: `--list` serialises strings coming from a plugin as
`{"__ansible_unsafe": "..."}`. That is Ansible's marking, not an anomaly;
`--graph` and playbooks see the string.

## How many API calls

Private networks are listed **once per region**, then joined in memory. The
official collection queries IPAM once per network card, that is two thousand
calls for a thousand two-card Instances, and gets less out of it: it keeps only
one private address per machine, without saying which network it belongs to.

Here the cost of the join is linear in network cards, and that is proven by
counting index lookups, not with a stopwatch.

The index itself is only built if a requested product carries private network
cards. `products: [apple_silicon]` therefore no longer pays for the twelve calls
it would have made nothing of. The filtering deliberately stops there: cutting
it as well when `address_priority` names only public families would silently
empty `scaleway_private_ipv4` and `scaleway_private_networks`, which a `compose`
may depend on. Not calling and returning nothing are not the same thing.

A missing permission on IPAM or VPC is a **warning**, not an error: a token
without that permission builds a perfectly good inventory of public machines,
and failing the whole inventory in strict mode over an enrichment nobody needed
would be a misplaced refusal.

## What this plugin does not do yet

* managed resources (Kubernetes, Load Balancers, databases) are not discovered;
  only machines are;
* discovery is sequential: no parallelism between products yet;
* Elastic Metal and Apple Silicon are proven by tests with simulated responses,
  for lack of an emulator serving them (feint#631, feint#632). Instance is
  proven end to end against a real emulator, and against a real account.
