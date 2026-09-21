# ADR-025. A versioned milestone is not a roadmap

**Status**: accepted, 21 September 2026. Still in force.

## Context

The 0.8.0 milestone closed at 23 issues, and it worked: one product, Kubernetes,
plus the fleet-memory work that made it useful. The next one did not inherit
that shape.

Read on the day 0.8.0 shipped, 0.9.0 held **14 open issues and nothing closed**,
and they were not one body of work:

```text
6  new products      Block, Public Gateway, Elastic Metal, Audit Trail,
                     VPC/IPAM, Secret Manager
3  Kubernetes debt   left over from the version already published
1  cross-cutting     an idempotence defect first measured on a load balancer
2  audit output      making findings leave the repository
2  other
```

Three facts settle this, and none of them is about taste.

**Six products is not a version.** Admitting a product costs an admission
verdict (ADR-011), a versioned contract, overrides with their reasons, modules,
an extended example platform, and a real-cloud run. 0.8.0 paid that price
**once**. The repository generates three products today and follows four more
without generating them; a milestone proposing six at once proposes to more than
double the surface in one release.

**Five of the fourteen carried no priority at all**, and they were exactly the
products, opened in one batch. More than a third unprioritised means nobody
arbitrated: nothing distinguished the core from the ambition.

**The title promised something already delivered.** "Guider, et éclairer les
angles morts" repeated a promise the previous version had kept, with the Kapsule
guide. The word covered two different things, a written guide and operational
guidance, and the milestone could not say which one it owed.

A milestone in that state cannot close. It is read as a wish list, and a wish
list nobody can finish stops being read at all, which is the same failure mode
this repository refuses for reports and counters.

## Decision

**A versioned milestone holds only the work the version actually depends on.**
Candidate products, continuous proof, upstream tracking and governance live in
**unversioned milestones** until something is explicitly promoted out of them.

The reservoir holds the opportunities; the versioned milestone holds the
commitments. The difference is not bookkeeping: an issue in a version is a
promise to somebody waiting for that version.

Four conditions, checked when a milestone takes a number:

```text
at most two new product lots
every issue prioritised
no exploratory issue
no real-cloud target left to invent after the issue enters the milestone
```

**A product lot is counted honestly, and so are the API surfaces it touches.**
VPC and IPAM ship as one lot and two surfaces; adding Public Gateway makes two
lots and three surfaces. Counting one number and publishing the other would
dress the metric up, which is exactly what the coverage rules already forbid.

**A product is ranked on operational value against cost of proof**, never on how
interesting it is. VPC/IPAM comes first because both contracts are already
tracked and the inventory already consumes them: the target exists, and nothing
has to be built to exercise it. Elastic Metal comes last for the opposite
reason, not because it matters less.

## Consequences

**A version can be refused entry, and that is the point.** Work that is ready,
valuable and wanted will sometimes sit in a reservoir because the version it
would join is already full. The cost is visible impatience; the alternative is a
milestone that never closes.

**The reservoir will grow, and that is not a backlog rotting.** An issue there
is not waiting for someone's attention: it is waiting for an admission verdict
and a way to prove it. Both are nameable, so both can be argued with.

**This record does not make the count automatic.** Nothing in the repository
refuses a fifteenth issue or an unprioritised one. That was a deliberate choice
here and it is the weak point: every other rule this project holds is executable,
and this one is read. It becomes a guard the day it is broken twice.

**Renaming a milestone rewrites what a version promised.** The old title is not
kept anywhere, and the issues that left carry no trace of having been in it. A
reader six months from now sees the result, not the arbitration, which is what
this record is for.

## What this record does not decide

It does not decide which products enter the collection; ADR-011 admits a
product, ADR-013 dates what it ships, ADR-022 places it relative to the official
collection.

It does not decide what a release must prove before publishing; ADR-024 settles
that, and `release:check` enforces it.
