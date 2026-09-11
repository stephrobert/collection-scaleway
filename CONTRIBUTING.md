# Contributing

## The one rule

**The generated code is not the product.** The product is the contract, the
classification rules, and the handful of explicit overrides that turn a
technical API into a coherent Ansible interface.

So a change that edits a file under `ansible_collections/` by hand is almost
always the wrong change. `mise run check:generated` regenerates everything and
fails on `git diff`, so the edit would not survive anyway, but the point is not
the check. The point is that fifty modules share one fix, and a hand edit fixes
one.

## Getting started

```bash
mise run setup     # the toolchain, pinned
mise run hooks     # git hooks that refuse before pushing what CI refuses after
mise run check     # lint, types, tests, strict report, golden drift
```

**Every hook mirrors a gate CI already holds.** A hook nothing doubles is a rule
only the people who installed it obey; a gate with no hook is one everybody
discovers after pushing. The fast ones run on commit, `mise run check` runs on
push. `.pre-commit-config.yaml` says why each one is where it is.

`check` is deterministic, offline, and takes under a minute. It needs no
Scaleway account and no credentials.

### Before you push

```bash
mise run qualifier   # what CI runs, in CI's order, before bothering CI
```

**CI is not a qualification lane.** `GITHUB_TOKEN` gets a thousand API requests
per hour per repository, shared by every workflow, and SARIF and artifact
uploads consume most of them. Using CI as a test loop drains that budget: CodeQL,
OSV-Scanner and the dependency review once failed **together**, on
`API rate limit exceeded for installation`, over code that had nothing wrong
with it.

`qualifier` replays `check`, `ansible-test sanity`, the integration run, the
example platform, both container images and the workflow scanners, and it
**names** what no local command can replay: CodeQL, the dependency review,
TruffleHog, Scorecard. A gate that stayed quiet about its own gaps would be the
green-on-nothing this repository is built against.

`mise run check` is the floor, not the ceiling. What else to run depends on what
you touched:

| what the change touches | run in addition | what it proves |
|---|---|---|
| a classification or naming rule | `mise run report`, read the diff | the decision changes where you think, and nowhere else |
| a guard, a validation, a refusal | `/falsify` | the test bites without the fix |
| the parser, the IR | `mise run golden:update`, read the diff | what the change really does to the 74 operations |
| a generated module, a template | `mise run sanity` | Ansible accepts the produced file |
| anything a reader sees | `mise run docs:quality` | the published page still explains itself |
| a module, a plugin, an inventory option | `python scripts/example.py machines`, then `reel` | it works on real machines, and on the real cloud |
| the contracts | `mise run sync:api` then `mise run check` | the API has not moved under the generator |
| adding a product | `mise run admission` | the product passes the gate, and you can name the price it enters with |
| a workflow, an action, `.github/` | `mise run security` | actionlint, zizmor and poutine accept the pipeline |
| `pyproject.toml` | `mise run lock`, read the diff | which dependency really appears, and under which hash |

**A golden regenerated without anyone reading its diff cancels the whole
mechanism.** It is a drift detector; refreshing it without looking turns it into
a rubber stamp.

## Falsifying a guard

A guard whose removal leaves every test green is a comment.

```bash
/falsify           # or: python scripts/falsify.py
```

It neutralises each declared guard in a copy outside the repository and requires
the named test to fail. Declared mutations live in `tests/falsify/specs.json`.

Two ways to write one that proves nothing, both met here:

* **deleting the term instead of neutralising the condition.** The import
  breaks, every test goes red, and it looks exactly like a proven guard. Keep
  every name evaluated: `if x is None and False:`, never `if False:`;
* **pointing the mutation at a test that reads the repository's state.** The
  files already carry the right content, so the test stays green while the
  function is broken. Exercise the function.

Add a mutation whenever you add a guard, and always after fixing a defect a
review named.

## Overrides

An override is a human decision, and it carries its reason:

```yaml
lb.v1.Acl.UpdateAcl:
  parameters:
    action:
      example:
        type: allow
      reason: >-
        La valeur vient du contrat : `scaleway.lb.v1.AclActionType` déclare
        `allow`, `deny` et `redirect`, et son défaut est `allow`.
```

The loader refuses a decision without a `reason`, and refuses an unknown field,
a typo would otherwise produce a silently inert override. It also refuses a key
declared twice: YAML keeps the last one without a word, and that once erased a
`resource` decision and renamed a published module with nothing turning red.

