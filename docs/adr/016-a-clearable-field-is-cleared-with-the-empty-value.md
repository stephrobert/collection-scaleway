# ADR-016. A clearable field is cleared with the empty value of its type, and an explicit null is refused

**Status**: accepted, 8 September 2026. Still in force.
Supersedes [ADR-012](012-an-explicit-null-is-refused-never-ignored.md).

## Context

The contract marks a writable field as clearable with `oneOf: [T, null]` or
`type: [T, "null"]`. Ansible does not tell an omitted option from an explicit
`null`: `module.params` carries `None` in both cases, so `description: null`
and `description` absent produced the same request, and the module reported
`ok` on a description that was still there.

[ADR-012](012-an-explicit-null-is-refused-never-ignored.md) closed the false
success by refusing the `null`, and was right to. It bought the refusal with a
marker default on a `raw` option, and `validate-modules` requires whatever the
module declares to be published: the page then showed `type: raw` and
`default: __unchanged__` on every clearable option, and the description had to
restore the type the type field no longer carried. That record also left open
what clearing means, and its refusal could not tell the reader what to write
instead.

Two things were measured before deciding.

**How to tell an omitted option from an explicit null, at no cost on the
page.** ADR-012 had ruled out `fallback` on this line:

> `type: str` or `raw`, marker `fallback`: distinguishable, everywhere, **but**
> `mutually_exclusive` then fails on every call.

The measurement was right and its scope was too narrow. It measured a fallback
that **returns** a value. Ansible applies a fallback before counting present
keys, so a returned value makes the key present, and mutual exclusion fires on
every call. A fallback that **raises** `AnsibleFallbackNotFound` injects
nothing, and Ansible calls it only when the key is absent from the invocation.
That is a witness, not a value, and it was never measured. On 2.17.14,
2.18.19, 2.19.12, 2.20.8 and 2.21.3, across `str`, `int`, `bool`, `list` and
`dict`:

| what the invocation does | the witness fires | `module.params` |
|---|---|---|
| omits the key | yes | `None` |
| writes `key: null` | no | `None` |
| writes a value | no | the converted value |

`mutually_exclusive` accepts a single provided option and still refuses two, on
all five versions. The option keeps its `type`, its `choices` and its
`elements`, and nothing about the mechanism reaches the page.

**What clearing actually is.** This was measured on the real account on
8 September 2026, on a security group created for the measurement and deleted
after, with the residue check green on both sides:

| body sent | status | reread |
|---|---|---|
| `{"description": null}` | 200 | `'une description à effacer'`, unchanged |
| `{"description": ""}` | 200 | `''`, cleared |
| `{"tags": null}` | 200 | `['un', 'deux']`, unchanged |
| `{"tags": []}` | 200 | `[]`, cleared |
| `{"stateful": null}` | **400** | `True` |
| `{"stateful": false}` | 200 | `False` |

The API accepts `null` on a field the contract calls clearable, answers 200,
and changes nothing. The last two rows confirm it from the other end:
`stateful` is **not** declared clearable, and there `null` is rejected outright.

That is coherent, and the explanation is upstream of Scaleway. The nullability
the parser reads sits behind a `$ref` to a protobuf wrapper type
(`google.protobuf.StringValue` and its family), whose whole purpose is to say
"field not set" over the wire. Declaring a field clearable means *the decoder
accepts null*, and `null` means *I am not talking about this field*. It is the
wire-level twin of an omitted key, not a clearing instruction.

A first implementation of this record sent the `null` and let the postcondition
check of [ADR-010](010-postconditions-are-checked-not-announced.md) judge the
reread. It worked exactly as designed and failed the module, both against the
emulator and against the real account, with a message about normalisation where
there was none. The measurement above is what replaced it.

## Decision

**Clearing a field is writing the empty value of its type.** `description: ""`,
`tags: []`, `config: {}`. This needs no mechanism at all: an empty value goes
down the ordinary path, is compared by the ordinary strategy, and is checked by
the ordinary postcondition. A second run reports no change.

**An explicit `null` is refused, before anything is read, and the refusal names
what to write.** The message states the empty value of that option's type,
literally, so it can be copied. For a type with no empty value, `int` and
`bool`, it says so instead of inventing one: `0` and `false` are values a
playbook can already write, not absences.

**The refusal needs the omission witness, and that is the whole reason it
exists.** Without it, refusing every `None` would refuse every playbook that
does not write all of its options.

**A clearable option is published exactly like any other option.** Its `type`,
`choices` and `elements` are those of the contract; it carries no default and
no marker. Its description says how to clear it, and that `null` is refused,
because the criterion of this repository is that a module is understood from
its page alone.

**A contract default on a clearable field is refused at generation.** With a
default, Ansible converts an explicit `null` toward the option type and
`description: null` reaches the module as `''`, which would make a refused
`null` indistinguishable from a legitimate clearing. No field is in that case;
the refusal waits for the one that will be.

**A module that declares clearable fields without a witness fails.** Passing no
witness is not the same as passing an empty one: the first says nothing was
posted, the second says nothing was omitted. Confusing them would refuse every
omitted option, so the runtime refuses to guess.

## Consequences

`type: raw` and the marker default leave the collection, and with them the
runtime code that stripped the marker and revalidated the provided value
against a second copy of the option entry. The type is described once, on the
published entry, and the witness reads it there to build its message.

Clearing works today for `str`, `list` and `dict`. It does not work for `int`
and `bool`, and no module can make it work: the API offers no representation of
an empty integer. The page says so on each of those options rather than leave
the reader to discover it. Some of them carry a documented sentinel in their
own contract description, `Use 0 value to disable` for instance, and that
sentence is published as it stands: it belongs to the field, not to this rule.

The mechanism is a public API used for a purpose it was not designed for. A
fallback is meant to supply a value; this one supplies none and records a name.
Nothing in Ansible promises that a fallback is called only on an absent key, so
the property is measured by a test that interrogates `ArgumentSpecValidator`
rather than asserted in prose, and that test turns red on the version where the
property stops holding.

The witness fills during `AnsibleModule.__init__` and is read after it. A
module process handles one invocation, so there is one witness per process; the
tests that build several modules in one process clear it explicitly.

An explicit `null` on a field the contract does **not** declare clearable is
still dropped in silence by the module, and the API rejects it in 400 if it
ever reaches it. A `null` on an action module's body field is also still
dropped: clearing has no meaning on an action body, whose fields describe one
call rather than a persistent resource.

## What this record does not decide

Whether the empty value clears on every endpoint, or only on the ones measured
here. `UpdateSecurityGroup` was measured on `str` and on `list`. A field where
the API normalises differently will surface through the postcondition check,
which names it, and will be handled by a comparison strategy chosen under
[ADR-009](009-how-a-managed-field-is-compared.md) and written as an override
with its reason.
