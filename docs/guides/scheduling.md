# Scheduling these runs

A chained playbook worth scheduling and launched by hand stays a demonstration.
`power_schedule` only pays for itself called twice a day, and nothing here said
how anyone gets there.

This page gives three ways, starting from a **shipped** playbook rather than one
written for the page, and it says which ones have actually been run.

| path | state |
|---|---|
| scheduled CI | **replayed here**, on every run of this repository's pipeline and once a week on a schedule |
| `ansible-navigator` | **measured once**, by hand, against the emulator. Not replayed |
| AWX | **not tested**. Written from the platform's documented shapes, never executed |

The difference matters more than the paths do. A page that presented the three
as equivalent would be claiming three things and having measured one.

## What all three need

The same three pieces, whatever runs them.

**An execution environment that carries the collection.** It is published, so
none of these examples explains how to build one:

```text
ghcr.io/stephrobert/collection-scaleway/ee:<version>
```

Pin it by digest rather than by tag wherever the platform lets you: a tag gets
rewritten, a digest does not.

**An inventory the runner can read.** The dynamic inventory names no machine, so
the same file works from a laptop, from a runner and from AWX:

```yaml
plugin: stephrobert.scaleway.compute
products: [instance]
group_by: [product, zone, state, tags]
strict: true
```

`strict: true` is not enough on its own: Ansible downgrades an inventory failure
to a warning and exits zero. Every example below sets
`ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED`, because a schedule that runs on an
empty inventory and reports success is worse than one that does not run.

**Credentials from the platform.** Never from a file in your repository. Each
path below uses its own mechanism, and that is the only part of the three that
really differs.

## Scheduled CI

The one this repository runs. `power_schedule` is played against a local
emulator on every pipeline run and once a week on a schedule, by
`scripts/quickstart.py`, which checks what the inventory says afterwards rather
than what the playbook claims.

Against a real account, the same shape:

```yaml
name: power schedule

on:
  schedule:
    - cron: "0 6 * * 1-5"    # 08:00 Paris, winter time
    - cron: "0 18 * * 1-5"   # 20:00 Paris, winter time

permissions: {}

jobs:
  power:
    runs-on: ubuntu-24.04
    container:
      image: ghcr.io/stephrobert/collection-scaleway/ee@sha256:<digest>
    env:
      SCW_ACCESS_KEY: ${{ secrets.SCW_ACCESS_KEY }}
      SCW_SECRET_KEY: ${{ secrets.SCW_SECRET_KEY }}
      SCW_DEFAULT_PROJECT_ID: ${{ secrets.SCW_DEFAULT_PROJECT_ID }}
      ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED: "True"
    steps:
      - uses: actions/checkout@v5
      - run: |
          ansible-playbook stephrobert.scaleway.power_schedule \
            -i lab.scaleway.yml \
            -e group=scw_tag_office_hours \
            -e desired_state=${{ github.event.schedule == '0 6 * * 1-5' && 'on' || 'off' }}
```

**Cron has no timezone.** GitHub runs schedules in UTC, so the hours above drift
by one when daylight saving changes. A schedule that powers a lab down is
forgiving about that; one that powers production up is not, and the answer is a
scheduler that knows about timezones rather than a comment that explains the
drift.

## ansible-navigator

For anyone without AWX. Against a real account:

```bash
ansible-navigator run stephrobert.scaleway.power_schedule \
  --mode stdout --pae false \
  --eei ghcr.io/stephrobert/collection-scaleway/ee@sha256:<digest> \
  --penv SCW_ACCESS_KEY --penv SCW_SECRET_KEY --penv SCW_DEFAULT_PROJECT_ID \
  --senv ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED=True \
  -i lab.scaleway.yml \
  -e group=scw_tag_office_hours -e desired_state=off
```

`--penv` passes a variable that already exists in your shell into the execution
environment; it never writes it anywhere. `--pae false` turns off the run
artifact, which would otherwise land in your working directory carrying every
variable of the run.

