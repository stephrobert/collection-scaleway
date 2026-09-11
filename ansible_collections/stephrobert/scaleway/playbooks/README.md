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

These three cover reading and acting. The collection now also ships state
management modules, which read, compare and write only the difference: no
shipped playbook demonstrates one yet, because a useful demonstration needs a
sequence to hold rather than a single call to make.

The full set is exercised elsewhere: `examples/playbooks/modules.yml` in the
repository plays 39 of the 46 modules against the same platform, on an emulator
and on a real account, and publishes what each run actually played.

`stop_server.yml` never chooses on its own which machine to stop:
without `-e server_id=<uuid>` it does nothing and says so. An example playbook
that decides for you is a trap, not documentation.
