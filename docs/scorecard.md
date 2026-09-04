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

## The measured state, and its honesty

**As of 2 September 2026, there is no score yet.** The repository had just been
created and published, and Scorecard audited nothing until the first `git push`
happened. Everything below is therefore an **estimate read from the files**,
not a reading. It will be replaced by the real score on the first run of the
`Scorecard` workflow, and this sentence with it.

The reference is the sibling repository, `stephrobert/feint`, measured at
**7.9** on 25 August 2026. Its configuration is reused here almost as is, and
its five checks below 10 are exactly the ones no configuration fixes.

## What the configuration should give

| check | expected | what holds it |
|---|---|---|
| Token-Permissions | 10 | `permissions: {}` on every workflow, then the minimum per job |
| Pinned-Dependencies | 10 | every action pinned by SHA, Python dependencies locked with hashes |
| Dangerous-Workflow | 10 | no `pull_request_target`, no `workflow_run`, no interpolation inside a `run:` |
| Security-Policy | 10 | `SECURITY.md`, with deadlines that can be held rather than copied |
| Dependency-Update-Tool | 10 | `.github/dependabot.yml`, pip and github-actions, 14-day quarantine |
| SAST | 10 | CodeQL on Python, plus four workflow scanners acting as a gate |
| License | 10 | `LICENSE` at the root, GPL-3.0-or-later |
| CI-Tests | 10 | four jobs on every pull request |
| Binary-Artifacts | 10 | no binary under version control |
| Vulnerabilities | 10 | OSV-Scanner on pull requests and every week |
| Branch-Protection | 4 to 8 | ruleset versioned in `.github/rulesets/main.json`, compared to the live one by a gate |

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

* **No release yet, so no signature and no provenance.** The collection is not
  published on Galaxy. The day it is, signature and attestation will be a
  condition of that publication, not an afterthought.
* **`egress-policy: audit` and not `block`.** An allowlist written without
  having observed the real traffic breaks CI without proving anything. The move
  to `block` will be based on the `audit` readings, once there are some.
* **Fuzzing.** The generator reads OpenAPI contracts, which is structured input
  and a reasonable fuzzing subject. Nothing is done, and saying so is better
  than counting on the 74 operations of the versioned contract as if it were a
  corpus.
