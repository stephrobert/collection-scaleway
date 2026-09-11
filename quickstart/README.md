# Try the collection without a Scaleway account

`SCW_API_URL` is honoured end to end. That is usually presented as a property of
the runtime; it is also the free door into this project, and this is where it is
signposted.

Everything below runs against [feint](https://github.com/stephrobert/feint), a
local emulator. Nothing here reaches Scaleway, nothing is billed, and no real
credential is needed or accepted.

## What you need

Docker with the compose plugin, and a clone of this repository. That is all.

```bash
git clone https://github.com/stephrobert/collection-scaleway
cd collection-scaleway/quickstart
docker compose up -d
```

`up` does three things and then stops: it starts the emulator, waits until it
answers, and creates a small fictional fleet. The fleet creation is a plain
`uri` playbook, not a collection module, and that is deliberate: **the
collection never creates anything.** It operates what already exists, so
something has to exist first. On a real account, that something is Terraform.

## The tour

Each command below is the one you would run against a real account. The only
difference is where `SCW_API_URL` points.

### Is my setup sound?

```bash
docker compose run --rm ansible ansible-playbook stephrobert.scaleway.doctor
```

Reports the ansible-core that will run the modules, the SDK the interpreter can
import, where the credentials came from, and whether the API answers. Run it
first, and run it again on the day something behaves oddly.

### What does the fleet look like?

```bash
docker compose run --rm ansible ansible-playbook \
  stephrobert.scaleway.fleet_report -e zones=fr-par-1,fr-par-2
```

Instances by state, by zone and by tag. The lab lives in those two zones; drop
the option and the report asks every zone there is, which is also worth seeing
once. Note what it does with a zone that did not answer: it names it as
unmeasured rather than counting it as zero. Nothing measured is not nothing
found, and that distinction is the reason this report can be trusted.

### Who is out there, and in which group?

```bash
docker compose run --rm ansible ansible-inventory --graph
```

Not one machine is named in `lab.scaleway.yml`. The plugin asks the API what
exists and builds the groups: by zone, by state, by tag. `scw_tag_office_hours`
is the group the power playbook acts on below.

### Write something, then run it again

```bash
docker compose run --rm ansible ansible-playbook etiquettes.yml
docker compose run --rm ansible ansible-playbook etiquettes.yml
```

The first run writes tags and reports `changed=1`. The second reads, compares,
finds nothing to do, and reports `changed=0`. That is the difference between a
module that is idempotent and a module that skips: this one read the machine
before deciding.

### Power the lab down, and bring it back

```bash
docker compose run --rm ansible ansible-playbook stephrobert.scaleway.power_schedule \
  -e group=scw_tag_office_hours -e desired_state=off --check
docker compose run --rm ansible ansible-playbook stephrobert.scaleway.power_schedule \
  -e group=scw_tag_office_hours -e desired_state=off
```

`--check` lists what would move without moving it. The real run leaves alone
whatever is already in the target state, and names the machines caught in a
transient state rather than acting on them.

This is the one that pays for itself, and only if something calls it twice a
day. The scheduling guide gives three ways to get there, and says which of them
has actually been run.

### Restart production progressively

```bash
docker compose run --rm ansible ansible-playbook stephrobert.scaleway.rolling_reboot \
  -e group=scw_tag_role_web -e batch_size=1
```

It reboots one batch at a time and waits for each batch to come back before
touching the next. It never waits on a duration: it watches each machine leave
`running` and return, which is the only way to tell a reboot that happened from
a reboot that never started.

## What the emulator does not prove

An emulator that lies without saying so teaches a false green. Three facts,
each measured rather than assumed:

* **it does not apply VPC ACLs.** The whole class of filtering defects is
  invisible to it;
* **it does not push a default route over DHCP.** Routing defects are invisible
  too;
* **it accepts every credential.** It proves the shape of a call and the
  sequence of a playbook, never an authorisation.

The first two each cost a full cycle on the real cloud before they were
understood, which is why they are written here rather than left to be
rediscovered.

The emulator also does not serve every route the collection calls. Which ones,
on any given day, is measured rather than claimed:

```bash
mise run coverage:diff      # what the real account serves and feint does not
```

That comparison is the material of the issues filed against feint, and running
it is how this page stays honest without carrying a number that ages.

## Switching to a real account

Two things change, and nothing else:

```bash
unset SCW_API_URL                    # stop pointing at the emulator
export SCW_ACCESS_KEY=...            # a real key
export SCW_SECRET_KEY=...
export SCW_DEFAULT_PROJECT_ID=...
ansible-playbook stephrobert.scaleway.doctor
```

The inventory file, the playbooks and the module calls are unchanged. That is
the point of the tunnel: what you learned here is what you will run there.

Install the collection outside this repository with:

```bash
ansible-galaxy collection install stephrobert.scaleway
```

## What this is not

The emulator container accepts any credential and, by design, answers every
client on its network. The compose file publishes it on `127.0.0.1` only, and
the flag that lets it leave the container's own loopback is set because the
other services need to reach it across the compose network. Do not port this
file to a shared host: it is a laboratory, not a service.

## Cleaning up

```bash
docker compose down -v
```

`-v` also removes the emulator's fleet. Without it, the fictional machines are
still there next time, and the fleet creation notices and creates nothing.
