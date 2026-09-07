# ADR-006. The emulator is a proof, not the proof of the real cloud

**Status**: accepted, 4 September 2026. Still in force.

## Context

`feint` is a local emulator of the Scaleway API. It lets every playbook in this
repository run on every pull request, with no credentials and no spend, and it
is what makes `SCW_API_URL` honoured end to end worth having.

It is also the most dangerous artefact in the repository, for exactly that
reason: a green run against an emulator reads identically to a green run against
the cloud, and it is not the same claim.

## Decision

The emulator proves the **shape** of a run: that the module builds its request,
that a second pass returns `changed=false`, that the inventory joins its
addresses, that a playbook resolves by its fully qualified name. It never proves
the cloud.

What it does not apply is written down rather than assumed: quotas, per-zone
availability, propagation delays, error bodies on conflicting states, the real
`400` on a reused IP. Each of those has cost a diagnosis at least once.

So a change that touches a module, a plugin or an inventory option is not
finished until it has run **against the real account**, framed by the residue
check: `mise run example:reel`, then `mise run example:residu`. The zero-residue
rule is not politeness, it is what makes the next real run mean something.

## Consequences

Four stages of proof exist and none is a substitute for another: classified,
carried by a module, called by the example, played against a target. The first
three are computable offline and belong in the README's derived blocks; the
fourth depends on a run and does not, which is why `mise run coverage:example`
publishes it separately, and says "no run recorded" rather than "0 %" when
there is none. Nothing was measured is not nothing worked.

## What this record does not decide

Which operations get a module at all. That is [ADR-002](002-day-2-only.md).
