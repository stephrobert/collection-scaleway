# ADR-023. A product is known to every seam, or its absence is declared

**Status**: accepted, 15 September 2026. Still in force.

## Context

An external audit of the 0.8.0 branch raised six release-blocking defects. Three
of them were the same defect wearing three hats:

```text
fleet_audit passed only Instance zones to audit_changes,
  so a Kapsule finding could never become "resolved"

the snapshot schema said "zones" where Kapsule has regions,
  and the normaliser filed a region under a field named zone to fit

fleet_report did not read Kapsule at all,
  so the version that adds fleet memory could not remember a cluster
```

None of these was a hard failure. Each produced a plausible report that was
quietly wrong, which is the failure mode this repository is built to refuse
everywhere else.

The cause is structural rather than careless. Adding a product touches a seam
(`resource_facts`), and then touches six other places that consume what that
seam produces: the snapshot schema, the diff's compared fields, the selector's
field table, two roles' read lists, and the documentation. Nothing connected the
first to the rest. Kubernetes was added carefully, reviewed, measured against
the real cloud, and still left three consumers behind.

A checklist in a document would not have helped. Nobody reads a checklist while
adding a normaliser; the repository already knows this, which is why
`/falsify` exists rather than a note saying "remember to test your guards".

The audit also raised a second family, which this record does not decide: a
claim that outlived what measured it, and documentation that was never in any
definition of done. Those are real, and they are different problems.

## Decision

**The set of products is derived from one place, and every consumer is checked
against it.** `resource_facts.NORMALISEURS` is that place. A product added there
makes the guard red everywhere it is not yet known.

What every product must have, and what each absence costs if it is missing:

| seam | what its absence produces |
|---|---|
| declared fields | a shape nothing describes: fields no rule can judge, or promised and absent |
| a selector table | selection finds nothing, which reads exactly like an empty fleet |
| compared fields, or a declared witness | a change comes out unnamed, on the field that mattered |
| a typed scope | a region compared against a zone, silently |
| an option on each role that reads it | the role decides somebody's API bill |

**An absence is declared with its reason, never left implicit.** The exemption
table carries what would close it, the same way example coverage does. A product
missing from a consumer without a reason is a defect; with a reason it is a
decision, and the reason is what a later reader argues with.

**The guard derives, it does not enumerate.** A list of products written a second
time inside the test would drift from the first, and it is the second list that
would forget the new product. This is the same rule the repository applies to
contracts, to golden files and to derived counters.

## Consequences

**Adding a product costs more up front**, and that is the point. The cost was
already there; it was paid later, by somebody reading a report that was wrong.

**The guard can be satisfied without being satisfying.** A product can be added
to every table with a plausible-looking entry and still be wrong in substance,
exactly as a module can be generated and never run. This guard closes the
structural gap, not the semantic one; the three tiers of proof still apply.

**It found a defect on its first run.** `k8s_pool` was normalised and unknown to
the selector, written minutes earlier in the same session that wrote the guard.
That is the strongest argument for it, and also a warning: the author of a change
is the worst-placed person to notice what it left behind.

**The exemption table will grow, and each line is a small debt.** An empty table
today is not a promise that it stays empty. What matters is that adding a line
requires writing why, in front of somebody.

## What this record does not decide

It does not decide which products the collection supports; ADR-013 and ADR-022
do that.

It does not decide anything about claims that outlive their measurement, nor
about documentation as a condition of done. Both were raised by the same audit
and both deserve their own decision, once what they should say has been
measured rather than guessed.
