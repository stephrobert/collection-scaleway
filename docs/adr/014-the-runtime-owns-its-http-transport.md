# ADR-014. The runtime owns its HTTP transport

**Status**: accepted, 8 September 2026. Still in force.

## Context

The Scaleway Python SDK is the collection's dependency, and the generator uses
its `Client` and `Profile` to hold credentials. What remained open was how a
generated module reaches an operation.

The first answer, recorded in the runtime architecture page as "Decision 1", was
`scaleway_core.api.API._request(method, path, ...)`. It kept the contract as the
only source: the generator guesses no SDK method name from an `operationId`, and
the IR already carries `http_method` and `path`. The price was named at the
time, and accepted: a dependency on a method whose name starts with an
underscore, held by a guard that checked its signature.

Two measurements closed that question.

**The SDK passes no timeout.** Read in its source: `API._request` calls
`requests.request()` without one. A connection that opens and never answers
holds a module forever, and `wait_timeout` does not help, because it bounds a
wait loop rather than a single call. No playbook should carry that risk, and no
guard on a signature would have caught it: the signature was correct, the
behaviour was not.

**An underscore is not a contract.** A minor release of the SDK may move
`_request` without promising anything to anyone. The guard on its signature
turned that into a red build instead of a broken playbook, which was the right
mitigation for a dependency that should not have existed.

The migration happened before 0.4.0 and the changelog described it. What did not
happen is the record: the architecture page kept describing the reversed
decision, and it is the page a contributor reads to understand why the runtime
has the shape it has (#131). Worse, the replacement carried the same defect one
floor down: to hand the paginator the `x-total-count` header, the runtime wrote
`requests.Response._content`, a private attribute of a third-party library, in
code written to stop depending on one (#132).

## Decision

**The runtime composes its own HTTP request, and owns every responsibility that
comes with it.** The SDK supplies the profile and the credentials; it does not
execute.

Each responsibility has one place in `plugins/module_utils/scaleway.py`:

| responsibility | where |
|---|---|
| authentication headers, user agent, content type | `ScalewayApi._send` |
| query parameter serialisation, a list becoming repeated pairs | `ScalewayApi._send` |
| timeout, per call, from the `api_timeout` option | `ScalewayApi._send` |
| TLS, and the `api_allow_insecure` escape for an emulator | `ScalewayApi._send` |
| error translation, without ever copying the response body | `_error_from_response` |
| reading the body, and carrying `x-total-count` into it | `ScalewayApi.request`, `_avec_total_count` |
| pagination, and the three conditions that stop it | `paginate` |

**No private attribute of a third-party library is read or written in what is
shipped.** The rule now has a control rather than a paragraph: `mise run
api:privee` reads `plugins/` and refuses an underscored attribute on anything
but `self`. It cannot infer types, so it refuses what it cannot justify; in
shipped code, an underscore on something that is not one's own asks to be
argued, and an argument gets written down.

Carrying `x-total-count` therefore merges into the **body that was read**, never
into the response object. The need was never to change the response: it was to
give its reader what the header knows.

## Consequences

**The collection now maintains an HTTP client.** Retries, connection pooling and
proxy handling are ours to decide rather than inherited. None of them is
implemented today, and that is a deliberate gap rather than an oversight: #91
carries the retry policy, per kind of operation, because retrying a `POST` that
triggers an action is not the same act as retrying a `GET`.

**The SDK stays a dependency, for a narrower purpose.** Its profile resolution,
its configuration file format and its credential validation are used as they
are. A future release that changed `Client` or `Profile` would still reach us;
what no longer reaches us is a change to how it sends requests.

**One dependency was traded for another.** `requests` is now used directly, and
it is what `ansible-core` and the SDK already pull in. It has a public API, and
the control above is what keeps us on it.

## What this record does not decide

Whether an operation should be retried, and under which conditions: #91.

ADR-003 decides what a managing module sends and why a `PUT` reads first; this
record decides how anything is sent at all.
