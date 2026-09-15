# ADR-024. A recorded run is a file, so the fourth tier of proof can be published

**Status**: accepted, 15 September 2026. Still in force.

## Context

This repository separates four tiers of proof, and the separation is the point:

```text
classified               no rule asks for it to be written by hand
carried by a module      a module exists and calls it
called by the example    the playbook names the module
played against a target  a run actually exercised it
```

The first three are derived into published blocks. The fourth was deliberately
excluded, and the reason was written down: it depends on an execution, and a
derived block has to recompute offline.

That exclusion held until a guide needed the fourth tier. Kubernetes has no
middle tier at all: the local emulator does not serve `/k8s/v1`, so there are
unit tests and then the real cloud, with nothing in between. A page describing
how to operate a Kapsule cluster that could not say which modules had ever
reached the real API would be asking people to trust a table written by hand,
about an API they are being billed for.

An external audit on 15 September 2026 had just made the general form of that
objection: claims that outlive what measured them. Writing the matrix by hand
would have created one on the same day the audit named the category.

**What changed the answer is that the run was recorded.** The proxy in front of
the real API wrote every request to a JSONL file, which is versioned in the
repository. It carries the method, the path, the status and the user agent of
everything that went over the wire. It is a file, so it is readable offline, and
the objection that kept the fourth tier out of published documents does not
apply to it.

Three facts came out of building the join, and they are why this record exists
rather than a comment:

* **the first attempt measured nothing, and said nothing.** It filtered emitted
  routes on the longest prefix the module templates share, which for `k8s` is
  `/k8s/v1/regions/{region}/`: a template, matching no concrete path. Every
  route of the run was discarded before any matching happened, every module came
  out "not reached", and the table was perfectly readable and entirely false;
* **the guard against that failure was inert twice.** Both early versions
  counted "routes belonging to this product" by reusing the very filter they
  were meant to be watching, so each was disabled in exactly the case it existed
  to catch. Only a test that neutralised the filter showed it;
* **the derivation contradicted the hand-written table on two rows.** A read can
  belong to two modules: `GET /pools/{id}` is the info module's read and also the
  read a MANAGE module performs before writing (ADR-003). The request went out;
  nothing in the recording says which module sent it.

## Decision

**A recorded run is a versioned file, and the fourth tier of proof is derived
from it into published blocks like the other three.** The recording is the
source; no table of what ran is written by hand.

**A route that more than one module carries proves none of them.** The published
states are three, not two:

| state | what it means |
|---|---|
| reached | a route only this module carries went over the wire |
| shared route only | every route of its that circulated is carried by another module too |
| not reached | none of its routes circulated |

Collapsing the middle state into either neighbour would be a lie in one
direction or the other, and the direction would be decided by alphabetical
order.

**A request whose author cannot be read is an error, never a request that does
not count.** The recording carries several agents: this collection, the
Terraform provider that built the platform, and the residue fingerprints. A line
with no readable agent stops the measurement rather than being silently
attributed.

**A recording states its date, and the date is cross-checked.** The filename
carries it and the timestamps must agree. Renaming a file costs a second, and
would republish an old measurement under a fresh date.

**A guard over a derivation must not consult the derivation it guards.** This is
the general form of the defect above, and it is the part of this record most
likely to matter somewhere else.

## Consequences

**A run that is not recorded proves nothing publishable.** Anyone qualifying a
product against the real cloud must run it behind the recording proxy, or the
guide for that product cannot carry a proof table. That is a real constraint on
how a qualification run is done, and it is deliberate.

**The recording is a file in the repository, and it holds request metadata.** No
bodies, no credentials, no tokens: methods, paths, statuses and headers. A
recording that carried a payload would be a secret in a public repository, and
nothing here checks that for you.

**A proof table ages by construction, and it should.** It says "run of
2026-09-14", not "supported". A module added after that date comes out "not
reached" until somebody runs it, which is exactly the pressure this tier is for.

**Published tables now disagree with each other on purpose.** A module can be
called by the example and not reached by a run, and both blocks are right. The
two tiers answer different questions, and the guides have to keep saying which.

## What this record does not decide

It does not decide which products are qualified against the real cloud, nor when
a run is required before a release; ADR-011 admits a product, ADR-006 settles
what the emulator is worth.

It does not decide anything about documentation as a condition of done, which
the same audit raised and ADR-023 explicitly left open. This record makes one
guide possible to write honestly; it does not say when a guide is owed.
