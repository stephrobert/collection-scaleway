# ADR-019. An API name filter narrows a listing, it never selects a resource

**Status**: accepted, 10 September 2026. Still in force.

## Context

Half of this collection acts on a sub-resource carrying its own identifier,
which only the matching `_info` module returns. The README publishes the
measurement: the inventory sets `scaleway_id` and `scaleway_zone`, which is
what 25 of the 50 modules need, and the other 25 act on a sub-resource whose
identifier comes from a listing. So a playbook calls a module, registers its
result, digs a UUID out of it, and injects it into the next task.

The shape that appears in every such playbook is the problem:

```yaml
backend_id: "{{ (backends.backends | first).id }}"
```

`| first` is silent when there are two candidates and crashes obscurely when
there are none. Removing it was the reason to resolve a name into an
identifier at all.

The obvious implementation is to let the API do the work, because the versioned
contracts declare a `name` query parameter on the listings. **Measured on the
contracts, that filter does not mean what its name suggests.** `ListServers`
documents itself:

> Filter Instances by name (eg. "server1" will return "server100" and "server1"
> but not "foo").

and `ListVolumes`:

> for eg. "vol" will return "myvolume" but not "data".

It is a prefix match. Three levels of declaration coexist for one notion:
`ListServers` and `ListVolumes` describe the semantics with an example,
`ListLbs` and `ListBackends` say only "to filter for", and `ListImages`
declares nothing at all. Nothing in the contracts lets us conclude that the
filter is exact anywhere.

A lookup that trusted it would answer `server100` to a caller asking for
`server1`. That is the `| first` defect moved inside the plugin, where it is
less visible: the playbook would not even show the list it chose from.

## Decision

The API filter is a **narrowing hint**, never a selection.

* it is sent when the contract declares it, because paginating a whole fleet to
  find one machine is a cost the caller did not ask for;
* the exact comparison on `name` is done locally, **in every case**, including
  when the API has already filtered. A code path that only ran against some
  future contract would not be exercised, and an unexercised path is a promise;
* the three outcomes are distinct and none of them is a choice made on the
  caller's behalf:

  ```text
  no exact match     -> refuse, naming what was found nearby
  exactly one        -> its identifier
  more than one      -> refuse, naming the candidates
  ```

The "no match" message carries the near misses, because the question the caller
is asking at that moment is whether they made a typo. The "several" message
carries the identifiers, because without them there is nothing to arbitrate.
Scaleway does not enforce name uniqueness, so the third case is not theoretical.

## Consequences

Resolving one name costs at least one listing, and the local comparison walks
every element the API returned. On a large fleet with a filter that narrows
poorly, that is more work than a single `GET`. It is the price of never
answering with a resource nobody designated.

A caller who genuinely wants prefix behaviour cannot get it from this lookup.
That is deliberate: they can call the `_info` module and filter as they see fit,
where the list they chose from is visible in the playbook.

The refusal messages become part of the interface, so they are worth their
length. A message that said only "not found" would send someone hunting for a
typo in a name that is spelled correctly.

## What this record does not decide

Which identifiers can be resolved at all. That is derived from the contracts,
not decided: an identifier resolves when exactly one listing returns an object
carrying both `id` and `name`. Four identifiers of the versioned contracts do
not, because `Ip`, `Route`, `PrivateNIC` and `SecurityGroupRule` carry no `name`
field, and no heuristic will fill that in. They are published with that reason
rather than approximated.

How a retry policy applies to the listing, which is ADR-018.