Three things an override must never do:

* **fix a rule that is wrong everywhere.** A correction repeated across ten
  operations is a missing rule in `generator/classifier/rules.py`, not ten
  overrides;
* **cover a sentence the contract already carries.** A `description` override
  fills a gap and nothing else; the day Scaleway documents the field, the
  override is reported as orphaned and `report --strict` exits 2;
* **invent.** A description written from memory is a claim about an API nobody
  checked. Transpose what the same contract says of the same field elsewhere,
  and name the source in the reason.

## What belongs here, and what does not

```text
Terraform provisions resources. Ansible operates existing resources.
```

An operation that creates, deletes or links resources has no place in this
collection, even when the generator can produce it. That is the boundary that
settles every design ambiguity, and it is why `AttachServerVolume`,
`AddBackendServers` and every `Set*` replacement is excluded, each with its
reason, in `generator/overrides/`.

**No operation ever disappears.** One that no rule settles is `UNKNOWN` and
fails `report --strict`. Never filter it out, never widen a rule to make it fit
somewhere.

## From your chain to the recipe chapter

If you automate something with this collection, the shortest useful thing you
can do is say so in
[Show and tell](https://github.com/stephrobert/collection-scaleway/discussions/categories/show-and-tell).
That costs a sentence and it is how `ADOPTERS.md` gets its lines.

If the chain is worth other people running, it can ship. The route, in order:

1. **Say what it is for, in one sentence that starts from a need.** Not "a
   playbook that calls X", but the thing someone tells themselves before they
   go looking. That sentence becomes the recipe's heading;
2. **It ships as a playbook** under `ansible_collections/stephrobert/scaleway/`
   `playbooks/`, named in English like the rest, and callable by its full name;
3. **`mise run integration` plays it** on every run, against a local emulator.
   That is what keeps it correct after you stop using it. A chain that ships
   without being replayed is a chain that will be wrong and look fine;
4. **Its recipe says what it does not do**, in the playbooks README. That half
   is the one missing everywhere else, and it is where a tool misleads: no
   default target, no waiting on a duration, no choosing a machine for you;
5. **`scripts/example.py` either plays it against a real account or declares
   why not**, with the reason in its table. Being written is not being run.

Steps 3 to 5 are held by tests rather than by goodwill, so a playbook that
skips one of them fails the build rather than shipping quietly. Open the pull
request even if you have only done the first two: the rest is a conversation,
not a barrier.

## Issues

Before opening one about a missing module, run `mise run report` and look: the
operation is either generated, excluded with its reason, or `UNKNOWN`. Which of
the three it is changes the whole conversation.

The most useful report is **a playbook that failed**, with what Ansible printed.
This project's claim is that a generated module is the one an operator would
have written by hand; a playbook that says otherwise is a fact.

## Commits

Commit messages are in French. They say what changed and **why**, and they name
what was measured. The repository's history is the design record: a subject line
of "fix" tells a future reader nothing.

Everything published is in English: both READMEs, `docs/`, `galaxy.yml`,
changelog fragments, and whatever `DOCUMENTATION`, `EXAMPLES` and `RETURN`
carry. Code, comments, docstrings, test names, override reasons and program
output are in French, with the accents. The full table is in `CLAUDE.md`.

Never use an em dash, in either language. `mise run typographie` refuses one,
and does not offer a replacement: the punctuation an em dash stands in for
depends on what the aside does, and a single substitution would put the same
mark everywhere and produce wrong sentences.

## AI-assisted contributions

The bar is the same as for everyone. What is added is disclosure and one extra
question.

**Disclose it** with an `Assisted-by:` trailer naming the tool and the model.

**Run it before you send it.** `mise run qualifier` and `/falsify`, yourself,
not "it should pass". A red pull request costs the runner, the reviewer, and the
repository's hourly API budget.

**Every field name in the diff comes from the versioned contract, the Scaleway
SDK, or a run against the real API, and you can say which.** "The model produced
it" is not a source. This is the one failure mode this repository is built
against: a plausible, wrong translation that looks correct until a playbook
fails in production.

What gets refused on sight: a generated file edited by hand, a golden refreshed
without its diff being read, an override without a reason, and a guard with no
mutation proving it.

## Security

Report a vulnerability privately rather than in a public issue. See
[SECURITY.md](SECURITY.md).
