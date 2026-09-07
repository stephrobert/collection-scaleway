# ADR-011. A product is admitted, not merely added

**Status**: accepted, 7 September 2026. Still in force.

## Context

Adding a product is the most expensive decision in this repository. It brings a
contract nobody here wrote, dozens of operations to classify, and pages that are
published on Galaxy for good.

Every measurement needed to judge that decision already existed, and none of
them answered it. `mise run report` says a product is classified.
`mise run parser:coverage` says what the parser cannot read. `mise run
docs:quality` says whether the page can be understood. Asked "is it safe to add
RDB?", the only available answer was "the tests pass".

That is not an answer. The tests also pass on a product whose parser ignores
half the constructs, whose pages nobody has read, and half of whose operations
come out `UNKNOWN`.

## Decision

`mise run admission` chains the stages in the order in which they inform each
other, and returns a verdict with an exit code: `0` admitted, `1` error, `2`
refused. It runs in `mise run check`, over every product in the index: adding a
refused product to `products.txt` turns the gate red.

**Not every stage blocks, and that is deliberate.** A gate that refused on every
measurement would refuse both shipped products, so nobody would run it, and it
would measure nothing. The blocking stages are the ones whose failure produces a
**wrong module**:

| stage | blocks | why |
|---|---|---|
| OpenAPI syntactic coverage | no | a construct being present is work to decide, not a defect |
| semantic constraints | yes | a constraint found and silenced gives a module that accepts what the API refuses ([ADR-008](008-a-constraint-is-translated-or-named.md)) |
| clearable fields | no | a known, documented, sized limit ([ADR-008](008-a-constraint-is-translated-or-named.md), issue #114) |
| Day-2 classification | yes | an operation no rule settles is indistinguishable from a forgotten one ([ADR-001](001-no-operation-is-unknown-in-silence.md)) |
| write completeness | yes | a managing module that vanishes silently is indistinguishable from a forgotten one |
| comparison strategies | yes | a managed parameter with no strategy is compared strictly with nobody having decided it ([ADR-009](009-how-a-managed-field-is-compared.md)) |
| documentary coverage | yes | a page is published for good ([ADR-005](005-generated-documentation-behind-a-gate.md)) |

The non-blocking stages print a number. That number is **the price of
admission**, and printing it is the point: a product enters with its price
known, not with its price hidden.

## Consequences

**Excluded with a reason is not missing.** The first version of the write
completeness stage refused `instance_server_user_data`, which the generator does
not write because the contract describes no body field for
`SetServerUserData`: the module would not know what to send. The reason is
carried and published. A gate that confuses the two punishes exactly the
behaviour this repository asks for, and it found that out on a shipped product
the first time it ran.

Both current products are admitted. Their price is the response codes the
parser does not read, two for Instance and one for the Load Balancer, and forty
clearable fields between them. The first version of this record said "two
unhandled OpenAPI constructs each": the parser coverage report filed
`oneOf: [T, null]`, which the parser translates, under the same "unhandled" line
as a real union of shapes, and the gate charged the Load Balancer for it. Issue
#120 separated the two counts, and the corrected price is the one above.

The gate reuses the other measurements rather than recomputing them. Reading
their printed output would make a second reader of the same calculation, and the
two would diverge at the first formatting change; `parser_coverage` was split
into a function that measures and one that prints, for that reason.

## What this record does not decide

Whether a product is worth adding at all. That is a judgement about users, and
no gate makes it.