**What was measured, and what it added.** That command was run against the
quickstart emulator, and it powered off the machines of the group while leaving
alone the one already off. Reaching the emulator needed three arguments a real
account does not: `--ce docker` to name the engine, `--container-options` to
join the compose network the emulator listens on, and `--eev` plus a
`ANSIBLE_COLLECTIONS_PATH` to mount the collection of a clone over the one the
image carries. Those are how you point this at a laboratory, and they are worth
knowing for that alone.

Then schedule the line itself, with whatever schedules things on that machine.
This path is the shortest of the three, and it is also the one where the
schedule is someone's crontab: what happens when the run fails is your problem
rather than the platform's.

## AWX

Not tested. The shapes below come from the platform's documentation, and they
are given so that someone with AWX starts from something rather than nothing.

**A custom credential type**, because AWX ships none for Scaleway:

```yaml
# Inputs
fields:
  - id: scw_access_key
    type: string
    label: Access key
  - id: scw_secret_key
    type: string
    label: Secret key
    secret: true
  - id: scw_default_project_id
    type: string
    label: Default project
required: [scw_access_key, scw_secret_key]
```

```yaml
# Injectors
env:
  SCW_ACCESS_KEY: "{{ scw_access_key }}"
  SCW_SECRET_KEY: "{{ scw_secret_key }}"
  SCW_DEFAULT_PROJECT_ID: "{{ scw_default_project_id }}"
```

The injector is what keeps the secret out of the playbook and out of your
repository: AWX puts it in the environment of the run and nowhere else.

**An inventory source** of type "Sourced from a Project", pointing at the
inventory file above, using the same execution environment. Turn on "Update on
launch" so the schedule acts on the fleet as it is rather than on the fleet as
it was cached.

**A job template** on `stephrobert.scaleway.power_schedule`, with the credential
attached and the execution environment set to the published image.

**Two schedules on that template**, each carrying its own extra variables, one
with `desired_state: on` in the morning and one with `desired_state: off` in the
evening. AWX schedules are timezone aware, which is the one thing it gives you
that a cron line does not.

## When something else decides when

A schedule fires on the clock. Event-Driven Ansible fires on an event, and the
collection ships a rulebook for it:

```bash
ansible-galaxy collection install ansible.eda
ansible-rulebook --rulebook stephrobert.scaleway.diagnose_on_alert \
  -i inventory.yml -E SCW_ACCESS_KEY,SCW_SECRET_KEY
```

An alert posted to its webhook makes it read the fleet.

**Detect then diagnose, never detect then modify.** That is the design, not a
first step towards something else. An event is reachable by a third party in a
way a command line is not, so a rule that powered machines off on a malformed
payload would be the failure mode `power_schedule` refuses by construction,
moved somewhere nobody reviews. A test refuses a rulebook that triggers anything
that writes, and it derives what a playbook does rather than trusting its name.

Two things measured while building it, worth knowing before you write your own:

- `ansible-rulebook` carries webhook code inside its own package, but neither
  `ansible.eda.webhook` nor a bare `webhook` resolves without the `ansible.eda`
  collection installed. This collection does not declare it as a dependency:
  somebody installing modules to power a fleet down at night should not be made
  to pull an event framework they never asked for;
- the webhook source nests the posted body under `payload`, so a body of
  `{"status": "firing"}` reads as `event.payload.status`. Wrapping it yourself
  gives a rule that never fires.

This path is replayed here on every run, like the scheduled pipeline: an
emulator, the rulebook of the installed collection, an alert posted the way a
monitoring system would, and the diagnosis played by the rule.

## What none of these make safe

Scheduling does not make a fleet-wide action safe, and none of these paths tries
to pretend otherwise.

* **run it with `--check` first**, and read the plan. `power_schedule` says what
  it would move and moves nothing;
* **verify the group holds what you think.** `ansible-inventory --graph` shows
  it. A named group that holds nothing fails rather than acting on everything,
  but a group holding the wrong machines fails nothing at all;
* **a schedule that never fails visibly is a schedule nobody checks.** The
  playbook fails on a machine it could not read rather than reporting a fleet it
  did not measure. Let that failure reach someone.
