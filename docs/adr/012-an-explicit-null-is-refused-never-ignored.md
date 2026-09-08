# ADR-012. An explicit null is refused, never ignored

**Status**: superseded by [ADR-016](016-an-explicit-null-clears-the-field.md), 8 September 2026.

The refusal below closed a false success and was right to. Its mechanism was ruled by a measurement whose scope was too narrow: it measured a `fallback` that returns a value, and never one that raises. ADR-016 carries the wider measurement, and the clearing this record could not do.

## Context

The contract marks a writable field as clearable with `oneOf: [T, null]` or
`type: [T, "null"]`, and the IR carries the fact since
[ADR-008](008-a-constraint-is-translated-or-named.md). The runtime built its
request from the values that were not `None`:

```python
demande = {nom: params[nom] for nom in geres if params.get(nom) is not None}
```

So this task reported `ok`, and the description was still there:

```yaml
- hosts: localhost
  tasks:
    - name: Retirer la description
      stephrobert.scaleway.instance_security_group:
        zone: fr-par-1
        security_group_id: "{{ sg_id }}"
        description: null
```

The request vanished before the whole chain of proof, read, compare, write,
read again, verify ([ADR-010](010-postconditions-are-checked-not-announced.md)).
A false success, on the promise this repository refuses to break anywhere else.

Ansible does not tell an omitted option from an explicit `null`: `module.params`
carries `None` in both cases. Which public mechanism does, and on every
`ansible-core` the CI exercises, was measured rather than assumed, with
`ArgumentSpecValidator` and with `AnsibleModule` itself fed through
`_ANSIBLE_ARGS`, on 2.17.14, 2.18.19, 2.19.12, 2.20.8 and 2.21.3:

| option form | omitted | explicit `null` | verdict |
|---|---|---|---|
| `type: str`, no default (before) | `None` | `None` | indistinguishable, everywhere |
| `type: str`, marker default | marker | 2.17 and 2.18: type error, the module fails; 2.19 and later: `''` | not portable |
| `type: raw`, marker default | marker | `None` | distinguishable, everywhere |
| `type: str` or `raw`, marker `fallback` | marker | `None` | distinguishable, everywhere, **but** `mutually_exclusive` then fails on every call: Ansible counts present keys, and a fallback is applied before that check where a default is applied after |
| `basic._load_params()` | raw arguments, `null` kept | | distinguishable, everywhere; private, its docstring promises no stability |

The issue that opened this record had measured the second row on 2.21.3 only,
where it reads `''`. On 2.17 and 2.18 the same form fails the module on an
explicit `null` with "unable to convert to str". A mechanism that holds on one
version and not the next is not a mechanism.

`validate-modules` was measured too, on a copy of the collection outside the
tree: an `argument_spec` that says `raw` with a documentation that says `str`
is refused (`doc-type-does-not-match-spec`), and a marker default absent from
the documentation is refused (`doc-default-does-not-match-spec`). Whatever the
module declares, the page publishes.

## Decision

**A field the contract declares clearable, managed by a managing module, is
published as `type: raw` with the marker `__unchanged__` as its default.** The
generator applies it to those options only; the option description states the
API type, what the marker means, and that an explicit `null` is refused. The
`choices` and `elements` of such an option move to the runtime entry: Ansible
checks a default against `choices`, and would refuse every call where the
option is omitted.

**The runtime refuses an explicit `null` before reading anything.** A `null` on
a field it cannot clear is a request it cannot honour, and it says so, naming
the field and what to do instead. Refusing before the read is what makes the
refusal identical against the emulator and against the real cloud.

**`raw` costs the playbook nothing.** The runtime strips the marker, then
re-validates every provided value with Ansible's own `ArgumentSpecValidator`
and the real entry: same conversions, same messages. `stateful: "no"` is still
a boolean.

The generator and the runtime each carry the marker; a test requires the two to
agree.

## Consequences

The page publishes `raw` and a marker default on those options: at the date of
this record, 38 options across 13 managing modules, out of the 40 clearable
fields the measurement counts (the other two belong to `instance_server_action`,
an action module, on which this record does not act). The description restores
what the type field loses. That is the price, and it was measured before being
paid: the cheaper mechanisms either do not hold on every version or break
mutual exclusion.

`basic._load_params()` would have cost nothing on the page and holds on every
version. It is rejected for the reason `API._request` was: a name that starts
with an underscore is not a contract, and this runtime does not build on one.

The refusal covers what the IR sees. At the date of this record the parser
loses nullability behind a `$ref` to a protobuf wrapper and on
`type: [array | object, "null"]`: the contract declares 55 clearable body
fields, the IR carries 40. Those 15 keep the old silence until the parser
carries them, and this record does not fix the parser.

The message is in French, like every message the runtime emits.

## What this record does not decide

What clearing a field means for each endpoint: `null`, `""`, `[]`, a default, a
dedicated endpoint. Issue #114 carries it, and `explicit_nulls` already takes
the set of fields the runtime knows how to clear, empty today, so that their
`null` becomes a request to execute rather than a request to refuse.

Whether an explicit `null` on a field the contract does not declare clearable
should be refused as well. It is still dropped in silence, and so is a `null`
on an action module's body field.
