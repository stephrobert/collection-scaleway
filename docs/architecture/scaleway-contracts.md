# The Scaleway contracts: the source, its limits, how it is watched

The generator reads **OpenAPI 3.1** documents published by Scaleway and
versioned under `specs/scaleway/`. This page says where they come from, what
they carry, what they do not, and how the repository notices that they moved.

## The source

Every product page on the developers portal exposes a downloadable document:

```text
https://www.scaleway.com/en/developers/api/<slug>/<version>/schema.yml
```

`mise run sync:api` downloads them, `specs/scaleway/products.txt` indexes them.
Generation itself reads only the disk: it never depends on the network, so it
is reproducible offline, and an API change arrives as a reviewable diff rather
than as a result that changes on its own.

**The portal slug is not always the product name in the SDK.** It is checked on
the product page rather than guessed:

| SDK name | portal slug |
|---|---|
| `baremetal` | `elastic-metal` |
| `k8s` | `kubernetes` |
| `lb` | `load-balancer/zoned` |
| `vpcgw` | `public-gateway` |

Some products are split on the portal side: `account/v3` answers 404, while
`account/project/v3` and `account/contract/v3` answer 200.

**There is no machine-readable index.** No public Scaleway repository publishes
these documents, and the version-less URL answers 404. The list of tracked
products is therefore maintained by hand in `specs/scaleway/products.txt`. That
is a fact about Scaleway, not a design choice.

## What the document carries

Measured on `instance.v1.yml`: **38 paths, 74 operations, 134 schemas, 18
enums**, and for every operation:

* an `operationId` (`ListServers`, `ServerAction`, ...);
* the scope in the path, with the closed enumeration of zones:
  `/instance/v1/zones/{zone}/servers`, `zone ∈ {fr-par-1, …, it-mil-1}`. VPC v2
  does the same with `{region}`;
* typed query parameters, pagination `page` and `per_page` included;
* enums, reached by reference:
  `#/components/schemas/scaleway.instance.v1.Server.Action` is
  `[poweron, backup, stop_in_place, poweroff, terminate, reboot, enable_routed_ip]`;
* request bodies, property by property, with their descriptions;
* responses, by reference to a named schema;
* field-level deprecations (`routed_ip_enabled`, `enable_ipv6`);
* an `x-properties-order` extension giving the original field order.

## What the document does not carry

The published document is a **lossy projection** of Scaleway's internal IDL,
poorer than the SDKs generated from the same source. These limits are measured
on `instance.v1.yml`, and the generator **reports** them instead of filling
them in by guesswork: they appear in the report under "contract limits".

### `total_count` is absent from list responses

The document declares `ListServersResponse` with the single field `servers`.
The Python SDK declares, for the same type:

```python
class ListServersResponse:
    total_count: int
    servers: list[Server]
```

Pagination that relies on `total_count` must therefore read it at runtime, not
in the contract.

### Arrays in a request body do not declare their elements

```yaml
tags:
  type: [array, "null"]
  description: Tags of the Instance.
```

No `items`, no element type. Seventeen parameters of Instance v1 are in this
case. The generator falls back to `elements: str` **and** records the parameter
in the report's limits, so that a wrong type does not slip by unnoticed.

### No body field is declared `required`

`ServerActionRequest` marks `requestBody.required: true`, but its schema
carries no `required` list. The `action` field, which the API refuses to do
without, is therefore optional according to the contract. Body requirements
come from the overrides, and they carry their reason.

### The protobuf wrappers show through

`google.protobuf.BoolValue`, `Int32Value`, `StringValue` and `UInt32Value`
appear as schemas and resolve to nullable types. The parser walks through them;
the IR carries only the useful type.

### There is neither a waiter nor an idempotency rule

The contract does not say which field to watch to know that an action has
finished. The SDK, on the other hand, exposes waiters. Wait configuration
therefore comes from the overrides.

### `ListPrivateNICs` does not list every NIC, and the contract says so

Measured on 3 September 2026, by the first run of the drift workflow. Scaleway
added two descriptions to the Instance v1 contract:

> Some private NICs, such as those in deleting, detaching, or in error state
> are not listed. We strongly recommend migrating to v2alpha1 to retrieve all
> private NICs.

This is a limit of the API, not of the generator, and it is visible only there:
no parameter, no enum and no operation moved, and the strict report stays at 0.

**What it does not affect.** The dynamic inventory does not join the network
through `ListPrivateNICs`. It lists once per region (`ipam.list_i_ps_all`,
`vpc.list_private_networks_all`, `vpc.list_vp_cs_all`), indexes, then joins in
memory: IPAM carries the NIC/network/VPC relation, and that is the source that
decides.

**What it does affect, and how the warning got there.**
`instance_server_private_nic_info` is generated and shipped, so a playbook that
calls it receives an incomplete list. The module says so itself: the generator
copies the contract's description verbatim into `DOCUMENTATION`, so the
sentence above reached the module's documentation without anyone writing it.
That is the mechanism working as intended, and it is why descriptions are
propagated rather than rewritten.

`CreatePrivateNIC` carries a neighbouring warning about quotas. It is
classified LIFECYCLE, Terraform's scope, so it does not concern this
collection.

## Two roles that are never confused

| role | who holds it |
|---|---|
| describing the API for generation | the portal's OpenAPI documents, versioned under `specs/scaleway/` |
| calling the API at runtime | the official Python SDK, like the Scaleway collection |

The generator does not read the SDK, and the modules do not read the contract.
The official SDKs are generated from an unpublished internal IDL: depending on
them would mean parsing Python or Go code to extract a contract, which is a
parser against a moving target. They serve here as an arbitration source when
the OpenAPI document is ambiguous or silent.

## Risks and watching

| risk | why it is real | what makes it visible |
|---|---|---|
| the `schema.yml` URL is not contractual | it is a web page link, and the portal has already been redesigned | `mise run sync:api` fails loudly on a 404 rather than leaving a stale file |
| no product index | no public repository publishes one | `specs/scaleway/products.txt`, hand-maintained, with the slug measured |
| the projection loses information | measured on `total_count`, `items`, `required` | the report lists the limits encountered, operation by operation |
| the API moves | Scaleway added 453 SDK methods and removed 26 in twelve months | the golden IR and `report --strict` fail on any unsorted operation |

Four more contracts are versioned under `specs/scaleway/suivis/` without being
generated: `ipam.v1`, `vpc.v2`, `baremetal.v1` and `applesilicon.v1alpha1`. The
dynamic inventory calls them, and the join that gives each machine its private
address reads their fields through `getattr(..., None)`, so a renamed field
upstream returns `None` rather than raising. Generating them would add
permanent UNKNOWN operations for work nobody asked for; versioning them makes
their drift visible.

## Reproducing the measurements

```bash
curl -sL -o /dev/null -w '%{http_code} %{size_download}\n' \
  'https://www.scaleway.com/en/developers/api/instance/v1/schema.yml'

mise run sync:api
python -m generator inspect instance
python -m generator report instance --strict
```
