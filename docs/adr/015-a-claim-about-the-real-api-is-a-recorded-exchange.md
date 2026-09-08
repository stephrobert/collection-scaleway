# ADR-015. A claim about the real API is a recorded exchange, not a green assertion

**Status**: accepted, 8 September 2026. Still in force.

## Context

[ADR-006](006-the-emulator-is-a-proof-not-the-proof.md) settles that the local
emulator proves the shape of a run and never the real cloud. It does not settle
how the real cloud gets measured, and the answer in practice was: an assertion
in `examples/playbooks/modules.yml`, run against the `reel` target.

Issue #119 asked one question that only the real API could answer. Does it
preserve the order of `certificate_ids`? The answer decides whether a managing
module is idempotent, and [ADR-009](009-how-a-managed-field-is-compared.md)
explicitly waits for somebody to observe before adopting `set`.

Three billed runs were needed, and the first two returned **nothing** about the
question:

* the first died at `terraform apply`, on a self-signed certificate Scaleway
  refused for carrying no DNS name. Worse, the destroy could not run: the git
  branch had been switched while the platform was up, and the versioned
  Terraform lock no longer declared the provider the deployment used. **41 billed
  resources survived** (#148);
* the second deployed, and an assertion counting frontends failed at task 43 of
  96 because the measurement's own TLS frontend made the count two. The play
  died there, carrying the measurement with it. 45 resources created and
  destroyed, zero data;
* the third recorded every exchange through `feint proxy`. The measurement task
  was skipped again, for a third and different reason, and **the answer was in
  the transcript anyway**:

```text
seq 277  CreateFrontend  sent [cfcb677d, 28856172]  returned [cfcb677d, 28856172]
seq 286  UpdateFrontend  sent [cfcb677d, 28856172]  returned [cfcb677d, 28856172]
seq 288  GetFrontend                                returned [28856172, cfcb677d]
seq 467  GetFrontend                                returned [28856172, cfcb677d]
```

The write answers in the order asked; the **read reverses it**, stably, two
hundred exchanges apart. `ordered_list` was the wrong fallback, and no assertion
had ever said so.

The difference is not luck. **An assertion returns a boolean.** When it fails it
says what it expected, never what the API answered, and a play that dies on one
carries away everything after it. A recording is not conditional on the
playbook's control flow: it captures what crossed the wire.

## Decision

**A claim about the real API is established by a recorded exchange.** Assertions
keep their job, which is to fail a run; they are not the evidence.

`python scripts/example.py reel --enregistrer <file>` puts `feint proxy` between
the collection and the cloud. It forwards and records; it never answers in the
cloud's place, which is what separates it from the emulator and what makes its
transcript a measurement of the API rather than of an imitation. The two listen
on different addresses so they can never be confused.

Three properties the wiring must hold, each learnt by getting it wrong:

* the proxy stops **after** the destroy. An interrupted playbook can have a call
  in flight, and cutting early loses the end of the transcript, which is exactly
  what failed;
* the run **refuses to start** if the proxy is not listening. A billed run that
  records nothing is the worst of both;
* Terraform goes through it too. That is measured, not assumed: the stack leaves
  `api_url` null on the real target, so the provider reads `SCW_API_URL` like the
  modules do, and a transcript carries thirty-two create and delete operations no
  module of this collection emits. The first comment written here claimed the
  opposite, and the transcript disproved it.

An override that changes a comparison strategy **quotes the transcript**: the
sequence numbers, what was sent, what came back. A reader must be able to
disagree with the conclusion by reading the same lines.

## Consequences

**A measurement now costs a billed run, and produces a durable artefact.** The
transcript outlives the run, and is what a feint issue needs the day the
emulator serves the same routes. Credentials never reach it: redaction is a
property of the recorded type in feint, not a rule someone remembers.

**The example playbooks keep their assertions**, and they stay fragile in the
same way: one failure ends the play. That is acceptable now that the evidence no
longer depends on reaching the end.

**Nothing here makes a run cheap.** The three runs that produced this record cost
real money on a real account, and the residue control is what made them safe to
repeat. Recording lowers the number of runs needed per question; it does not
lower the price of one.

## What this record does not decide

Whether a platform may be deployed at all, and what the residue rule requires:
that is the `example-stack-author` skill, and #148 carries the execution lock
that would have prevented the first run's survivors.

ADR-009 decides how a managed field is compared; this record decides what counts
as grounds for changing that comparison.
