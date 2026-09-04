# Generator architecture

This repository does not contain a hand-written Ansible collection: it contains
the generator that writes it, and the decisions that turn a technical API into
a coherent Ansible interface. What the collection runtime carries and what it
costs is in [runtime.md](runtime.md); the source of the contracts and its
measured limits are in [scaleway-contracts.md](scaleway-contracts.md).

## The pipeline

```text
specs/scaleway/instance.v1.yml          versioned contract (OpenAPI 3.1)
        |
        v  generator/parser/openapi.py
   ApiService                            canonical IR, no Ansible, no SDK
        |
        v  generator/classifier/rules.py
   Classification                        INFO ACTION MANAGE WORKFLOW
        |                                LIFECYCLE IGNORE UNKNOWN
        v  generator/overrides/*.yml
   ProductPlan                           decision + target module + reason
        |
        +--> generator/report/render.py  text, JSON, Markdown
        |
        +--> generator/ansible/models.py intermediate model
                    |
                    v  generator/renderer + templates/
             plugins/modules/*.py
                    |
                    v  plugins/module_utils/scaleway.py
             execution: single client, errors, pagination
```

Every stage is testable on its own, and every stage has its test: the parser
against a laboratory contract (`tests/fixtures/widget/`), the classifier
against hand-built operations, the plan against the real Instance contract.

**Why an intermediate representation.** Without it, every change to the API or
to Ansible touches the same code. With it, the parser knows nothing of Ansible,
the renderer knows nothing of OpenAPI, and the boundary between the two is what
makes the tests possible.

## The structural decisions

### 1. The contract is versioned, not fetched on the fly

`mise run sync:api` downloads, `mise run report` reads the disk. A generation
run never depends on the network, so it is reproducible, and a change in the
Scaleway API shows up as a diff in a review.

### 2. The IR is immutable and serialises deterministically

`ApiService.to_json()` produces the same bytes on every run: operations sorted
by identifier, enums sorted by name, null keys dropped. That is what makes the
golden file `tests/fixtures/instance/expected_ir.json` possible, and therefore
drift detection.

### 3. The operation key is stable

`instance.v1.Server.ServerAction`: product, version, resource, identifier. It
is the key of the overrides and the key of the report. It depends on the
derived resource, so correcting a resource moves the key, and an override that
becomes orphaned is reported rather than ignored.

### 4. The resource is derived from the path, not from the operation name

The rule: **first and last resource-bearing segment**, after removing the
product, the version, the scope, the identifiers, the action segments and the
value segments.

Taking both ends rather than the last segment is what gives the same name to
`/security_groups/{id}/rules` and `/security_groups/{id}/rules/{id}`. A rule
that looks at one end only names the same resource `security_group_rule` in one
case and `rule` in the other, which is two modules for a single thing. The
report shows it immediately, because it prints the derived resource of every
operation.

### 5. Classification is mechanical, exceptions are written down

Six rules, based on the verb of the `operationId` and the HTTP method:

| verb | method | class |
|---|---|---|
| `get`, `list`, `describe` | GET | INFO |
| `create` | POST | LIFECYCLE |
| `delete`, `destroy` | DELETE | LIFECYCLE |
| `update`, `set`, `patch` | PATCH, PUT | MANAGE |
| anything else | POST | ACTION |
| anything else | GET | INFO |
| anything else | anything else | **UNKNOWN** |

Across the 74 operations of Instance v1, these rules settle everything: zero
UNKNOWN. That is not proof that they are right, only that they decided, which
is why the report prints the reason behind every decision.

A correction that would repeat across ten operations is a missing rule, not ten
overrides.

### 6. What the overrides settle on Instance

Every decision carries its reason in `generator/overrides/instance.yml`, and
the loader refuses a classification change that has none:

* **the replacing PUT is not exposed.** Scaleway publishes `Update*` (partial
  PATCH) and `Set*` (full PUT) for the same resource. An idempotent MANAGE
  module compares and writes only the difference: that is the PATCH. Exposing
  both would give a module able to silently erase the fields it was not given.
  Seven operations concerned;
* **attaching a volume belongs to Terraform.** `AttachServerVolume`,
  `DetachServerVolume` and their `FileSystem` equivalents create a relation
  between two resources; that is the boundary this project draws;
