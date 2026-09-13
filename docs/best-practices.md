# OpenSSF Best Practices badge: every answer, ready to paste

This page exists because the badge cannot be filled in from a script. The
BadgeApp accepts `POST` and `PUT` only from a logged-in browser session; there
is no API key. So the answers are written here, and a human pastes them.

**Why bother.** The badge is worth 5 points out of 10 on the Scorecard
`CII-Best-Practices` check, which is 2.5 % of the aggregate score. That alone
would be a poor reason. The better one is that the questionnaire asks 67
questions a maintainer should be able to answer, and answering them honestly is
how you find out which ones you cannot.

**Read the answers before pasting them.** Several are `Unmet` on purpose. An
answer that claims a practice nobody follows is exactly the fault this
repository spends its time hunting, and the badge is not worth acquiring that
way.

## Before you start

1. Sign in at <https://www.bestpractices.dev/> with the GitHub account that owns
   the repository.
2. Add the project with the repository URL:
   `https://github.com/stephrobert/collection-scaleway`
3. The form autofills a dozen answers from GitHub. **Check them anyway**: the
   autofill guesses from file names, and a guess that lands on the right answer
   is still a guess.
4. Work down the page in the order below. It follows the page exactly.

The badge is awarded when every `MUST` is met and every `SHOULD` is met or
justified. `SUGGESTED` criteria may be left `Unmet` without justification.

Three answers are possible: **Met**, **Unmet**, **N/A**. Some criteria require a
URL alongside `Met`; they are marked `(URL required)` below.

---

## Basics

### Basic project website content

**`description_good`** · MUST · **Met**

> The project produces an Ansible collection for the Scaleway APIs, and the
> generator that writes it. The README says what it is in its first two
> sentences, and states the boundary that decides the rest: Terraform
> provisions resources, Ansible operates existing ones.

**`interact`** · MUST · **Met**

> Contribution and bug reporting are described in CONTRIBUTING.md, linked from
> the README, with issue templates that ask the question that settles a report
> before the conversation starts.

**`contribution`** · MUST · **Met** (URL required)

    https://github.com/stephrobert/collection-scaleway/blob/0.7.0/CONTRIBUTING.md

> CONTRIBUTING.md describes what to run before pushing, what gets refused on
> sight, and how a decision is recorded as an override carrying its reason.

**`contribution_requirements`** · SHOULD · **Met** (URL required)

    https://github.com/stephrobert/collection-scaleway/blob/0.7.0/CONTRIBUTING.md

> The same file states the requirements: no hand-edited generated file, a
> falsification mutation for every new guard, and the language boundary between
> what is published and what is not.

### FLOSS license

**`floss_license`** · MUST · **Met**

> GPL-3.0-or-later, declared in `LICENSE` and in `galaxy.yml`.

**`floss_license_osi`** · SUGGESTED · **Met**

> GPL-3.0-or-later is OSI-approved.

**`license_location`** · MUST · **Met** (URL required)

    https://github.com/stephrobert/collection-scaleway/blob/0.7.0/LICENSE

### Documentation

**`documentation_basics`** · MUST · **Met**

> The collection README covers installation, authentication, a sixty-second
> first run, and the module tables. Every published module carries its own
> reference page, generated from the same model as its `argument_spec` so the
> two cannot describe different things.

**`documentation_interface`** · MUST · **Met**

> Each module publishes `DOCUMENTATION`, `EXAMPLES` and `RETURN`, rendered by
> `ansible-doc` and on Galaxy. As of 0.3.0, 297 options, 62 returned keys and
> 669 returned fields carry a description, and the release gate refuses to
> publish a version where one does not.

### Other

**`sites_https`** · MUST · **Met**

> The repository, the released archives and the Galaxy pages are served over
> HTTPS only.

**`discussion`** · MUST · **Met**

> GitHub Issues and pull requests. Searchable, addressable by URL, open to new
> participants, and requiring no proprietary client.

**`english`** · SHOULD · **Met**

> Everything published is in English: both READMEs, `docs/`, `galaxy.yml`, the
> changelog, and the documentation of every module. The code, its comments and
> the test names are in French, which is the maintainer's language and does not
> reach a user of the collection. The boundary is written down in the
> repository's own instructions.

**`maintained`** · MUST · **Met**

---

## Change Control

### Public version-controlled source repository

**`repo_public`** · MUST · **Met**

    https://github.com/stephrobert/collection-scaleway

**`repo_track`** · MUST · **Met** (git)

**`repo_interim`** · MUST · **Met**

> Every change lands on `main` through a pull request; interim versions are
> public as soon as they are pushed.

**`repo_distributed`** · SUGGESTED · **Met** (git)

### Unique version numbering

**`version_unique`** · MUST · **Met**

> Each release carries a unique version in `galaxy.yml`, and the release gate
> refuses to publish when the tag and that file disagree.

**`version_semver`** · SUGGESTED · **Met**

