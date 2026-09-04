# The collection runtime

What `plugins/module_utils/scaleway.py` carries, why, and what it costs.

State: written, measured by 49 unit tests, judged by `ansible-test sanity`, and
exercised end to end against a local emulator and against a real Scaleway
account.

## How the roles are split

```text
generator/                              reads the contract, decides, writes the module
ansible_collections/stephrobert/scaleway/
  plugins/modules/                      the documentation, the argument_spec, the operation
  plugins/module_utils/                 the client, the errors, pagination, check mode
```

A generated module contains **no** logic. That is measured, not asserted:
`test_le_module_ne_porte_aucune_logique` parses the produced file and requires
that it define only `main`, that `main` do two things, and that there be
neither a condition nor a loop inside. Logic sneaking into the template would
redden that test immediately.

## Decision 1: execute the contract's method and path

The Python SDK is the execution client. What remained was **how** a generated
module reaches an operation. Two paths existed:

| path | what it requires knowing | what it costs |
|---|---|---|
| the SDK's generated classes (`InstanceV1API.get_server`) | translating `GetServer` into `get_server`, and hoping | a second source, never measured, drifting silently |
| `scaleway_core.api.API._request(method, path, ...)` | the method and the path, which the IR already carries | a dependency on an underscore-prefixed method |

The second was chosen. The contract stays **the only source**: the generator
guesses no SDK method name, and the IR already carries `http_method` and
`path`.

The price is real, and it is held by a guard rather than by hope:
`test_le_sdk_expose_toujours_le_point_dexecution_attendu` checks the signature
of `API._request`. If the SDK moves it, `mise run check` says so, not a
playbook in production.

## Decision 2: a single way to build the client

The official collection has two, and the second silently ignores an
`access_key` passed as a parameter.

`build_client()` is the only one, and its precedence is the one a user expects:

```text
module parameters  >  environment variables  >  configuration file
```

The SDK logger receives a `NullHandler`: without it, every run without a
configuration file writes a warning to standard error, which is the normal case
in CI.

## Decision 3: validation depends on the target

The SDK validates the key format (`SCWXXXXXXXXXXXXXXXXX`) as soon as an `API`
is built. That is useful against the production API, and it would forbid the
project's only credential-free test scenario.

The rule fits in one sentence, and it is in the code:

* **against `https://api.scaleway.com`**, the SDK's full validation applies;
* **against any other `api_url`**, only the presence of credentials is
  required, with a message that names the parameter and its environment
  variable.

This is what gives rule 7 of the project its meaning: `SCW_API_URL` honoured
end to end is not an intention, it is what makes `mise run integration`
possible.

## Decision 4: pagination goes all the way, and knows when to stop

`page` and `per_page` **are not module options**. Exposing them would allow
returning a first page silently, presented as a complete list. The runtime
walks, and stops on three conditions, in this order:

1. `total_count` is present and the count has been reached. The published
   contract does not declare that field; the SDK reconstructs it from the
   `x-total-count` header, and the emulator returns it in the body. It is used
   when present, and never required;
2. the returned page holds fewer elements than requested;
3. `MAX_PAGES` is reached, and **that is an error**. An API ignoring `per_page`
   would loop forever; failing loudly is better.

The order matters, and it was corrected: reading the short page first made
eleven Load Balancer lists return their first page in silence, because that API
answers a `page_size` request with a full page and a `total_count` that says
there is more. All three conditions are measured, and two are falsified.

## Decision 5: an error says what to diagnose, and nothing else

A module message ends up in a log, and a log gets shared. The error carries the
operation, the HTTP status, the request identifier and the API's `type`. It
**never** copies the response body: it may contain what the caller sent.

```json
{
  "msg": "resource is not found",
  "operation": "GetServer",
  "status_code": 404,
  "request_id": "req-42",
  "api_type": "not_found"
}
```

Measured by `test_une_erreur_ne_recopie_pas_le_corps_de_la_reponse`, and
falsified: copying the whole payload reddens that test.

## Decision 6: a PUT receives everything you want to keep

A `PUT` replaces, a `PATCH` modifies. Sending only the difference to a `PUT`
silently erases everything you did not name, which is exactly why the five
`PUT` operations of Instance are set aside by override.

Seven Load Balancer operations are `PUT`, and the generated module used to
carry both contradictory sentences in its own documentation, three lines apart:
"You must set all parameters", from the contract, and "writes only the fields
that differ", from this runtime.

So the body of a `PUT` carries **every** managed field: the requested value
where the playbook gives one, the value read back otherwise. What the read does
not return is not sent, because the contract does not say what an absent field
means. `changed` is still decided on the difference: the body grows, the verdict
does not move, and idempotence holds. Measured against a real account: nine
identical rewrites out of nine report no change.

## The three kinds of module, and what each one does