* **`SetSecurityGroupRules` is manual.** Replacing every rule of a group in one
  call requires comparing two ordered lists and defining what an "identical"
  rule is: that is business logic;
* **four resources are renamed.** `/products/servers` is a catalogue, not a
  `product` resource: `server_type`, `volume_type`,
  `server_type_availability`, `server_compatible_type`.

### 7. Coverage is not computed on a chosen denominator

```text
Day-2 coverage = (AUTO + OVERRIDE) / (INFO + ACTION + MANAGE + WORKFLOW)
```

LIFECYCLE and IGNORE are not in the denominator: that is not work to automate,
it is work set aside. The report counts them separately so the gap stays
visible. With no Day-2 operation, coverage is `null` and not `0.0`: a ratio
with no denominator is undefined, not zero.

Measured on Instance v1: **41 Day-2 candidates, 40 AUTO, 1 MANUAL, coverage
97.6%**, out of 74 operations discovered, of which 19 LIFECYCLE and 14 IGNORE.

That figure does not say "the product is 97.6% covered". It says that 40 of the
41 operations *retained as Day-2* are **classified for automatic generation**.
Any published sentence about coverage names its denominator.

Nor does it say that a module carries them. "Generatable" implied that, and it
was the defect: classification permits generation, it does not produce it. So
the generation report publishes **two** ratios side by side, this one and the
one for operations a written module actually calls, each with its name and its
fraction. The gap between the two reads module by module in the list of
exclusions, where each carries its reason.

A third tier exists and lives outside this report, because it depends on a run
rather than on the contract: how many modules the example playbook calls, and
how many a given run actually played. `mise run coverage:example` publishes it.

### 8. What the generator does not understand stays visible

Three mechanisms, none of them decorative:

* an operation no rule settles is `UNKNOWN`, and `report --strict` exits with
  code 2;
* an override that designates no existing operation is *orphaned*, and also
  exits with code 2. That check caught a faulty key on its very first run;
* what the contract does not say (an array with no `items`, a body with no
  schema) is listed in the report's limits, operation by operation.

## How a module is built

In this order, every brick before the one that leans on it:

1. **`plugins/module_utils/scaleway.py`**: single client, centralised error
   handling, complete pagination, check mode. Written **before** any template,
   otherwise the logic lands in the template and stays there. The five runtime
   decisions and what they cost are in [runtime.md](runtime.md);
2. **`generator/ansible/models.py`**: the intermediate model, the single source
   of the `argument_spec`, the `DOCUMENTATION`, the `EXAMPLES` and the
   `RETURN`. The selector of an INFO module is **computed** there: it is the
   path parameter the GET requires and the LIST does not know. Several
   candidates, or none, and the model refuses rather than choosing;
3. **`generator/renderer/modules.py` and `generator/templates/module.py.j2`**:
   Jinja2 for rendering only. Python literals and YAML blocks are produced by
   the renderer, not by `repr()` nor by a dictionary whose order would depend
   on the run;
4. **`galaxy.yml` is read by the generator.** The namespace, the version and
   the authors end up in every module; copying them into the code would create
   a second source;
5. **drift**: `mise run check:generated` regenerates the golden files **and**
   the modules, then requires that git see no difference, untracked files
   included.

### What is not decided in a template

The rule that settles every edge case: **if a template needs an `if` on
anything other than the presence of a value, the decision is missing from the
model.** It is measurable on the produced file: it defines only `main`, `main`
does two things, and there is neither a condition nor a loop inside it.

### Two golden files, two different measurements

* `tests/fixtures/instance/expected_ir.json` freezes what the **parser** reads
  from the real contract. It moves when Scaleway moves;
* `tests/fixtures/widget/expected_modules/` freezes what the **renderer**
  writes, from the laboratory contract. It must not move on the day Scaleway
  adds a server.

## What this project does not do

No second Terraform provider, no generation of `create` and `delete`, no
multi-cloud abstraction. The boundary is drawn once:

```text
Terraform provisions resources. Ansible operates existing resources.
```

An operation that creates, deletes or links resources has no place here, even
when the generator knows how to produce it.
