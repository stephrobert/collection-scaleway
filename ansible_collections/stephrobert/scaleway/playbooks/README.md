# Collection playbooks

Playbooks that run, not snippets that illustrate.

They live in `playbooks/`, the location Ansible recognises: once the collection
is installed, they are called by their fully qualified name, with no path.

Each one is played by `mise run integration` against a local emulator, on every
run of that target. An example nobody executes rots, and a wrong example in
documentation costs more than no documentation at all.

| playbook | what it shows |
|---|---|
| [inventaire_serveurs.yml](inventaire_serveurs.yml) | listing a whole zone, split by state and by type |
| [detail_dun_serveur.yml](detail_dun_serveur.yml) | the same module in unit read, and the `changed=false` of an information module |
| [arreter_un_serveur.yml](arreter_un_serveur.yml) | stopping a named Instance, waiting for the target state, then reading it back |

## Running them

Against a real Scaleway account, with credentials in the environment or in the
configuration file:

```bash
export SCW_ACCESS_KEY=... SCW_SECRET_KEY=...

# from the repository
ansible-playbook playbooks/inventaire_serveurs.yml -e zone=fr-par-1

# from the installed collection, by its fully qualified name
ansible-playbook stephrobert.scaleway.inventaire_serveurs -e zone=fr-par-1
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

`arreter_un_serveur.yml` never chooses on its own which machine to stop:
without `-e server_id=<uuid>` it does nothing and says so. An example playbook
that decides for you is a trap, not documentation.