| kind | what it does | what it never does |
|---|---|---|
| INFO | reads one resource, or lists them all, every page walked | write |
| ACTION | triggers a one-shot operation, and waits for the target state | create or delete |
| MANAGE | reads, compares, writes only the difference | replace what it was not given |

MANAGE supports check mode and `--diff`, and masks the value of a field marked
`no_log` in the diff it publishes.

## What this runtime still does not carry

* **the object-to-dict conversion** has no reason to exist: by executing the
  contract's path, the runtime receives JSON, never an SDK object. The
  `object_to_dict` defect of the official collection is avoided by not walking
  the ground where it happens.

## The end-to-end proof

`mise run sanity` judges the produced file. It says nothing about its
behaviour. `mise run integration` does:

```bash
mise run integration
```

The scenario starts [feint](https://github.com/stephrobert/feint), a local
emulator of the European clouds, creates 104 servers in it, assembles the
collection and plays a real playbook against it. 104 and not 10: below one
page, pagination would never be exercised, and an incomplete list would pass
for a complete one.

What the playbook proves, and no unit test can:

* the list returns every server, therefore both pages;
* a supplied identifier switches to the unit read, and the module returns
  `server` rather than `servers`;
* a contract filter (`name`) does reach the API;
* check mode returns the same thing and changes nothing;
* an unknown identifier produces the error described above, with no secret.

### What the scenario asks the emulator rather than writing it down

* **the credentials**, through `feint env scaleway --endpoint <url>`. Writing
  them in this repository would create a second source of what the emulator
  accepts. The command writes its exports to standard output and its remarks to
  standard error, which makes reading it safe;
* **the probe**, through `feint wait`, which returns 0 when the emulator answers
  and 1 otherwise. `feint status` will not do: measured, it exits 0 in both
  cases, and using it would have suggested an emulator always answered;
* **the expected number of servers**, read back from the emulator after seeding
  rather than assumed. An adopted emulator may already hold some.

One guard holds all of this: if `feint env` does not return a `SCW_API_URL`
pointing at the emulator, the scenario stops. It is the most expensive guard in
the repository to lose, because without it the playbook would leave with
whatever is lying around in the shell, that is, possibly towards the real
Scaleway API.

### Two backends for the same scenario

`FEINT_VM` chooses what carries a running server. The scenario does not change;
only the subject gets harder.

```bash
mise run integration                        # off: state is bookkeeping
mise run integration FEINT_VM=incus-ovn     # a machine really boots
```

Measured on 1 September 2026, on feint 0.12.1, host with Incus 7.2 and OVN:

| mode | `CreateServer` | `poweron` to `running` | what exists behind it |
|---|---|---|---|
| `off` | 0.02 s | 0.0 s | nothing, state is a record |
| `incus-ovn` | 0.02 s | 1.0 s | a `feint-scw-<uuid>` container RUNNING in Incus |

Creating a server boots nothing in either case: at Scaleway a server is born
`stopped`, and only `poweron` turns it on. That is what makes seeding 104
servers as cheap under `incus-ovn` as under `off`.

What machine mode adds to the proof: the playbook reads a server whose
`running` state matches a real process, not a field the emulator wrote to
itself. `feint doctor --vm incus-ovn` says, before any start, whether the host
can deliver it, and refuses rather than falling back to a weaker mode.

Two things learned while wiring it up, both held by a test and a falsification:

* **`--cleanup` is not a convenience.** Without it, a run under `incus-ovn`
  leaves behind the container it started. Observed on the development machine,
  `incus list` in hand;
* **adopting an emulator can measure something other than what was asked.** A
  `mise run integration FEINT_VM=incus-ovn` launched while an emulator in `off`
  was already listening was adopted and went green **without starting a single
  machine**. The output was that of a successful run; only the boot duration,
  0.0 s instead of 1.0 s, said that nothing had happened. The scenario now reads
  `feint status --format json`, compares the `machines` field, and refuses to
  adopt an emulator in another mode. `FEINT_ADDR` allows taking another port
  rather than stopping someone else's.

### In CI

The `integration` job starts the emulator with the action feint publishes:

```yaml
- uses: stephrobert/setup-feint@b7eba1d4fcaccf65cf9124bf97a0d995996709b9 # v1
  with:
    version: "0.12.1"
    addr: 127.0.0.1:4599
```

It downloads the release binary, **checks its SHA-256** against the published
`checksums.txt`, then runs `feint start`. The feint repository holds the guard
that matters here itself: a job in its `workflow-security` compares the
`stephrobert/setup-feint@v1` mirror to `.github/actions/setup-feint/action.yml`
in its own repository, and fails while the two differ.

`scripts/integration.py` **adopts** an emulator that is already listening and
does not stop it: the lifecycle belongs to whoever started it. That is what
lets the same script serve locally, where it starts and tidies up, and in CI,
where the action takes care of it.

**The emulator is a test backend, not a dependency.** Nothing under `plugins/`
knows about it, `mise run check` runs without it, and the shipped collection
does not mention it. The target is separate, and it **fails** when feint is
absent rather than skipping itself: a test that skips itself eventually never
runs again.

### What the emulator serves of our roadmap

Measured by comparing **method and path**. Operation identifiers cannot be
compared: the contract and the Go SDK do not name them the same way.

| feint version | INFO | ACTION | MANAGE | Day-2 served |
|---|---|---|---|---|
| 0.12.1, the version CI pins | 23/27 | 1/3 | 10/11 | **35/41** |
| `main`, unpublished as of 1 September 2026 | 25/27 | 1/3 | 11/11 | **38/41** |

The six refusals reported upstream were all arbitrated, and four changed their
mind:

| operation | issue | verdict |
|---|---|---|
| `UpdatePrivateNIC` | [#624](https://github.com/stephrobert/feint/issues/624) | served |
| `GetDashboard` | [#626](https://github.com/stephrobert/feint/issues/626) | served |
| `GetServerCompatibleTypes` | [#626](https://github.com/stephrobert/feint/issues/626) | served |
| `GetServerTypesAvailability` | [#626](https://github.com/stephrobert/feint/issues/626) | refusal upheld |
| `ListVolumesTypes` | [#625](https://github.com/stephrobert/feint/issues/625) | refusal upheld |
| `ExportSnapshot` | [#627](https://github.com/stephrobert/feint/issues/627) | refusal upheld |

**Testing an unpublished version requires nothing special**:
`FEINT=/path/to/the/binary mise run integration`. That is how the table above
was filled in, on a binary built from `main` without tagging anything. CI, on
the other hand, stays pinned to a **release**: CI that follows a branch
measures a moving target.

### What the emulator does not serve, and how it says so

An unmounted route receives **501 `not_emulated`**, with a message pointing at
`/_feint/routes`. That is an honest answer: nothing can pass for a success.

The gap is measured rather than felt. The example stack plays the same
playbook against both targets and keeps an artefact of each run:

```text
feint  28 modules played out of 46 · 8 idempotences proven · 4 routes not emulated
real   39 modules played out of 46 · 9 idempotences proven · no residue
```

Eleven modules therefore run against the real cloud and not here, and they are
listed by name rather than summarised. `mise run coverage:example` publishes
the comparison.

## The trap hit while writing all this

`ansible-test` asks git for the list of files to examine. The first version of
this repository put the collection at the root and assembled a copy under
`build/`, which git ignores. It therefore found no files there:

```text
WARNING: All targets skipped.
```

...and it **exited 0**. Twenty-four tests announced, zero files examined, a
perfect green, indistinguishable from that of a flawless collection.

The fix was not to work around the symptom but to remove its cause: the
collection lives in `ansible_collections/stephrobert/scaleway/`, tracked by
git, and `ansible-test` works there **in place**. The script that built the
copy was deleted.

What remains is the guard, and it now bears on the real condition:

* **before**, `scripts/sanity.py` refuses to measure if git tracks no file of
  the collection, the exact case that produced the false green;
* **after**, it refuses the output if the phrase `All targets skipped` appears.

Both are falsified (`sanity-sur-collection-invisible`,
`sanity-qui-ne-mesure-rien`). Outside a git repository the first does not
apply: `ansible-test` then walks the disk, and refusing there would mean
refusing a measurement that does take place.

## The inventory engine, layer by layer

The `plugins/inventory/scaleway.py` plugin carries only the dialogue with
Ansible. Everything that decides lives under `plugins/module_utils/inventory/`,
in layers that are testable on their own:

| layer | what it decides |
|---|---|
| `config` | reading and validating what the user asked for |
| `providers` | translating a Scaleway API into the normalised model |
| `network` | indexing IPAM, private networks and VPCs, then joining |
| `address` | choosing `ansible_host`, and being able to explain it |
| `hostname` | choosing `inventory_hostname`, and refusing collisions |
| `groups` | naming the groups, and sanitising those names |
| `models` | the normalised model, the only object crossing the layers |
| `errors` | telling a denied permission from an outage and from an absence |

That map used to live in the docstring of `inventory/__init__.py`, until
`ansible-test sanity` refused it: under `module_utils`, `__init__.py` files must
be **empty** for ansible-core 2.17 and 2.18, which `meta/runtime.yml` declares
as supported. Recent versions accept it, and that is the kind of gap a matrix
exists to catch.

The join reads its fields through `getattr(..., None)`, so a field renamed
upstream returns `None` rather than raising, and the inventory returns a mute
fleet. That is why `ipam.v1` and `vpc.v2` are versioned under
`specs/scaleway/suivis/`, and why a test confronts what the code actually reads,
read from the code by AST, with both the contract and the installed SDK.
