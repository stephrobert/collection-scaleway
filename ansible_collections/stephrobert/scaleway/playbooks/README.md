# Collection playbooks

Playbooks that run, not snippets that illustrate.

They live in `playbooks/`, the location Ansible recognises: once the collection
is installed, they are called by their fully qualified name, with no path.

Each one is played by `mise run integration` against a local emulator, on every
run of that target. An example nobody executes rots, and a wrong example in
documentation costs more than no documentation at all.

| playbook | what it shows |
|---|---|
| [doctor.yml](doctor.yml) | what is wrong with a setup, all of it at once, before anything else fails halfway |
| [fleet_report.yml](fleet_report.yml) | the whole fleet in one read-only command, and the zones it could not read named rather than counted as empty |
| [power_schedule.yml](power_schedule.yml) | bringing a named group to a power state, twice a day, and refusing every target it was not given |
| [rolling_reboot.yml](rolling_reboot.yml) | rebooting a named group in batches, waiting on what is observed and never on a duration |
| [list_servers.yml](list_servers.yml) | listing a whole zone, split by state and by type |
| [server_details.yml](server_details.yml) | the same module in unit read, and the `changed=false` of an information module |
| [stop_server.yml](stop_server.yml) | stopping a named Instance, waiting for the target state, then reading it back |

## Start here

```bash
ansible-playbook stephrobert.scaleway.doctor
```

It checks the ansible-core that will run the modules, the SDK the interpreter
can import, where the credentials come from, and whether the API answers. Every
check runs: finding one problem per run is how a first contact is spent on
nothing. It prints `Ready.` only when everything was checked **and** everything
passed, and it never prints a credential, only where it came from.

## Recipes

Each one starts from a need rather than from a module. They are the shipped
playbooks, so what is written here is what runs: `mise run integration` plays
every one of them against an emulator on each run, and the real exercise plays
them against a Scaleway account.

**Three of them are roles you can call from your own playbook.** The playbook is
the ergonomics, the role is the operation, and the module is the technical API.
Where a recipe says so below, the same logic is available without copying it:

```yaml
- ansible.builtin.include_role:
    name: stephrobert.scaleway.rolling_reboot
  vars:
    scaleway_rolling_reboot_group: scw_tag_production
    scaleway_rolling_reboot_batch_size: 2
```

The playbook and the role are never two implementations: the playbook calls the
role and passes what the command line carried. A test refuses anything else,
because two implementations of one operation always end up disagreeing.

**One way of saying what to act on.** The operations that act on machines take a
selector: exactly one of a group, a name, or tags.

```yaml
scaleway_rolling_reboot_selector:
  tags: [production, web]     # every machine carrying both
  match: all                  # `all` is the default; `any` widens it
```

`group: X` on the command line is the shorthand for `selector: {group: X}`. An
ambiguous name is refused rather than settled, and an unknown key is refused
rather than quietly selecting nothing, because a typo and an empty fleet look
alike.

**What every operation gives back.** `scaleway_operation` holds a
machine-readable result: what it examined, what it changed, what it left alone,
what it refused and why, and what it could not read. A pipeline reads that
rather than the sentence, and a sentence gets reworded.

### "My Scaleway setup does not work"

```bash
ansible-playbook stephrobert.scaleway.doctor
```

Reports the ansible-core that will run the modules, the SDK the interpreter can
import, where the credentials come from, and whether the API answers in a zone.
Every check runs, so one command names every problem rather than the first one.

**Check before**: nothing. This is the one to run before anything else.

**What it does not do**: it never prints a credential, only where it came from,
so its output can be pasted into a ticket. And it says `Ready.` only when
everything was checked **and** everything passed: an unreachable API is reported
as unverified, never as fine.

### "I need to see the state of my fleet"

```bash
ansible-playbook stephrobert.scaleway.fleet_report
ansible-playbook stephrobert.scaleway.fleet_report -e output=json
ansible-playbook stephrobert.scaleway.fleet_report -e output=markdown -e zones=fr-par-1
```

Instances by state, by zone and by tag, plus the load balancers. Three outputs
for three readers: a terminal, a pipeline, a ticket.

**As a role**: `stephrobert.scaleway.fleet_report`, with
`scaleway_fleet_report_zones` and `scaleway_fleet_report_output`. It leaves the
report in `scaleway_fleet_report_result`, so a calling playbook can act on it
rather than read it off the screen.

**Check before**: nothing. It is read-only, which is what makes it safe to run
first on an account you do not know.

**What it does not do**: it never counts a zone it could not read. A zone that
does not answer is named as unmeasured rather than contributing a zero, and when
no zone answers it says so instead of printing a total.

