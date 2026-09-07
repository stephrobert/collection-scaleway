# ADR-013. When a module appeared is recorded, never computed

**Status**: accepted, 7 September 2026. Still in force.

## Context

`version_added` answers a question a user cannot settle any other way: *can I
call this module with the collection version I pinned?* Every published module
page carries it, `antsibull-docs` renders it, and the Ansible community
inclusion checklist names it explicitly:

> documentation and return sections use `version_added:` containing the
> *collection* version for which an option, module or plugin was added

Until 0.4.0 the generator wrote the **current** collection version into that
field. Every generation therefore rewrote the history of every module it
produced. Measured on the four published tags on 7 September 2026:

| tag | what `instance_server_info` announced | when it actually appeared |
|---|---|---|
| `0.2.0` | `version_added: 0.2.0` | `0.1.0` |
| `0.3.0` | `version_added: 0.3.0` | `0.1.0` |
| `0.4.0` | `version_added: 0.4.0` | `0.1.0` |

The measurement was made by looking, for each name, for the first published tag
that carries it. It settled three counts that had been assumed rather than
known:

* all **50** modules of 0.4.0 exist since `0.1.0`, at the same path in all four
  tags. The issue that opened this work supposed `instance_server_info` had
  arrived in 0.2.0; that was wrong;
* all **271** options were born with their module;
* **8** return keys, all named `result`, appeared in `0.4.0`. They were added
  **beside** the existing key, not in its place, so they are genuine additions
  rather than a rename.

The hand-written inventory plugin was correct throughout, carrying
`version_added: 0.1.0`. That contrast is what shows the defect belongs to the
generator and not to a decision anyone took.

Three sources could have supplied the fact, and two were measured unusable:

* **`changelogs/changelog.yaml`** declares modules per release only when a
  fragment says so. It names exactly one module under `0.1.0`, out of fifty. A
  partial record used as a complete one would have dated forty-nine modules
  wrong;
* **git history** is true by construction, but it makes generation depend on
  the repository rather than on its inputs, and the CI checkout that runs
  `mise run check` fetches no tags. A control reading it would have degraded
  silently, which is the failure this repository spends its time refusing.

## Decision

**The introduction version is recorded, never computed.** It lives in
`generator/ansible/introductions.yml`, a journal read by the generator and by
nothing else.

The journal is a sequence of dated blocks. Its form carries its invariant:

* **a name appears in exactly one block.** A name found in two blocks is an
  appearance being redated, and the loader refuses the file. The rule that a
  release never changes an existing `version_added` is therefore measured, not
  written in a comment;
* **a block accepts only `modules`, `options` and `retours`.** An unknown key
  is refused rather than ignored, for the same reason an override refuses an
  unknown field: a typo would produce a silently inert record;
* **an option or return dated on a module the journal does not know is an
  orphan**, and the file is refused. This mirrors the orphan override check;
* **what is not yet dated receives `en_preparation`**, a value written by hand
  in the same file. That is a declared decision, not a guess, and
  `scripts/introductions.py` confronts it with the version the pending
  changelog fragments imply.

A module always publishes its `version_added`. An option or a return publishes
one **only when it is later than its module**: repeating the module's date on
each of its options would print the same badge on every line of a page and
teach nothing.

## Consequences

**Adding a module is now two steps.** The generator dates an unknown module
with `en_preparation`; the journal must then record it. A control lists what is
covered by `en_preparation` rather than dated, so the gap is visible rather
than silent.

**The journal is a fourth thing to keep.** It joins the contracts, the overrides
and the goldens. It is small, it is append-only, and its diff is the record of
what a release adds, which makes it worth reading rather than merely
maintaining.

**Nothing repairs the pages already published.** Galaxy pages for 0.1.0 through
0.4.0 keep the wrong dates. They cannot be republished, and the correction
starts at 0.5.0.

**The two-step can be forgotten.** `en_preparation` is set by hand, and a stale
value would stamp a new module with a version that never ships. The control
compares it with what the changelog fragments imply, and says plainly when
there are no fragments to compare against rather than passing in silence.

## What this record does not decide

ADR-007 decides where a measured number lives, and it is why the counts above
are here rather than in a comment. ADR-005 decides that generated documentation
is refused rather than reported when it is unusable; a wrong `version_added` is
not unusable documentation, it is false documentation, and that gate did not
and could not see it.

Whether a module should also declare its Ansible `attributes`, and what
`version_added` those attributes carry, is not decided here.
