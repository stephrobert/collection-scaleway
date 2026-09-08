# ADR-018. A retry policy belongs to the operation, and an action is never replayed

**Status**: accepted, 8 September 2026. Still in force.

## Context

The runtime had no retry at all: one request, one response. On a cloud that
makes a playbook fragile for nothing, because a `503` lasting thirty seconds
fails an entire deployment.

The obvious fix is the wrong one. A `Retry(total=5)` on a `requests` session, or
any policy held by the client, applies the same rule to a `GET` and to the
`POST` that reboots a machine. A reboot played twice is not a reboot. The
policy has to belong to the operation, the way a comparison strategy belongs to
the field ([ADR-009](009-how-a-managed-field-is-compared.md)).

What the policy can be derived from is narrow, and that is deliberate. No
Scaleway document declares an operation idempotent, none carries an idempotency
key, and none says which failures are safe to replay. Two facts remain, and
both are stated rather than guessed: the HTTP method, whose safety RFC 9110
fixes, and the class the classifier established.

The families of failure are not equivalent either:

* a `429` is the rate limiter answering **before** the API. The request was not
  processed, so replaying it changes nothing that has not already been changed;
* a `500`, `502`, `503` or `504` is ambiguous. After one of them, a write may
  have landed and only a read could tell;
* a transport failure, a timeout or a refused connection, is the most ambiguous
  of all: the request may have left.

## Decision

**Every operation carries a retry policy, and the generator derives it** from
the HTTP method and the operation class. Three values, and the class is tested
first because `ServerAction` is a `POST` exactly as a creation would be:

| policy | which operations | replayed on |
|---|---|---|
| `safe` | `GET`, so every read | `429`, the ambiguous `5xx`, transport failures |
| `limited` | the writes of a managing module | `429` only |
| `never` | the operation an action module triggers | nothing |

**`limited` does not replay an ambiguous failure.** After a `502` the write may
have landed, and this runtime prefers to fail loudly rather than report a state
it did not observe, which is the same rule the postcondition check applies
([ADR-010](010-postconditions-are-checked-not-announced.md)).

**`Retry-After` is honoured, in both forms RFC 9110 allows**, a number of
seconds or an HTTP date. Reading only one of them would ignore the other in
silence and replay too early against an API that just said no. An unreadable
header falls back to the default wait rather than failing the module: the
server already said the essential by answering 429.

**A `Retry-After` beyond the ceiling is not waited for.** The server can
announce minutes; obeying blindly would make a module that looks frozen, and the
error that comes out carries the header in its message.

**The runtime default is `never`.** A module produced by an older generator,
declaring nothing, must not start replaying writes because this runtime learned
how.

**The retry lives around the single HTTP call, and nowhere else.** Putting it in
`request` would make every caller responsible for knowing whether it had already
been replayed; putting it in a `requests` session would make it global, hence
identical for a read and for a reboot, which is what this record refuses.

## Consequences

An operation that deserves a different policy than the derivation gives has no
way to say so yet. `depuis_le_nom` exists and refuses an invented value, so an
override can be wired the day a case appears; until then, adding the plumbing
would be building for a case nobody has met.

The waits are a plain increasing sequence rather than an exponential backoff
with jitter. The exact values are not what matters here, and a formula nobody
can read is a formula nobody can judge. If a measurement ever shows the
sequence matters, it will be changed with that measurement.

A `limited` write that fails on a `503` fails the playbook where a replay might
have succeeded. That is the price, and it is the direction this repository errs
in everywhere else: a module that reports what it did not observe is worse than
a module that fails.

Nothing here was measured against a real `429` or a real `503` from Scaleway:
the behaviour on those codes is derived from RFC 9110 and from what the codes
mean, not from an observation. The tests fabricate the responses.

## What this record does not decide

Whether a failed write should be reconciled by re-reading and comparing before
deciding to replay. That would be a stronger guarantee than failing, and it
needs the read to be cheap and the comparison to be exact for every managed
field. [ADR-010](010-postconditions-are-checked-not-announced.md) already reads
after a successful write; extending it to an ambiguous failure is a separate
decision.