### "I want to know what is wrong with my fleet, every morning"

```bash
ansible-playbook stephrobert.scaleway.fleet_audit
ansible-playbook stephrobert.scaleway.fleet_audit -e output=json
ansible-playbook stephrobert.scaleway.fleet_audit -e @policy.yml
```

Judges the fleet against a policy and prints what it found, with a severity per
finding. `rolling_reboot` is used when you need it; this is the one that earns
its place in a schedule.

**As a role**: `stephrobert.scaleway.fleet_audit`. It leaves its findings in
`scaleway_fleet_audit_findings`, so a pipeline can open a ticket rather than
read a report.

**Check before**: nothing. It is read-only.

**What it does not do**: it never repairs what it finds. Terraform provisions
and Ansible operates, and an audit that corrected things would cross that line.
It never counts a zone it could not read as compliant, because a `PASS` over a
fleet nobody read would be worse than no audit: it would be believable. And the
shipped policy is a starting point made only of warnings, never an opinion about
your fleet: the severity of a public address depends on whether the machine is a
bastion or a database.

### "I need to power the lab down tonight"

```bash
ansible-playbook stephrobert.scaleway.power_schedule \
  -i production.scaleway.yml -e group=scw_tag_office_hours -e desired_state=off
```

Brings a named inventory group to a power state. Scheduled at 08:00 with
`desired_state=on` and at 20:00 with `off`, it is the command that pays for
itself twice a day.

**As a role**: `stephrobert.scaleway.power_schedule`, with
`scaleway_power_schedule_group` and `scaleway_power_schedule_desired_state`.

**Check before**: that the group holds what you think. `ansible-inventory -i
production.scaleway.yml --graph` shows it, and `--check` lists what would move
without moving it.

**What it does not do**: it has no default target, so it never guesses which
machines to power off. A named group holding no host fails rather than exiting
quietly, and machines in `starting`, `stopping` or `locked` are named and left
alone. Running it twice changes nothing the second time, because it reads each
machine before acting rather than firing blind.

### "I need to restart production progressively"

```bash
ansible-playbook stephrobert.scaleway.rolling_reboot \
  -i production.scaleway.yml -e group=scw_tag_production -e batch_size=1
```

Reboots a named group in batches, waiting for each batch to come back before
touching the next.

**As a role**: `stephrobert.scaleway.rolling_reboot`, with
`scaleway_rolling_reboot_group`, `scaleway_rolling_reboot_batch_size` and
`scaleway_rolling_reboot_wait_timeout`.

**Check before**: run it with `--check` first. It returns the batch plan and
reboots nothing.

**What it does not do**: it never waits on a duration. The machine is watched
leaving `running` and coming back, and a reboot that never starts is reported
rather than assumed to have worked. A machine that was already stopped is left
stopped: this reboots, it does not start. A batch that does not come back stops
the roll and names what was left to do.

### "I need to look at one machine, or list a zone"

```bash
ansible-playbook stephrobert.scaleway.list_servers -e zone=fr-par-1
ansible-playbook stephrobert.scaleway.server_details -e zone=fr-par-1
ansible-playbook stephrobert.scaleway.stop_server -e zone=fr-par-1 -e server_id=<uuid>
```

`server_details` takes the first Instance in the zone when none is named, so it
can be tried without knowing anything in advance.

**What they do not do**: `stop_server` never chooses on its own which machine to
stop. Without `-e server_id=<uuid>` it does nothing and says so. A playbook that
decides for you is a trap, not documentation.

## Running them

Against a real Scaleway account, with credentials in the environment or in the
configuration file:

```bash
export SCW_ACCESS_KEY=... SCW_SECRET_KEY=...

# from the repository
ansible-playbook playbooks/list_servers.yml -e zone=fr-par-1

# from the installed collection, by its fully qualified name
ansible-playbook stephrobert.scaleway.list_servers -e zone=fr-par-1
```

With no account and no spend, against a local emulator:

```bash
mise run integration          # starts feint, seeds it, plays everything
```

## What they do not show yet

These cover reading, acting and scheduling. The collection also ships state
management modules, which read, compare and write only the difference: no
shipped playbook demonstrates one yet, because a useful demonstration needs a
sequence to hold rather than a single call to make.

The full set is exercised elsewhere: `examples/playbooks/modules.yml` in the
repository plays them against the same platform, on an emulator and on a real
account, and publishes what each run actually played. The collection's own
README carries the counts, in a block that is recomputed rather than typed.

`stop_server.yml` never chooses on its own which machine to stop:
without `-e server_id=<uuid>` it does nothing and says so. An example playbook
that decides for you is a trap, not documentation.
