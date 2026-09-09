# ADR-017. The launcher removes what blocks its own destruction, once, and says so

**Status**: accepted, 8 September 2026. Still in force.

## Context

No resource created by an example may outlive its run, and the destruction runs
in a `finally` so that a failed playbook does not change that.
[ADR-015](015-a-claim-about-the-real-api-is-a-recorded-exchange.md) recorded the
first time that promise broke: the `finally` had run, and the destruction it
launched could not execute because the git tree had moved under the deployment.
The lesson written then was that a `finally` only protects if the command it
launches can still run.

On 8 September 2026 the promise broke again, for a different reason, and this
one is inside the stack. `terraform destroy` ran, five times, and each time
returned:

```text
Error: scaleway-sdk-go: precondition failed: ,
       Can't delete a private network interface attached to a server
```

30 billed resources stayed up: five servers, two Block volumes, an Instance IP,
three security groups, a placement group, nine IPAM addresses and a private
network. The residue check did its job and named every one of them with its id,
which is how they were found and removed.

The cause is an ordering the dependency graph gets backwards.
`scaleway_instance_private_nic` carries a `server_id`, so Terraform destroys the
card **before** the server, and the API refuses to delete a card that is
attached. Two things were measured while cleaning up:

* stopping the servers does not help. The destruction failed again on servers
  in state `stopped`;
* the direct API call succeeds where the provider fails:

  ```text
  scw instance private-nic delete server-id=<id> private-nic-id=<id> zone=fr-par-1
  ✅ Private-nic has been successfully deleted.
  ```

  With the five cards removed by hand, `terraform destroy` finished on its own,
  destroying the remaining 18 resources, and the residue check returned to zero.

**Why the provider fails where the direct call succeeds was left open here,
and has since been answered.** The recorded transcript of that same run carries
the five failed calls, and they are not the same route:

```text
DELETE /instance/v2alpha1/zones/fr-par-1/private-network-interfaces/<nic>
  -> 412  precondition is not respected
```

The provider imports `scaleway-sdk-go/api/instance/v2alpha1` and calls
`DeletePrivateNetworkInterface` with the card alone, no server. The `scw` call
above uses the v1 route nested under the server,
`/instance/v1/zones/<zone>/servers/<server>/private_nics/<nic>`, which answers
204 on the same attached card. Two endpoints, two preconditions.

The remedy this record decides was therefore not lucky: it uses the route that
accepts an attached card, and it is the only one that does.

## Decision

**On a failed destruction, and only then, the launcher removes the private
network cards of the platform it deployed, then runs the destruction once
more.** The happy path never goes through this code, so a defect in it cannot
break a destruction that was working.

**Once, not until it works.** An unbounded destruction loop against a real cloud
is worse than the failure it claims to catch: it would hide a block of another
nature by spinning until the time runs out.

**Only what the run created.** The filter is the platform prefix. A relaxed
filter would strip the network cards of machines nobody created for the
exercise, and a machine without its card is no longer joined to its private
network. That selection is a pure function, tested, and covered by a mutation;
an empty prefix is refused rather than treated as "everything", because
`startswith("")` is true for all names and that case looks exactly like normal
operation.

**A failed `scw` is an error, never "no cards".** A recovery that removes
nothing because a command failed would let the destruction fail a second time
with nobody able to say why.

**The recovery says what it removed**, card by card, on the error stream. A run
that needed unblocking must be able to say so, otherwise the defect becomes a
habit instead of an issue.

## Consequences

The launcher now reaches behind Terraform's back on a resource Terraform owns.
That is a real cost: the state is momentarily ahead of the account, and the
destruction that follows sees a card that is already gone. Terraform treats a
missing resource as destroyed, so the sequence converges, but the asymmetry is
worth stating rather than discovering.

The recovery is only wired for the real target. The emulator's destruction does
not fail this way, and running it there would exercise nothing while adding a
path that only the emulator sees.

The recovery is not proven against the real cloud by an automated run. It
automates a sequence that was measured by hand, and its selection logic is
proven by unit tests and by `/falsify`. The proof that it works end to end will
come from the next real run that needs it, and if a run needs it and it does not
help, the residue check will still name what is standing.

## What this record does not decide

Whether the right long-term fix is upstream, in the stack topology, or here.
The v2alpha1 route refusing an attached card may well be deliberate, and the v1
nested route may be the one that will go away: nothing measured here says which
of the two Scaleway intends to keep. This record covers the guarantee the
repository already made, which is that nothing survives a run, and which had no
owner in this case.
