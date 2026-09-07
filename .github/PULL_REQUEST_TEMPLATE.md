<!--
One thing that surprises first-time contributors here, worth thirty seconds
before you push:

**The generated code is not the product.** Files under `ansible_collections/`
are written by the generator. `mise run check:generated` regenerates them and
fails on `git diff`, so a hand edit does not survive, but that is not the
point. The point is that fifty modules share one fix, and a hand edit fixes one.

`mise run check` takes under a minute, needs no Scaleway account, and catches
almost everything CI runs.
-->

# Summary

<!-- What does this change, and why? -->

## Type of change

- [ ] A classification or naming rule
- [ ] An override, with its reason
- [ ] The parser or the IR
- [ ] A module, a template, the runtime
- [ ] The inventory plugin
- [ ] Documentation
- [ ] Tooling / CI
- [ ] Security / supply chain

## Checklist

Only the **Always** block applies to every pull request. The other blocks are
conditional: if a block does not apply, write `N/A` rather than leaving it blank.
A blank box reads as "forgotten", an explicit `N/A` reads as "considered", and
only one of the two is a decision.

### Always

- [ ] `mise run check` passes
- [ ] No file under `ansible_collections/` edited by hand. If a produced file is
      wrong, the generator is wrong
- [ ] Every operation still lands in one of three states: generated, excluded
      with its reason, or `UNKNOWN` and the CI is red. Never filtered out
- [ ] Nothing in the diff creates, deletes or links a resource. Terraform
      provisions, Ansible operates

### When a guard, a validation or a refusal is added (otherwise N/A)

- [ ] `/falsify` run, and the new mutation is declared in
      `tests/falsify/specs.json`
- [ ] The mutation **neutralises** the condition rather than deleting the term.
      A deletion breaks the import, every test goes red, and it looks exactly
      like a proven guard
- [ ] The test it names exercises the function, not the state of the repository.
      A test that reads a committed file stays green while the function is
      broken

### When a rule or an override changes (otherwise N/A)

- [ ] `mise run report` run, and its diff read. A naming rule rarely touches one
      operation
- [ ] The override carries a `reason` that names its source. Transposed from the
      contract, never written from memory
- [ ] It is not a rule in disguise: a correction repeated across ten operations
      belongs in `generator/classifier/rules.py`

### When the parser or the IR changes (otherwise N/A)

- [ ] `mise run golden:update` run, **and the diff read**. A golden refreshed
      without being read turns a drift detector into a rubber stamp
- [ ] What the change does not handle is written down: a warning, a report line,
      or an override

### When something a reader sees changes (otherwise N/A)

- [ ] `mise run docs:quality` reports zero blocking defect. A page published on
      Galaxy is immutable, including what it fails to say
- [ ] `mise run sanity` passes
- [ ] `mise run readme` run if a derived block or a versioned link moved

### When a module, a plugin or an inventory option changes (otherwise N/A)

- [ ] `mise run integration` passes against the emulator
- [ ] The example stack exercises it, or this pull request says why not. A
      module that is written is not a module that has run
- [ ] Run against the real account before closing, and **nothing left behind**:
      checked, not assumed

### When `.github/workflows/` is touched (otherwise N/A)

- [ ] `mise run security` passes (actionlint, zizmor, poutine)
- [ ] Every action pinned to a full 40-character commit SHA with a `# vX.Y.Z`
      comment, never `@v4`, never `@main`
- [ ] `permissions:` is least-privilege on every job
- [ ] The exit-code contract still holds: `0` ok, `1` error, `2` unsorted
      operation or orphaned override

### When a model wrote a substantive part of this (otherwise N/A)

See the AI-assisted contributions section of
[CONTRIBUTING.md](../CONTRIBUTING.md).

- [ ] An `Assisted-by:` trailer names the tool and the model version
- [ ] I ran `mise run check` and `/falsify` myself, not "it should pass"
- [ ] Every field name in the diff comes from the versioned contract, the
      Scaleway SDK, or a run against the real API, and I can say which. "The
      model produced it" is not a source

## Related issues

<!-- e.g. Closes #123 -->