> Semantic versioning, which Ansible requires of collections. The next number is
> derived from the changelog fragments rather than chosen.

**`version_tags`** · SUGGESTED · **Met**

> Every release is a signed tag, and the workflow publishes on a tag and nothing
> else.

### Release notes

**`release_notes`** · MUST · **Met** (URL required)

    https://github.com/stephrobert/collection-scaleway/blob/0.7.0/ansible_collections/stephrobert/scaleway/CHANGELOG.rst

> Composed by `antsibull-changelog` from fragments written with the change they
> describe. The release gate refuses to publish while a fragment is still
> pending, so a change cannot ship undescribed.

**`release_notes_vulns`** · MUST · **Met**

> No publicly known vulnerability has been fixed to date. The changelog
> mechanism carries a `security_fixes` section for the day one is, and the
> release notes are composed from those fragments rather than written by hand.

---

## Reporting

### Bug-reporting process

**`report_process`** · MUST · **Met** (URL required)

    https://github.com/stephrobert/collection-scaleway/blob/0.7.0/CONTRIBUTING.md#issues

**`report_tracker`** · SHOULD · **Met**

    https://github.com/stephrobert/collection-scaleway/issues

**`report_responses`** · MUST · **Met**

> The repository has a single maintainer, and reports are answered. The issue
> templates ask for what settles most reports in one exchange: for a module
> that fails, what Ansible printed; for a module that is missing, what
> `mise run report` says about the operation, since every operation is either
> generated, excluded with its reason, or unclassified and failing CI.

**`enhancement_responses`** · SHOULD · **Met**

> Enhancement requests are answered, including when the answer is no. The
> project has a written boundary that refuses a whole class of them: Terraform
> provisions resources, Ansible operates existing ones, so an operation that
> creates or deletes resources is out of scope even when the generator could
> produce it.

**`report_archive`** · MUST · **Met** (URL required)

    https://github.com/stephrobert/collection-scaleway/issues?q=is%3Aissue

### Vulnerability report process

**`vulnerability_report_process`** · MUST · **Met** (URL required)

    https://github.com/stephrobert/collection-scaleway/blob/0.7.0/SECURITY.md

**`vulnerability_report_private`** · MUST · **Met** (URL required)

    https://github.com/stephrobert/collection-scaleway/security/advisories/new

**`vulnerability_report_response`** · MUST · **Met**

> SECURITY.md commits to an acknowledgement within 3 working days, a first
> assessment with its severity and reasoning within 10, and a fix or a reasoned
> decision not to fix within 90. Those deadlines are written for what one
> person can hold rather than copied from a template.

---

## Quality

### Working build system

**`build`** · MUST · **Met**

> `mise run package` builds the collection archive, checks its contents,
> installs it into a throwaway directory and asks `ansible-doc` for its
> documentation. A file present in an archive is not a module Ansible can load,
> which is why the last two steps exist.

**`build_common_tools`** · SUGGESTED · **Met** (mise, uv, pip, `ansible-galaxy`)

**`build_floss_tools`** · SHOULD · **Met**

> Every tool in the build is FLOSS.

### Automated test suite

**`test`** · MUST · **Met**

<!-- compteurs:tests-badge:début, produits par scripts/readme_counters.py -->
> 1175 unit tests, plus `ansible-test sanity` on four `ansible-core` versions and
> an integration run of the shipped playbooks against a local emulator.
<!-- compteurs:tests-badge:fin -->

**`test_invocation`** · SHOULD · **Met**

> `mise run test` for the unit suite, `mise run check` for everything a pull
> request must pass.

**`test_most`** · SUGGESTED · **Unmet**

> No line-coverage figure is measured or published, so claiming "most" would be
> a claim nobody checked. What the repository measures instead is whether each
> guard actually bites: `/falsify` neutralises every declared guard one at a
> time in a copy outside the repository and requires the named test to fail.
> That is a different property from coverage, and it is not a substitute for it.

**`test_continuous_integration`** · SUGGESTED · **Met**

> Every pull request runs `mise run check`, `ansible-test sanity` on four
> `ansible-core` versions, the archive build, the integration run and the
> example platform.

### New functionality testing

**`test_policy`** · MUST · **Met**

> CONTRIBUTING.md requires a test with new functionality, and requires a
> falsification mutation with any new guard, because a guard whose removal
> leaves the tests green is a comment.

**`tests_are_added`** · MUST · **Met**

**`tests_documented_added`** · SUGGESTED · **Met**

> The requirement is in CONTRIBUTING.md and repeated as a checklist item in the
> pull request template, with the two ways of writing a mutation that proves
> nothing, both of which happened here.

### Warning flags

**`warnings`** · MUST · **Met**

> `ruff check`, `ruff format --check`, and `mypy` in strict mode.

**`warnings_fixed`** · MUST · **Met**

> All three are gates: a warning fails the build rather than being reported.

