# Releasing

**A version published on Galaxy is immutable.** Republishing the same one
returns `conflict.collection_exists`. There is no correction, only one more
version. Everything below exists because each refusal would otherwise cost a
number.

## Which number

You do not choose it. It is already written in the changelog fragments:

```bash
mise run version          # what the fragments imply
```

| what the fragments carry | what moves |
|---|---|
| `breaking_changes`, `removed_features` | **major** |
| `major_changes`, `minor_changes`, `deprecated_features` | **minor** |
| `bugfixes`, `security_fixes` alone | **patch** |

**Before `1.0.0`, a breaking change does not force `1.0.0`.** Declaring the
interfaces stable is a human act, not the mechanical consequence of a fragment,
so a pre-1.0 break increments the minor. Semantic versioning allows this
explicitly, and the collection README already announces it.

A release with no fragment is refused: a version that describes no change gives
nobody a reason to upgrade.

## Cutting one

Everything below happens on `main`, after the pull requests are merged.

```bash
git switch main && git pull

mise run version:bump     # writes galaxy.yml, composes the changelog
mise run readme           # the derived blocks follow the new version
mise run check            # everything, one last time
git diff                  # read it
```

`version:bump` writes the number into `galaxy.yml` and makes
`antsibull-changelog` absorb the pending fragments. `readme` matters more than
it looks: the documentation links published next to the version are derived from
it, so skipping this step ships links pointing at the previous release.

```bash
git switch -c release/0.2.0
git commit -am "Version 0.2.0"
git push -u origin release/0.2.0
gh pr create --base main --title "Version 0.2.0"
```

**The version commit goes through a pull request like every other commit.** A
repository rule requires it and refuses a direct push to `main`, and that is the
right shape: what ships must come from the branch that ran the fourteen required
checks. `git push origin main` will simply be rejected.

Once it is merged — and **only** then, because a squash merge rewrites the
commit and a tag placed before would point at something `main` does not contain:

```bash
git switch main && git pull
git tag -s 0.2.0 -m "stephrobert.scaleway 0.2.0"
git push origin 0.2.0
```

The tag is signed. `git config --global gpg.format ssh` and a
`user.signingkey` are enough; there is nothing else to set up.

## What the tag triggers

Pushing the tag — and nothing else — starts `.github/workflows/release.yml`.
**Not a push to `main`**: an irreversible publication must not come from a
merge.

The workflow runs, in this order:

1. `mise run release:check`, the gate. It refuses six things, and each one would
   cost a number:
   * a version that is not semantic versioning, which Ansible requires;
   * a missing tag, or a tag that does not say what `galaxy.yml` says. The
     archive is named after `galaxy.yml`, so the two can diverge with nothing
     saying so;
   * a tag that is not on `main`. What ships must come from the branch that was
     reviewed;
   * a dirty tree. An archive built on unversioned changes does not reproduce;
   * pending changelog fragments. They describe what the version brings, and
     they would stay outside it;
   * a blocking documentation defect. A page that says "Not documented by the
     Scaleway API contract" or shows `zone: <zone>` is published forever.
2. `mise run check`, what every pull request passes;
3. `mise run sanity`, what Ansible says of the produced file;
4. `mise run package`, which builds the archive, checks its contents, installs
   it into a throwaway directory and asks `ansible-doc` for its documentation. A
   file present in an archive is not a module Ansible can load;
5. the publication itself;
6. the GitHub release, **after** a successful publication. It records what went
   out; it does not announce it in advance.

The token lives in the `galaxy` environment, reachable only from `main`, and it
is passed through the environment rather than on a command line: a command ends
up in a log, and a log gets shared.

## Verifying a release

```bash
ansible-galaxy collection install stephrobert.scaleway:==0.2.0 -p /tmp/verif
ansible-doc -M /tmp/verif/ansible_collections/stephrobert/scaleway/plugins/modules \
  stephrobert.scaleway.instance_server_info
```

The page must explain the module on its own: what it reads, which options it
takes, what it returns, and an example that can be copied as is. That is the
criterion `mise run docs:quality` measures, and the reason it gates the release.

## Publishing by hand

Only if the workflow cannot run. The two things learnt the day it was done by
hand, written here rather than rediscovered:

* the server URL must be `https://galaxy.ansible.com/api/`. On a bare host,
  `ansible-galaxy` returns **401 at version discovery**, and the message talks
  about authorisation where the problem is a path;
* `--token` alone is not enough. The server configuration carries both the URL
  and the token, and the `ANSIBLE_GALAXY_SERVER_*` variables express it without
  writing a file.

```bash
mise run release:check
mise run package
ANSIBLE_GALAXY_SERVER_LIST=published \
ANSIBLE_GALAXY_SERVER_PUBLISHED_URL=https://galaxy.ansible.com/api/ \
ANSIBLE_GALAXY_SERVER_PUBLISHED_TOKEN="$GALAXY_API_TOKEN" \
  ansible-galaxy collection publish build/dist/*.tar.gz
```

The token never goes on a command line. Keep it in `.mise.local.toml`, which is
git-ignored, and a hook refuses a command that carries it.

## What you may depend on

Before `1.0.0`, treat the interfaces as evolving. Concretely:

* **a module name will not change silently.** A rename goes through a
  `breaking_changes` fragment, and the old name keeps working for one minor
  version with a deprecation notice;
* **an option that disappears is announced** the same way. A parameter the
  contract removes upstream is a `removed_features` entry, and the drift report
  is what surfaces it;
* **`SCW_API_URL` stays honoured end to end.** It is what lets you test against
  a local emulator without credentials, and no change may take it away.

What is not a promise: the exact wording of a description, the choice of an
example value, or the set of fields a `RETURN` lists. All three come from the
versioned contract, and they follow it.
