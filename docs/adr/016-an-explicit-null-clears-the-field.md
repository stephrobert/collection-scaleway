# ADR-016. An explicit null clears the field, and an omitted option touches nothing

**Status**: accepted, 8 September 2026. Still in force.
Supersedes [ADR-012](012-an-explicit-null-is-refused-never-ignored.md).

## Context

The contract marks a writable field as clearable with `oneOf: [T, null]` or
`type: [T, "null"]`. Ansible does not tell an omitted option from an explicit
`null`: `module.params` carries `None` in both cases, so `description: null`
and `description` absent produced the same request, and the module reported
`ok` on a description that was still there.

[ADR-012](012-an-explicit-null-is-refused-never-ignored.md) closed the false
success by refusing the `null`. It bought that refusal with a marker default on
a `raw` option, and `validate-modules` requires whatever the module declares to
be published: the page then showed `type: raw` and `default: __unchanged__` on
every clearable option, and the description had to restore the type the type
field no longer carried. The playbook still could not clear anything.

That record measured five candidate mechanisms and ruled out `fallback` on this
line:

> `type: str` or `raw`, marker `fallback`: distinguishable, everywhere, **but**
> `mutually_exclusive` then fails on every call.

The measurement was right and its scope was too narrow. It measured a fallback
that **returns** a value. Ansible applies a fallback before counting present
keys, so a returned value makes the key present, and mutual exclusion fires on
every call. A fallback that **raises** `AnsibleFallbackNotFound` injects
nothing, and Ansible calls it only when the key is absent from the invocation.
That is a witness, not a value, and it was never measured.

Measured on 2.17.14, 2.18.19, 2.19.12, 2.20.8 and 2.21.3, on `str`, `int`,
`bool`, `list` and `dict`, with `ArgumentSpecValidator`, the validator
`AnsibleModule` itself uses:

| what the invocation does | the witness fires | `module.params` |
|---|---|---|
| omits the key | yes | `None` |
| writes `key: null` | no | `None` |
| writes a value | no | the converted value |

`mutually_exclusive` accepts a single provided option and still refuses two, on
all five versions. The option keeps its `type`, its `choices` and its
`elements`, and nothing about the mechanism reaches the page.

Two facts bound the decision, and both were measured on the contracts in the
tree rather than assumed:

* no clearable field carries an enum, so the case where Ansible refuses `null`
  against `choices` before the module sees it does not exist today;
* no clearable field carries a contract default. A default matters because
  Ansible then converts an explicit `null` toward the option type, and
  `description: null` reaches the module as `''`: clearing would become
  indistinguishable from writing an empty value.

## Decision

**An explicit `null` on a field the contract declares clearable is a clearing
request, and the module honours it.** The generated module calls
`poser_les_temoins(ARGUMENT_SPEC, MODULE.nullable_params)` before building its
`AnsibleModule`, and passes the resulting set to the runtime. The runtime treats
a clearable field that is `None` and absent from that set as cleared, and sends
it in the request body with the value `null`, which is what the contract
sanctions by declaring the field clearable.

**A clearable option is published exactly like any other option.** Its `type`,
`choices` and `elements` are those of the contract; it carries no default and no
marker. Two sentences of its description say what `null` does and what omitting
does, because the criterion of this repository is that a module is understood
from its page alone.

**What clearing produces is checked, not guessed.** The contract says a field
accepts `null`; it does not say what the reread will show. The postcondition
check of [ADR-010](010-postconditions-are-checked-not-announced.md) covers a
cleared field like any other written value, and names it when the API returns
something else. No exception was added for clearing.

**A contract default on a clearable field is refused at generation.** The
generator raises rather than produce a module where clearing and writing an
empty value cannot be told apart. No field is in that case; the refusal waits
for the one that will be.

**A module that declares clearable fields without a witness fails.** Passing no
witness is not the same as passing an empty one: the first says nothing was
posted, the second says nothing was omitted. Confusing them would make every
omitted option a clearing request, so the runtime refuses instead of guessing.

## Consequences

`type: raw` and the marker default leave the collection, and with them the
runtime code that stripped the marker and revalidated the provided value
against a second copy of the option entry. That second copy is gone too: the
witness is posted on the entry the module already publishes, so the type is
described once.

The mechanism is a public API used for a purpose it was not designed for. A
fallback is meant to supply a value; this one supplies none and records a name.
Nothing in Ansible promises that a fallback is called only on an absent key, so
the property is measured by a test that interrogates `ArgumentSpecValidator`
rather than asserted in prose, and that test turns red on the version where the
property stops holding.

The witness set fills during `AnsibleModule.__init__` and is read after it. A
module process handles one invocation, so there is one set per process; the
tests that build several modules in one process clear it explicitly.

An explicit `null` on a field the contract does **not** declare clearable is
still dropped in silence, and so is a `null` on an action module's body field.
Clearing has no meaning on an action body, whose fields describe one call rather
than a persistent resource.

## What this record does not decide

Whether the API returns `null`, `""` or `[]` after a clearing, per endpoint.
The postcondition check measures it on every run and names the field when the
reread disagrees; a field where the API normalises to an empty value rather than
to `null` will need a comparison strategy, chosen by
[ADR-009](009-how-a-managed-field-is-compared.md) and written as an override
with its reason.
