# What OpenSSF Scorecard says, and what it does not

Scorecard audits a repository from the outside: branch protection, action
pinning, dangerous workflow patterns, security policy, dependency update tool.
It is a good detector, and a bad objective.

This page is written under one rule: **a control is not raised by satisfying
its detector.** Each of the ones below has a form that scores well and means
nothing: requiring approvals that a bypass then skips, displaying a badge
describing practices nobody follows. That is the same fault as a comment
describing a control nobody applies, and it is precisely what this repository
spends its time hunting elsewhere.

## The measured state

**6.1 on 6 September 2026**, read from the public API rather than estimated:

```bash
curl -s https://api.securityscorecards.dev/projects/github.com/stephrobert/collection-scaleway
```

| check | score | what holds it, or what is missing |
|---|---|---|
| Binary-Artifacts | 10 | no binary under version control |
| CI-Tests | 10 | every pull request runs `mise run check` |
| Dangerous-Workflow | 10 | no `pull_request_target`, no interpolation inside a `run:` |
| Dependency-Update-Tool | 10 | `.github/dependabot.yml`, pip and github-actions |
| License | 10 | `LICENSE` at the root, GPL-3.0-or-later |
| Pinned-Dependencies | 10 | every action pinned by SHA, Python dependencies locked with hashes |
| SAST | 10 | CodeQL, plus four workflow scanners acting as a gate |
| Token-Permissions | 10 | `permissions: {}` on every workflow, minimum per job |
| Vulnerabilities | 10 | OSV-Scanner on pull requests and weekly |
| Security-Policy | 4 → 10 | it held no link and no address; both were added |
| Branch-Protection | 4 | one maintainer, so the bypass is described rather than removed |
| Contributors | 3 | one contributor |
| Signed-Releases | 0 → 10 | the archive was published unsigned; it now carries a signature, a certificate and a provenance bundle |
| CII-Best-Practices | 0 | the project is not registered on bestpractices.dev |
| Code-Review | 0 | one maintainer |
| Maintained | 0 | see below |
| Fuzzing | 0 | see below |
| Packaging | -1 | see below |

**Where the previous estimate was wrong, and it matters.** This page used to
carry a table of *expected* scores read from the files. Four of them were wrong:
`Security-Policy` was estimated at 10 and measured 4, `Signed-Releases`,
`Fuzzing` and `Packaging` were not in the table at all. An estimate that reads
like a measurement is exactly what this repository refuses everywhere else, and
it survived here for four days.

### Signed-Releases: what is signed, and how to check it

The tag was signed from the first release; the **archive** was not, and that is
what this check reads. Since 0.4.0 the release workflow signs the archive
without a key and attests its build provenance, both bound to the identity of
the workflow that produced it rather than to a secret:

```bash
gh release download 0.4.0 --repo stephrobert/collection-scaleway
cosign verify-blob \
  --signature stephrobert-scaleway-0.4.0.tar.gz.sig \
  --certificate stephrobert-scaleway-0.4.0.tar.gz.pem \
  --certificate-identity-regexp '^https://github.com/stephrobert/collection-scaleway/.github/workflows/release.yml@refs/tags/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  stephrobert-scaleway-0.4.0.tar.gz

gh attestation verify stephrobert-scaleway-0.4.0.tar.gz \
  --repo stephrobert/collection-scaleway
```

The workflow runs that first command on itself before publishing: a recipe a
reader copies and that does not work is worse than no recipe.

### Fuzzing: what would move it, and what does not

**Property-based tests do not move this check for a Python project.** The
repository has them, in `tests/unit/generator/test_proprietes.py`, and they are
there for what they find rather than for the score: Scorecard's detector covers
Go fuzzing, Haskell, JavaScript and Erlang, and not Python. Measured on
`docs/checks.md` before writing this paragraph, because assuming it would have
been the same mistake as the estimate table above.

Only two things move it: enrolling in OSS-Fuzz, or deploying ClusterFuzzLite.
Both are real work on a parser that reads structured input, and neither is done.

### Packaging: -1 is "not detected", not "badly done"

The collection is published on Ansible Galaxy on every version tag. Scorecard
does not know Galaxy: it looks for a publishing workflow among the ecosystems it
supports. The honest way to score here is not to game the detector but to
publish something it recognises **and that users want** — an execution
environment image, which the collection's `meta/` already describes. It is not
done.

### Maintained: 0 on a repository committed to daily

Both this repository and `stephrobert/feint` read 0 on a report dated the same
day as commits landing in both. The check counts activity over 90 days; a
repository younger than that has no window to fill. Nothing in the configuration
moves it, and time will.

## The checks no configuration fixes

### Branch-Protection: the bypass, and what it really allows

The ruleset keeps a bypass for the administrator role:

```json
"bypass_actors": [{ "actor_id": 5, "actor_type": "RepositoryRole",
                    "bypass_mode": "pull_request" }]
```

`bypass_mode` carries the whole decision. `"pull_request"` and not `"always"`:
the administrator can merge a pull request the rules would hold back, and
**cannot push to `main` directly**. Deletion and non-fast-forward stay closed
to everyone.

What this bypass buys is one thing: merging when a gate is red for a reason
that is not the code, typically a scanner that cannot download its own binary.

The cost is written down, because a decision whose benefits alone are listed is
a justification: **a gate the owner can lift measures the owner's discipline,
not the code.** Nothing guarantees the hatch serves network outages rather than
a red test on a Friday. What makes it visible rather than invisible is that
every use is a merge on a pull request whose checks are on file: a trace, not a
prevention.

### Code-Review: it measures the number of reviewers

Every change goes through a pull request whose checks all run, and none carries
a human approval, because there is one human. The score is accurate; what it
measures is the number of reviewers, not whether changes are judged against
anything.

What this repository substitutes for a second reader is machinery, and that
substitution **is** the project: a change is judged on whether a real playbook
passes (`mise run integration`), whether the API surface moved (the IR golden
and the strict report), whether `ansible-test sanity` accepts the produced
file, and whether the guard that was added really bites (`mise run falsify`).
Scorecard cannot read that, and it does not replace a reviewer. Both sentences
are true at once.

### Maintained and Contributors: time and headcount

The first is 0 for any repository younger than 90 days, whatever it contains.
The second counts distinct organisations among the contributors. Neither can be
fixed, and trying would be noise in the history.

### CII-Best-Practices: a badge, not a practice

The badge is obtained by answering a questionnaire about oneself. It is worth
exactly what the person filling it in is worth. It will be requested when the
answers are true, not for the score.

## What is still missing, and is not a Scorecard check

* **`egress-policy: audit` and not `block`.** An allowlist written without
  having observed the real traffic breaks CI without proving anything. The move
  to `block` will be based on the `audit` readings, once there are some.
* **Fuzzing, in the sense Scorecard means it.** The generator reads OpenAPI
  contracts, which is structured input and a reasonable subject. Property-based
  tests cover the translating functions; neither OSS-Fuzz nor ClusterFuzzLite is
  deployed, and counting the 74 operations of the versioned contract as a corpus
  would be counting the cases somebody already thought of.
