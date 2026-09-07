# ADR-008. A constraint is translated or named, never guessed and never silent

**Status**: accepted, 7 September 2026. Still in force.

## Context

The generator was good at `type`, `required`, `enum` and `default`. It was blind
to everything else the contract says about a parameter, and the blindness had a
concrete cost: `lb_subscriber` accepted `email_config` **and** `webhook_config`,
which the contract forbids with a shared `x-one-of: config` marker. The API
answered 400. Nothing else in the chain could say so: not the documentation, not
the `argument_spec`, not `ansible-test sanity`, which has no way to know. The
defect was visible only on a user's first playbook.

The danger has moved. It is no longer "the generator picks the wrong `str` or
`int`". It is:

> the module accepts two parameters the API forbids together.

Much subtler, and invisible until the 400.

The parser saw the marker and dropped it, with a comment saying it was a
separate job.

## Decision

Every constraint keyword the contract can carry is in one of three states, and
the report says which:

* **translated** into an `argument_spec` constraint. `x-one-of` becomes
  `mutually_exclusive`;
* **carried by the IR and counted, not yet translated**. Nullability is here: a
  clearable field and an absent field produce the same request today, and
  telling them apart needs a clear/reset semantics the contract does not
  describe. Counting it first is what will size that work;
* **absent from the document**, which is measured and not asserted. A list
  written by hand would stay true on screen and false in the contract the day
  upstream adds the constraint, and the parameter would pass without it.

Two rules follow, and both are the repository's rule 3 applied to constraints:

* **nothing is guessed.** The generator does not invent a `required_one_of`
  because a group looks like it should have one. The contract does not declare
  it, so the module does not require it.
* **nothing is silent.** A keyword found and not translated raises a parser
  warning naming it and its count.

## Consequences

A group whose members are not all options of the module is dropped rather than
narrowed: Ansible refuses to load a module whose `mutually_exclusive` names an
absent option, and it refuses it for **every** call. A badly placed constraint
would break more than it protects.

The report now publishes three different numbers, and their names say what they
count. An earlier version announced `nullable` both as carried and as absent;
both were true, because one counted an OpenAPI 3.0 keyword the contracts never
use and the other counted the 3.1 form they do use. A count with an ambiguous
name is the same defect as a ratio with no denominator.

Nullability stays counted and untranslated, deliberately. That is a debt, it is
named, and it is sized: the report gives the number.

## What this record does not decide

What to do about clearable fields. That needs a semantics the contract does not
carry, and it will be decided when the count says it is worth it.