**`warnings_strict`** · SUGGESTED · **Met**

> `mypy` runs in strict mode, and the generator refuses an untranslatable type
> rather than defaulting it to `str`.

---

## Security

### Secure development knowledge

**`know_secure_design`** · MUST · **Met**

> The maintainer understands the principles. Where they apply here, they are
> applied and written down: least privilege on every CI job, no secret reachable
> from a `pull_request` run, a publication token confined to an environment that
> only version tags may deploy to, and a runtime that centralises error handling
> so that no code path copies a secret into a log.

**`know_common_errors`** · MUST · **Met**

> The class that matters for this project is secret leakage through generated
> code. The generator marks a sensitive parameter `no_log` from a deliberately
> wide name heuristic, on the stated reasoning that a false positive is fixed by
> an override while a false negative writes a secret into Ansible's log. A
> falsification mutation proves that guard bites.

### Use basic good cryptographic practices

**`crypto_published`** · MUST · **Met**

> The collection talks to the Scaleway API over TLS through the official SDK. It
> implements no cryptography of its own.

**`crypto_call`** · SHOULD · **Met**

> No cryptography is implemented in this project.

**`crypto_floss`** · MUST · **Met**

> Python's standard library and OpenSSL, through the SDK.

**`crypto_keylength`** · MUST · **N/A**

> The project generates no keys and specifies no key lengths. Release signing is
> keyless: the signature binds the archive to the identity of the workflow that
> produced it, and the key material is Sigstore's.

**`crypto_working`** · MUST · **Met**

> No broken or obsolete algorithm is used or depended upon.

**`crypto_weaknesses`** · SHOULD · **Met**

**`crypto_pfs`** · SHOULD · **N/A**

> The project operates no server and terminates no TLS connection.

**`crypto_password_storage`** · MUST · **N/A**

> The project stores no password and authenticates no user. Credentials are read
> from the environment or the Scaleway configuration file and passed to the SDK.

**`crypto_random`** · MUST · **N/A**

> No random value is generated for a security purpose. The generator is
> deliberately deterministic: the same contract produces the same files, byte
> for byte, and a golden test measures it.

### Secured delivery against man-in-the-middle attacks

**`delivery_mitm`** · MUST · **Met**

> The repository is cloned over HTTPS or SSH, the archive is downloaded from
> Galaxy over HTTPS, and each release carries a signed tag, a keyless signature
> over the archive and a build provenance attestation. SECURITY.md publishes the
> two commands that verify them, and the release workflow runs the first one on
> the archive before publishing it.

**`delivery_unsigned`** · MUST · **Met**

### Publicly known vulnerabilities fixed

**`vulnerabilities_fixed_60_days`** · MUST · **Met**

> None is known. OSV-Scanner runs on every pull request and weekly, Dependabot
> watches pip and GitHub Actions, and the dependency lock carries hashes.

**`vulnerabilities_critical_fixed`** · SHOULD · **Met**

### Other security issues

**`no_leaked_credentials`** · MUST · **Met**

> TruffleHog runs on every pull request. The publication token lives in a GitHub
> environment reachable only from version tags, and is passed through the
> environment rather than on a command line, because a command line ends up in
> a log and a log gets shared.

---

## Analysis

### Static code analysis

**`static_analysis`** · MUST · **Met**

> CodeQL on Python, `ruff` and `mypy --strict` as gates, and four workflow
> scanners: actionlint, zizmor, poutine and plumber.

**`static_analysis_common_vulnerabilities`** · SUGGESTED · **Met**

> CodeQL's security query suite.

**`static_analysis_fixed`** · MUST · **Met**

> All of them are gates rather than reports.

**`static_analysis_often`** · SUGGESTED · **Met**

> On every pull request, and weekly for the ones that need a trusted context.

### Dynamic code analysis

**`dynamic_analysis`** · SUGGESTED · **Met**

> The test suite runs on every change; the shipped playbooks are played against
> a local emulator on every pull request; and the example platform is played
> against the real Scaleway account before a release, with a differential check
> that the account returns to the resources it held before.

**`dynamic_analysis_unsafe`** · SUGGESTED · **N/A**

> Python is memory-safe. There is no C or C++ in this project.

**`dynamic_analysis_enable_assertions`** · SUGGESTED · **Met**

> Assertions are enabled: the code is never run with `-O`.

**`dynamic_analysis_fixed`** · MUST · **Met**

---

## After you submit

The badge percentage appears immediately; Scorecard picks it up on its next
weekly run, so `CII-Best-Practices` will still read 0 for a few days. That delay
is the tool's, not the project's.

Add the badge to the root README when the percentage reaches 100 %, next to the
others:

```markdown
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/<ID>/badge)](https://www.bestpractices.dev/projects/<ID>)
```

`<ID>` is the number in the project URL after registration. Tell the maintainer
of this file what it is, and it will be added to the derived block rather than
pasted by hand.
