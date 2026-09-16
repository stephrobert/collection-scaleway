==================================
stephrobert.scaleway Release Notes
==================================

.. contents:: Topics

v0.8.0
======

Minor Changes
-------------

- A guide for operating a Kapsule cluster, covering what to read before touching anything, auditing a version before it audits you, changing what a cluster or a pool holds, rolling through node reboots, and what is deliberately not supported (https://github.com/stephrobert/collection-scaleway/issues/280).
- The Kubernetes modules have now run against the real API. Nineteen modules were shipped in this cycle without a single call ever reaching Scaleway: loaded by Ansible, their arguments built, their documentation published, and nothing more. Fifteen of them are now exercised by the example platform, which creates a Kapsule cluster and a pool, and the two declarative-state modules took their MANAGE path against the real API, and their idempotence on tags is proven there: first pass ``changed``, second pass ``ok``. Their other fields, the mappings above all, are not measured yet: that is where an API injects defaults, normalises and reorders, and where idempotence breaks.
- The fourth unexercised Kubernetes action, ``k8s_node_replace_action``, is exempt for a different reason, and saying so matters: replacing a node is not a question of cost but of a missing wait. Nothing observes the old node gone and its replacement ready, so the operation is available as a primitive and not qualified as an operation.
- The guide's proof table is derived from the recorded real-cloud run rather than written by hand, and distinguishes a module a run proves from one whose only exercised route is shared with another module (https://github.com/stephrobert/collection-scaleway/issues/280).
- Three of the four Kubernetes action modules the example leaves unexercised say the same why: their only acceptable call changes the type or the version of a cluster, so the bill, and that is not a decision an example makes on behalf of whoever runs it. The types and reachable versions are read all the same, which is what a version-drift rule needs.
- filter - ``fleet_diff`` compares the fields a product alone carries, derived from what the normaliser declares rather than listed a second time. A cluster moving from one version to the next used to come out under ``changed_outside_this_shape``, saying that something had moved without saying what, on the most important change a managed cluster has.
- filter - ``fleet_snapshot`` builds the snapshot and ``snapshot_read`` refuses one this collection cannot read: an unknown ``schema_version``, or a truncated file. A truncated file and an empty fleet look alike, and only the second one is information.
- filter - ``resource_facts`` normalises Kapsule clusters, pool nodes and load balancer certificates alongside Instances and load balancers. A rule still names no product field: the seam absorbs the vocabulary, as it always has.
- filter - ``resource_facts`` now carries the resource identifier, and knows load balancers as well as Instances. A load balancer names its state ``status``, its addresses live under ``ip[].ip_address`` and its dates are ``updated_at`` and ``created_at``: absorbing those three differences is what this seam exists for, so no audit rule has to know them.
- filter - ``select_resources`` says what a selector designates among resources read from the API, the counterpart of ``select_hosts`` for what does not come from the inventory. An ambiguous ``name`` is refused; several nodes in a pool are the point, not an ambiguity.
- filter - a cluster carries the end of life of the version it runs, joined from the region's version catalogue at the seam rather than in a rule. One rule then answers the same question for a certificate and for a cluster.
- filter - a finding also carries the C(field) the rule judges, which is information rather than identity: each rule judges exactly one field, so the field adds nothing the rule does not already say. A test holds that invariant, because the day a rule judged two fields two distinct findings would share one identity.
- filter - a finding now carries the ``zone`` it was found in. Without it a vanished finding is indistinguishable from a resolved one, and the only honest answer would be to conclude nothing about the whole fleet.
- filter - a node carries the name of the pool it lives in, joined at the seam. It is the name an operator writes in a selector and reads in the console, where ``pool_id`` is what the API returns.
- filter - a pool of nodes enters the common shape, with its version, its size and its autoscaling. A cluster whose version does not move while one of its pools goes up is a change the cluster alone would not report.
- filter - a product carries what it can carry, and no more. A field a product does not have is not an empty field: the rule that judges it skips the resource rather than calling it compliant, because counting it as compliant would inflate the pass count with resources nobody looked at.
- filter - a version drift is counted within one major version. A major apart is a different question, and counting it in the same number would make it disappear behind a negative count that reads as up to date.
- filter - every audit finding now carries an C(id) that is recomputed on every run and comes out the same tomorrow for the same problem on the same resource. Nothing random, nothing timestamped, or everything would be new each morning. It is what lets a later version count findings as new, persisting or resolved without a heuristic.
- filter - node health conditions are measured, not contracted. ``scaleway.k8s.v1.Node`` declares neither ``conditions`` nor ``public_ip_v4`` nor ``public_ip_v6``, and the real response returns all three. Their absence therefore means unmeasured and never healthy: the day upstream stops returning them, no golden goes red, and a rule reading absence as good news would report a healthy fleet over zero fields read.
- filter - the selector grammar is written once. ``select_hosts`` and ``audit_exceptions`` ask the same question of two populations, and both validated it separately with two sets of messages that had already started to diverge.
- filter - what is shared is the grammar: one criterion and only one, an unknown key refused, a tag combination named. The resolution is not shared, and that is correct: an inventory group is not a pool, and a resource ``id`` has no equivalent in an inventory. The accepted criteria are the caller's to decide.
- generator - an action whose body carries parameters no longer publishes an example that supplies none. The contract cannot settle this: its ``requestBody`` is required while the properties inside it are not, and the parser translates what it reads. The decision belongs to an override, with its reason, and a guard now refuses the silence.
- inventory - ``state`` is accepted as the name ``scaleway.scaleway`` uses for the same idea, so a file written for that collection reads here without being rewritten. ``states`` wins when both are given: it is the one this documentation describes, and the one a user here wrote on purpose.
- inventory - ``variables`` takes a ``destination: source`` mapping, the shape ``scaleway.scaleway`` uses, where the source is a host variable this plugin sets without its ``scaleway_`` prefix. ``hostname``, ``vpc_ipv4`` and ``vpc_ipv6`` are accepted as their names for ``name``, ``private_ipv4`` and ``private_ipv6``.
- inventory - a ``variables`` source this plugin does not set is refused, and the refusal names the sources that exist. Their plugin drops the whole host instead, so a typo empties the inventory, the warning drowns in the rest, and a playbook then runs green having touched nothing.
- inventory - a source missing on one host is a different question from a source that does not exist. A machine with no private address is not a configuration mistake: the variable is not set for that host, and the host stays.
- lookup - ``resource_id`` no longer resolves a name that one product resolves and another refuses. ``acl_id`` exists in both the Load Balancer and Kubernetes, and they are not the same ACLs: the first resolved it, the second cannot for want of a name field, so the first one's resolution stood alone and somebody writing ``acl_id`` while thinking of a cluster rule got a load balancer rule in silence. Returning the wrong product's identifier is worse than returning none.
- modules - Kubernetes is the third product, and it does not enter on its number of routes. The official Scaleway collection ships ``k8s_cluster`` and ``k8s_pool``, both ``state: present/absent``: it creates clusters and offers nothing to operate them afterwards. This collection arrives behind it rather than facing it. Nineteen modules: the clusters, their pools, their nodes, the versions a cluster can move to, and the actions that upgrade, reboot or replace.
- modules - ``k8s_cluster_available_version_info`` next to ``k8s_cluster_info`` is what makes version drift a measurement rather than an impression, and it is the question nobody serves today.
- modules - ``k8s_node_reboot_action`` gains ``wait`` and ``wait_timeout``, and returns the state the node settled in.
- playbooks - ``fleet_changes`` runs the role from the command line, with ``-e snapshot=<file>`` and ``-e output=text|json|markdown``. The Markdown drops straight into a pipeline summary or a ticket: this collection talks to no messaging service, which is the same limit it holds for storage.
- playbooks - ``fleet_report`` accepts ``-e snapshot_to=<file>`` and writes the snapshot there. Redirecting the playbook's output would have captured Ansible's own decoration rather than JSON, which is what the previous instruction suggested.
- roles - ``first_seen`` is stamped on a new finding and carried over on a persisting one, so the date goes back as far as the caller kept its reports. A kept report that carries none says the date is unknown rather than inventing one.
- roles - ``fleet_audit`` accepts ``scaleway_fleet_audit_previous``, the findings of the previous run as you kept them, and sorts this run's findings into new, persisting and resolved. Run daily, an audit that shows the same warnings every morning stops being read by the third morning, which is the failure mode of a recurring tool and more dangerous than an outage because it does not show.
- roles - ``fleet_audit`` gains rules on fields the collection already returned and nobody read: planned maintenance, end of service, allowed actions, available upgrades, expiry, version drift and health conditions. These were not modules to write, they were fields already travelling through the plumbing.
- roles - ``fleet_changes`` reimplements nothing. It includes ``fleet_audit`` and ``fleet_diff`` and aggregates what they left behind; a second comparison written there would drift from the first.
- roles - ``fleet_changes`` says what moved since the last time, in one count per thing that moved. What makes a recurring tool useful is not what it can do: it is that somebody wants to read it again tomorrow, and a report that shows the same warnings every morning stops being read by the third morning.
- roles - ``fleet_diff`` only compares a zone both snapshots measured. A zone that did not answer, and a zone that was simply not read this time, would both make everything it holds look removed, and the report would be perfectly plausible. Such zones come out named, each with which of the two cases it is, and the resources they hold are counted rather than dropped.
- roles - ``fleet_diff`` says what changed between a snapshot you kept and the fleet as it is now, or between two snapshots. A report that announces the same count every morning stops being read by the third morning; the useful question is why there are two more today.
- roles - ``fleet_report`` accepts ``output: none``, for a caller that includes it for its data and for which a second report on screen is noise.
- roles - ``fleet_report`` can read Kapsule clusters, pools and nodes, so the version that adds fleet memory can remember a cluster. It is not read by default: on an account with no cluster it would carry a silent region in every report, and every product is a family of API calls on a billed account.
- roles - ``fleet_report`` now also leaves a versioned snapshot in ``scaleway_fleet_report_snapshot``, so a later run can say what changed rather than what exists. It costs no extra call, because the payloads are already in memory. Every resource carries its kind and its identifier, and that pair is the key: measured on a real account, two machines can carry the same name in one zone and the API then returns two distinct identifiers, so a snapshot keyed on names would merge them into one resource that changed. The snapshot also carries the zones that did not answer, because a comparison computed without them would announce the disappearance of a whole fleet. ``-e output=snapshot`` prints it; where it is kept belongs to the caller, and this collection stores nothing.
- roles - ``kind`` says what is being rolled through, not how it is designated. It is not a criterion, so the selector still carries exactly one of them and one grammar validates both products.
- roles - ``reason``, ``owner`` and ``expires_at`` are required on every exception, and each stops one thing: without a reason it is a rule quietly switched off, without an owner there is nobody to ask whether it still holds, and without an expiry it is not an exception but a change to the policy written in the wrong place.
- roles - ``rolling_reboot`` rolls through the nodes of a Kubernetes pool with the same grammar as machines: ``kind: k8s_node`` plus one of ``group``, ``name`` or ``id``. Somebody who knows how to roll through machines learns nothing new.
- roles - ``scaleway_fleet_audit_level`` is computed and never passed in: ``quiet``, ``changed``, ``action_required`` on a new failing finding or on anything that could not be concluded, and ``baseline`` on a first run. A caller able to force it could produce a report that calls itself calm when it is not.
- roles - ``scaleway_fleet_audit_products`` says which products the audit reads, Instance alone by default, which is what it read before the others existed. A version that started querying Kubernetes and load balancers on every account would multiply API calls nobody asked for.
- roles - ``tags`` is not accepted for nodes. Measured: ``scaleway.k8s.v1.Node`` carries none, ``scaleway.k8s.v1.Pool`` does, and passing a pool's tags off as its nodes' would add a hop you cannot see.
- roles - a ``name`` carried by two resources is refused rather than resolved. Measured on a real account: two machines accept the same name in one zone, so covering both would excuse a resource nobody named, and covering one would depend on the read order.
- roles - a finding that persists does not demand action every morning. It was already reported yesterday, and raising it again at the same rank is the noise this milestone exists to remove.
- roles - a finding that vanished because its zone did not answer never comes out as resolved. A zone that did not answer makes everything it held disappear, and announcing that as resolved tells somebody their problem is fixed when nobody looked. Those come out under their own heading, each with which of the two cases it is.
- roles - a first run is a baseline rather than a fleet where everything is new. No previous run at all and a previous run that found nothing lead to opposite reports, and a caller keeping an empty list would otherwise flood a whole fleet into the new set.
- roles - a last-change timestamp that moved on its own does not make a change. It is a witness rather than a property, and a diff line showing only a timestamp gives nobody an action; those resources are counted apart, neither hidden nor presented as actionable.
- roles - a new failing finding is counted, never the delta. A ``fail`` that appears while another resolves leaves the count unchanged, and deciding on the delta would silence the new one behind its neighbour's good news.
- roles - a policy now carries ``exceptions``, for the case every used policy meets within a week: yes, that bastion must have a public address. Without them the only way out is to delete the rule, which loses it for the whole fleet in order to excuse one machine.
- roles - a region that did not answer is named with the product it did not answer for. A region that answers for clusters and not for versions is not the same situation as a silent one, and a name that merged them would make the report useless for acting on.
- roles - a region that did not answer stops the roll rather than narrowing it. Rolling through a fleet that is only partly known is how a roll takes down what it could not see.
- roles - a rule judging a field no read product carries fails the run and names what to add. A rule that judges nothing is a silence, not a compliance: it produces a green report where nobody checked anything, and nothing in that report says so.
- roles - a selector names exactly one of ``id``, ``name`` or ``tags``. Two criteria ask two questions and the answer would depend on the order they are read in, and a selector with no criterion at all would cover the whole fleet, which is a removed rule wearing an exception's clothes.
- roles - a suppressed finding is not a resolved one. An exception changes a status, it does not make the problem go away, so it stays among the persisting findings with its status.
- roles - aggregating two verdicts keeps the higher one. Keeping the lower would let a calm half hide a half that is not, which is the simplest way to manufacture a reassuring report.
- roles - an exception changes a finding's status, it never removes it. The finding stays readable with ``status: suppressed`` and the ``suppressed_by`` that covers it, and it is counted apart. A finding that was erased is a problem nobody knows about any more, which is what writing the exception rather than removing the rule is meant to avoid.
- roles - an exception that matches nothing is reported and not refused. One left behind by a destroyed machine is housekeeping, not a policy error.
- roles - an expired exception becomes a finding of severity ``fail`` rather than a refusal. Refusing the whole policy over one stale line would switch off the audit on the day an exception expires, which is the opposite of what is wanted then.
- roles - anything that could not be measured ranks with a new failing finding: an unmeasured zone, a finding that could not be concluded, an expired exception, a zone two snapshots do not both cover. A fleet nobody could read is not a calm fleet.
- roles - for nodes, ``group`` means the pool, which groups nodes the way an inventory group groups machines. The list comes from the API rather than the inventory, which serves Instance, Elastic Metal and Apple Silicon and nothing from Kubernetes.
- roles - no composite score. A ``83/100`` looks good and cannot be traced back to what moved it, so every line counts one named thing and is explainable on its own.
- roles - the JSON and Markdown renderings of ``fleet_audit`` now carry the expired exceptions alongside the fleet's findings, and the status of each. A pipeline reading the JSON would otherwise never see the expiry, which is the very failure this filter exists to prevent, one level up.
- roles - the level a comparison earns is computed, never passed in: ``quiet`` when nothing is new, ``changed`` when something moved, and ``action_required`` when something could not be measured. A caller able to force it could produce a report that calls itself calm when it is not. Nothing new prints one line, on purpose.
- roles - the level is computed and never passed in: ``quiet``, ``changed``, ``action_required`` and ``baseline``. A caller able to force it could produce a report that calls itself calm when it is not, which is exactly what a recurring tool must not be able to do.
- roles - there is deliberately no ``since`` field. Nothing in a set of kept findings says when the previous run happened: the oldest ``first_seen`` dates the oldest finding, and on a run where nothing was new it dates nothing at all.
- roles - with no snapshot handed back, the infrastructure comes out as ``not compared`` rather than as zero changes, and a severity with no earlier run to compare against carries no delta rather than ``(+0)``. Not having looked is not the same as nothing having moved.

Breaking Changes / Porting Guide
--------------------------------

- filter - a snapshot carries typed scopes, ``{type, name}``, and refuses a bare string. ``fr-par`` is a region and ``fr-par-1`` a zone; nothing in the string says which, and guessing from the shape would work on Scaleway today and break on the first product that names things differently.
- filter - the common shape says ``scope`` and ``scope_type`` where it said ``zone``. Instance and Load Balancer are zonal, Kapsule is regional, and filing a region under a field named zone worked while saying something false. Nothing published ever carried the old name: the snapshot schema did not exist in 0.7.0, so the vocabulary is corrected before its first publication rather than migrated after.

Bugfixes
--------

- The example platform no longer leaves a security group behind. A Kapsule cluster creates one for itself and ``delete_additional_resources`` does not take it: measured five times over three minutes after the cluster was destroyed, it was still there every time. It does not carry the platform's prefix, so the guards that filter by prefix ignore it; the launcher now removes it after destruction and before the residue check, so that check stays the judge.
- The public gateway waits up to sixty minutes instead of ten. Measured on a real account: one took fifty-six minutes to reach ``running``. The provider gave up at ten, never recorded the resource, and the destroy that followed took eighteen resources and left that one behind, billed and outside the state. A timeout that gives up does not leave a half-created resource, it leaves a whole one nobody tracks.
- The published archive no longer carries ``changelogs/.plugin-cache.yaml``, a cache ``antsibull-changelog`` rebuilds and git ignores. A fresh clone does not have it, so the CI published an archive without it while a workstation build published one with it, under the same version number, and a version published on Galaxy is immutable. Packaging now asks git what it ignores under the collection and refuses an archive that carries any of it.
- filter - an audit finding identified its resource by name, and a name is not an identity: measured on a real account, two machines accept the same name in one zone and the API then returns two distinct identifiers. Two homonymous machines produced indistinguishable findings, and grouping refusals by name merged them into one, so the count of examined resources was short by one. Both now go through the resource identifier.
- filter - an expiry in the past is reported with the number of days it actually is. Python's ``timedelta.days`` floors, so a certificate expired thirteen days and ten hours ago was reported as fourteen, always erring towards alarm.
- generator - a generated module, a golden and the runtime's resolution tables are written atomically, so a concurrent reader never sees an empty file. Measured while regenerating one module: fifty-six reads at a size other than the final one, all truncated, at 0, 4096, 8192 and 12288 bytes for a 12809-byte file.
- generator - an interrupted generation no longer leaves a half-written versioned artefact on disk, nor a leftover temporary file next to it.
- modules - ``instance_snapshot_action`` requires the bucket and the key it exports to, and its example shows both. Exporting a snapshot without saying where does nothing useful, and it had the same shape of defect, found by the guard written for the first one.
- modules - ``k8s_cluster_acl_action`` requires the ACLs it adds, and its published example shows one. Adding no ACL is accepted by the API, changes nothing, and the example was perfectly copyable: somebody copying it learned nothing about what the module does.
- modules - ``k8s_node_reboot_action`` waits for the node to be back before returning, instead of returning on an accepted trigger. A rolling reboot would have moved to the next batch while the first was still rebooting, which is the whole thing a rolling reboot exists to avoid.
- modules - a documentation line no longer exceeds what ``ansible-test sanity`` accepts. PyYAML never breaks inside a word, so a description carrying a URL of over a hundred characters in mid-sentence was wrapped after the URL, on a line of nearly two hundred characters. The rendering now narrows its width for the one block that needs it rather than reflowing every description in every module.
- modules - the wait observes what the contract declares: ``status``, not the ``state`` Instance uses, and ``ready`` after passing through ``rebooting``. Waiting on the wrong field would fail the action after ``wait_timeout`` on a node that had come back.
- roles - a Kapsule finding can become ``resolved``. ``fleet_audit`` passed only the Instance zones as what this run measured, and Kubernetes reads are regional: a finding whose scope is a region therefore came out as unmeasured even when the read had answered perfectly. The false verdict was the inverted one, refusing to call resolved what is, and it was a lie about a measurement that succeeded.

New Modules
-----------

- stephrobert.scaleway.k8s_cluster - Manage a Scaleway Kubernetes cluster.
- stephrobert.scaleway.k8s_cluster_acl_action - Perform an action on a Scaleway Kubernetes cluster ACL.
- stephrobert.scaleway.k8s_cluster_acl_info - Gather information about Scaleway Kubernetes cluster ACLs.
- stephrobert.scaleway.k8s_cluster_available_type_info - Gather information about Scaleway Kubernetes cluster available types.
- stephrobert.scaleway.k8s_cluster_available_version_info - Gather information about Scaleway Kubernetes cluster available versions.
- stephrobert.scaleway.k8s_cluster_info - Gather information about Scaleway Kubernetes clusters.
- stephrobert.scaleway.k8s_cluster_node_info - Gather information about Scaleway Kubernetes cluster nodes.
- stephrobert.scaleway.k8s_cluster_pool_info - Gather information about Scaleway Kubernetes cluster pools.
- stephrobert.scaleway.k8s_cluster_reset_admin_token_action - Perform an action on a Scaleway Kubernetes cluster reset admin token.
- stephrobert.scaleway.k8s_cluster_set_type_action - Perform an action on a Scaleway Kubernetes cluster set type.
- stephrobert.scaleway.k8s_cluster_type_info - Gather information about Scaleway Kubernetes cluster types.
- stephrobert.scaleway.k8s_cluster_upgrade_action - Perform an action on a Scaleway Kubernetes cluster upgrade.
- stephrobert.scaleway.k8s_node_info - Gather information about Scaleway Kubernetes nodes.
- stephrobert.scaleway.k8s_node_reboot_action - Perform an action on a Scaleway Kubernetes node.
- stephrobert.scaleway.k8s_node_replace_action - Perform an action on a Scaleway Kubernetes node replace.
- stephrobert.scaleway.k8s_pool - Manage a Scaleway Kubernetes pool.
- stephrobert.scaleway.k8s_pool_info - Gather information about Scaleway Kubernetes pools.
- stephrobert.scaleway.k8s_pool_upgrade_action - Perform an action on a Scaleway Kubernetes pool upgrade.
- stephrobert.scaleway.k8s_version_info - Gather information about Scaleway Kubernetes versions.

v0.7.0
======

Release Summary
---------------

Compose operations. The previous release turned modules into commands
somebody remembers; this one turns those commands into something other people
build on. The chains are roles now, callable by their full name from anybody's
playbook, with their arguments validated before the first task. The playbook
is the ergonomics, the role is the operational API, the module is the
technical one, and nothing a user types changed.

Every operation returns a result a machine reads rather than a sentence, with
its counts derived from the names it carries so the two cannot disagree. They
all accept the same way of saying what to act on: a group, a name, or tags,
with the refusals that already existed now holding for all three forms. In
check mode they render a plan a reviewer can read, and a new record says why
that plan is never replayed.

Two things are new to run. ``fleet_audit`` judges a fleet against a policy,
read-only, and it is the one that earns a place in a schedule rather than
being used when you need it; its rules are data, and so are their severities,
because the public address of a bastion is normal and that of a database is
not. And an Event-Driven rulebook reacts to an alert by reading the fleet:
detect then diagnose, never detect then modify, which is the design and not a
first step towards something else.

Both are replayed on every run, like everything else here.

Minor Changes
-------------

- A plan describes the fleet as it was read, and is never replayed: running the operation reads it again. An approval chain therefore approves an intention rather than a set of instructions, because the inventory can be served from its cache and a cached state is not a state. See ADR-020, which also says what that costs.
- Each product is now asked only the zones its own contract declares, and the report carries ``zones_not_offered`` beside ``zones_unmeasured``: a zone a product does not offer is a fact about the product, not a measurement that failed. The map comes from the versioned contracts, written by the generator into ``module_utils`` and held by ``check:generated``. Typing the eight zones into a role would have been a second source of the contract, wrong the day the product opens a zone.
- Every shipped operation now returns a machine-readable result alongside its sentence, built by the new ``stephrobert.scaleway.operation_result`` filter. A pipeline, a ticket or a monitoring system reads ``scaleway_operation`` instead of parsing standard output, and an output parser breaks on the first reworded sentence. Each operation also leaves its own ``scaleway_<operation>_operation``, which survives the next one.
- New ``stephrobert.scaleway.fleet_audit`` playbook and role: the fleet judged against a policy, read-only, with a severity per finding and the same three outputs as the fleet report. ``rolling_reboot`` is used when you need it; this is the one that earns its place in a schedule, and that is the difference between a useful tool and a tool somebody integrates into their operations.
- The collection now ships an Event-Driven Ansible rulebook, ``stephrobert.scaleway.diagnose_on_alert``: an alert posted to its webhook makes it read the fleet. **Detect then diagnose, never detect then modify**, and that boundary is the design rather than a first step towards something else. An event is reachable by a third party in a way a command line is not, so a rule that powered machines off on a malformed payload would be the failure mode the chains refuse by construction, moved somewhere nobody reviews. A test refuses a rulebook that triggers anything that writes, and it derives what a playbook does rather than trusting its name.
- The operational playbooks are now roles, callable by their full name from anybody's playbook: ``stephrobert.scaleway.fleet_report``, ``stephrobert.scaleway.power_schedule`` and ``stephrobert.scaleway.rolling_reboot``. Each one carries a ``meta/argument_specs.yml``, so Ansible validates its arguments before the first task rather than failing at the third. The playbook is the ergonomics, the role is the operational API, the module is the technical one; ``doctor`` stays a playbook, because an entry command has nothing to compose. Nothing a user types changed.
- The operations that act on machines now take a selector, and it is the same one everywhere: exactly one of ``group``, ``name`` or ``tags``, plus ``match`` set to ``all`` or ``any`` when several tags are given. ``all`` is the default because it is the narrower selection, and for an operation that writes, erring on the safe side means touching fewer machines rather than more. ``group: X`` on the command line stays, as the shorthand for ``selector: {group: X}``, because what a user types is published surface.
- The product admission gate now answers a second question, the one that decides adoption rather than correctness: which recurring operation does this product unlock? A product that adds modules no chain calls adds names to a README and nothing to anybody, and 0.6.0 showed the opposite by becoming usable without one new module. The answer is derived from the shipped operations rather than declared, so it cannot drift: an operation calls modules, a module names its product. A product with no operation is admitted while saying so, never refused, because refusing would forbid adding a contract before writing the chain that uses it.
- The rulebook is replayed on every CI run, and by ``mise run rulebook`` locally: an emulator, ansible-rulebook on the rulebook of the installed collection, an alert posted the way a monitoring system would, and the diagnosis played by the rule. What is measured is not that the command exits zero, which a rulebook that never fires would also do, but that the playbook ran and that an event with no status ran nothing.
- The sources come from the ``ansible.eda`` collection, which you install yourself. Measured: ansible-rulebook carries webhook code inside its own package, but neither ``ansible.eda.webhook`` nor a bare ``webhook`` resolves without that collection present. This collection does not declare it as a dependency, because somebody installing modules to power a fleet down at night should not be made to pull an event framework they never asked for.
- filter - ``audit_findings`` evaluates the policy. The rules are data, not code: an audit whose rules are carved into its playbook is its author's opinion made executable, and the first team without the same mandatory tags has to fork it. The severity is data for the same reason, because the public address of a bastion is normal and that of a database is not.
- filter - ``operation_result`` derives its counts from the names rather than taking them alongside. A ``changed: 3`` passed next to the list of changed machines would be a second source of one fact, and two sources of one fact end up disagreeing; here the count is the length of the list. It refuses a refusal without a reason, a count passed instead of a list, and an operation with no target or no mode. When nothing could be examined the totals are ``null`` rather than ``0``, because nothing measured is not nothing found.
- filter - ``product_zones`` splits asked zones into what a product offers and what it does not, and refuses a product absent from the map: one without modules has nothing to be asked.
- filter - ``resource_facts`` normalises what a reading module returned into the shape the audit rules are written against, so a rule never names a product's own fields: ``last_change`` rather than ``modification_date``, ``public_addresses`` rather than ``public_ips``. Adding a product adds a normaliser, not a line inside a rule, which is what keeps policy-as-data from becoming a giant playbook of rules per product. It refuses a product it does not know rather than normalising it as best it can, because a machine with no tags and a machine whose tags could not be read look alike, and the first is a finding while the second is an ignorance.
- filter - ``select_hosts`` unifies four refusals that already existed separately and now hold for all three forms: an ambiguous name is refused rather than settled, naming the candidates; a name is compared exactly, where the API filter matches by prefix; an unknown key is refused rather than selecting nothing, because a typo and an empty fleet look alike; and two criteria at once are refused, because the answer would depend on the reading order. ``fleet_report`` does not take a selector: its target is a list of zones, and forcing a host selector on it would be uniformity that lies about what the operation does.
- roles - ``fleet_audit`` refuses a policy with no rule, a rule nothing can settle, and a severity that is not one. The first would make emptying the policy file the shortest path to a green report; the second would report a resource as compliant for the sole reason that nobody evaluated it. Two rules the issue proposed are deliberately not written, and the refusal names them with the reason: neither an unused reserved address nor a load balancer backend has been measured on any available target, and a rule written on the supposed shape of an object never seen judges from an invention.
- roles - ``fleet_report`` leaves its report in ``scaleway_fleet_report_result``, so a calling playbook can act on it instead of reading it off the screen. Every other fact a role sets is prefixed and internal: a role included in somebody else's play shares their namespace, and a bare ``set_fact: machines`` would overwrite whatever they call ``machines``. A test refuses an unprefixed one, which is a defect that only exists once the code is a role.
- roles - a shipped playbook calls its role and never reimplements it, and a test refuses anything else. Two implementations of one operation always end up disagreeing, and the day they do, the documentation describes one while the user plays the other.
- roles - in check mode, ``power_schedule`` and ``rolling_reboot`` now render a plan a reviewer can read: the target, how many machines were selected, what would change, what is already compliant and what is refused with its reason. The same data is in ``scaleway_operation``, so a pipeline can make it an artifact and have somebody approve it before the operation runs. The plan is a rendering of the result structure, never a second computation.

Bugfixes
--------

- The pre-push gate announced replaying the CI while silently omitting two of its jobs: the quickstart journey and the event reaction, both added during this cycle. It reported ``12 steps of the CI replayed`` where the pipeline carried fourteen, and its own header promises to **name** whatever it cannot replay. A gate that hides its holes is the green on zero files examined this repository exists to prevent. Both are replayed now, and a test derives the coverage from the workflow itself: a job that is neither replayed nor named fails at the moment somebody adds it, rather than at the next release.
- The release workflow now runs Galaxy's own importer on the built archive, before publishing rather than during it, so a collection Galaxy would refuse is refused here. The importer is installed in that job rather than in the repository's lock file: it pulls around forty packages, including the very tool this repository refused for that reason, and it has no value outside a publication.
- roles - ``fleet_audit`` counted findings where the result contract counts resources. ``examined`` is the sum of what changed, what was already compliant and what was refused, so passing one refusal per finding counted a machine twice as soon as it broke two rules. On a fleet where each machine breaks exactly one, the total was right by coincidence, which is the shape a false green takes. There is now one refusal per resource, carrying the rules it broke as its reason, and the detailed findings stay where they were.
- roles - ``fleet_report`` reported two zones as unmeasured on every clean run, and neither was unmeasured. The Load Balancer contract declares eight zones where Instance declares ten, and the module refused the rest before any call. ``zones_unmeasured`` carries this collection's most repeated claim, that nothing measured is not nothing found, and a signal that cries wolf is a signal nobody reads: the day a zone really does not answer, the line would have looked the same.
- roles - each role now ships a README, which Galaxy requires: the import of the whole collection is refused without one, with ``No role readme found``, and that refusal arrives after the gate, the checks, the sanity run and the archive have all passed. Neither ``ansible-galaxy install`` nor the packaging step applies that rule. The pages are derived from each role's argument spec rather than repeating it, and carry one real invocation each.

v0.6.0
======

Release Summary
---------------

Operate, do not assemble. The previous releases built modules; this one turns
them into commands somebody remembers. Seven playbooks ship instead of three,
each answering a need rather than demonstrating a module: check a setup,
report on a fleet, power a group down for the night, reboot production in
batches. Each one says what it refuses to do, which is the half that is
missing everywhere else and the one that keeps a tool from misleading.

Two things you no longer need in order to try this. An account: a quickstart
brings up a local emulator and a fictional fleet with one command, and the
same playbooks then run against a real account by changing the endpoint and
the credentials. And a module call to find an identifier: the ``resource_id``
lookup resolves the name you already know, from a table derived from the
versioned API contracts rather than written by hand.

The rest is about being able to trust what is written here. The shipped
playbooks are renamed to English, which is a breaking change and the only one.
Every page that carries a measured number now derives it, including the one
recording what this project knows about its own adoption, and what it does
not.

Minor Changes
-------------

- A quickstart now lets anyone try the collection without a Scaleway account, without credentials, and without spending anything. ``docker compose up -d`` starts a local emulator and creates a small fictional fleet; from there the shipped playbooks run exactly as they would against a real account, and switching over changes the endpoint and the credentials and nothing else. The page says what the emulator does not prove, because an emulator that lies without saying so teaches a false green. The whole journey is replayed on every CI run, so it cannot go stale quietly.
- A scheduling guide now says how a shipped playbook gets called twice a day rather than by hand: a scheduled pipeline, ``ansible-navigator``, and AWX. All three start from ``power_schedule``, take their credentials from the platform rather than from a file, and use the published execution environment instead of explaining how to build one. The page says which path has actually run: the scheduled pipeline is replayed here on every run, ``ansible-navigator`` was measured once by hand, and the AWX shapes have never been executed. Presenting the three as equivalent would be claiming three things and having measured one.
- New ``stephrobert.scaleway.doctor`` playbook, the first command to run against a new setup. It checks the ansible-core that will run the modules, the Scaleway SDK the playbook interpreter can import, where the credentials come from, and whether the API answers in a zone. **Every check runs**: none aborts the others, so one run reports every problem rather than the first one. Finding one problem per run is how a first contact is spent on nothing.
- New ``stephrobert.scaleway.fleet_report`` playbook: the whole fleet in one read-only command, with three outputs for three readers. ``text`` for a terminal, ``json`` for a pipeline, ``markdown`` for a ticket. It creates nothing and changes nothing, which is what makes it safe to run first, and it answers the question asked most often: where is the fleet and in what state.
- New ``stephrobert.scaleway.power_schedule`` playbook: bring a named inventory group to a power state, which is the schedule that pays for itself twice a day. Machines running at night that nobody uses are the most ordinary waste there is, and the collection already had every piece: the inventory groups by tag, the action module powers on and off. Nothing joined them, so everyone wrote the loop again.
- New ``stephrobert.scaleway.resource_id`` lookup plugin. Half of the modules in this collection act on a sub-resource whose identifier only the matching ``_info`` module returns, so a playbook had to call a module, register its result and dig a UUID out of it. The lookup returns that identifier from the name you already know. Its resolution table is derived from the versioned API contracts rather than written by hand, so a resource that stops being listable, or that loses its ``name`` field upstream, leaves the table at the next generation instead of staying a promise. Twelve identifiers resolve today; four do not, and the plugin says why rather than reporting them as unknown. See #177.
- New ``stephrobert.scaleway.rolling_reboot`` playbook: reboot a named inventory group in batches, waiting for each batch to come back before touching the next. A lot of work went into making the ``reboot`` action and its check mode trustworthy, and none of it showed: someone wanting to restart production progressively wrote ``action: reboot`` over a group and hoped.
- The project now records what it knows about its own adoption, and what it does not, in ``ADOPTERS.md``. The Galaxy download counter is deliberately absent from it: a pipeline reinstalling on every run weighs as much there as a team using the collection daily, so steering anything on that number means optimising something nobody can read. Every recorded use names where it was said, and an entry without a source fails the derived block rather than being published as a measurement. Saying you use it no longer means opening a bug report: the issue chooser now points at a discussion for that, and CONTRIBUTING describes how a chain someone else wrote reaches the shipped playbooks and the recipe chapter.
- The shipped playbooks now carry a recipe chapter, organised by need rather than by module: what someone tells themselves before they go looking. Each recipe gives the command, what to check first, and **what the playbook does not do**, which is the half that is missing everywhere else and the one that keeps a tool from misleading. The recipes live in the playbooks README, which the documentation site assembles as its task page, so there is one source and it is the one that runs.
- ``doctor`` never prints a credential. It names where one comes from, which is what repairs a setup, and a report can be pasted into an issue as is.
- ``doctor`` separates three states that are not the same thing: the check ran and the answer is yes, the check ran and the answer is no, and the check could not run at all. A zone that does not answer has not been measured to be empty. ``Ready.`` is printed only when everything was checked **and** everything passed, so an unreachable API never reads as a success.
- ``fleet_report`` never counts a zone it could not read. **A zone that does not answer has not been measured to be empty**, so it is named as unmeasured rather than contributing a zero, and when no zone answers at all the playbook says so instead of printing a total. A report that counted an unreachable zone as empty would be worse than no report, because it would be a plausible one.
- ``power_schedule`` is idempotent, and the idempotence lives in the playbook rather than in the module. An action is a trigger and not a state, so ``instance_server_action`` reports ``changed`` every time by design. The playbook reads each machine first and acts only on those not already where they should be: measured against a fleet, the first pass acts on three and the second reports none changed.
- ``power_schedule`` refuses before it writes. It has no default target, because a schedule that guesses which machines to power off is how a fleet goes down one evening; a named group that holds no host fails rather than exiting quietly; and machines in ``starting``, ``stopping`` or ``locked`` are named and left alone rather than swept up. With no group named at all it does nothing and says so, which is the convention the other shipped playbooks follow.
- ``resource_id`` matches the name exactly, and refuses rather than choosing. The Scaleway ``name`` query filter matches by prefix, which the contract states for Instances: ``server1`` returns both ``server100`` and ``server1``. The filter is sent so a whole fleet is not paginated, and the exact comparison is always done locally. No match and several matches both fail, and the message names what was found nearby or which candidates collided. Returning the first of several would make the playbook act on a resource nobody designated. See ADR-0019.
- ``rolling_reboot`` records the state before touching anything: a machine that is not running is left alone and named, because a rolling reboot that starts machines has done something nobody asked for. A batch that does not come back stops the roll and names what was left to do, rather than continuing over a fleet a third of which may be down.
- ``rolling_reboot`` waits on what it observes, never on a duration. The action module already watches a machine leave ``running`` before accepting that it came back, and refuses to conclude when it never saw it change; the playbook puts that wait inside an async job so a batch waits for jobs rather than for a delay. A test reads both files and fails on any ``pause``, ``sleep`` or timed ``wait_for``, because a fixed delay that works today is indistinguishable from a correct wait until the day it is not.

Breaking Changes / Porting Guide
--------------------------------

- The shipped playbooks are renamed to English. ``inventaire_serveurs`` becomes ``list_servers``, ``detail_dun_serveur`` becomes ``server_details``, and ``arreter_un_serveur`` becomes ``stop_server``. A playbook name is what a user types, so it is published surface, and the rest of the collection is in English. **The old names stop resolving, and nothing can soften that**: Ansible exposes no playbook loader, so ``meta/runtime.yml`` cannot redirect an old playbook name to a new one. Update any ``ansible-playbook stephrobert.scaleway.<name>`` call accordingly.

Bugfixes
--------

- Cutting a release whose cycle added no module, option or return value left the appearance journal pointing at the version just published, and the next check refused with ``a release went out without the journal being frozen``. The journal had been frozen; the freeze had returned early, skipping the part that moves the preparation version on. The message was right about the fact and wrong about the culprit, which costs more than a silent refusal. What is skipped when there is nothing to date is the block, because an empty one would publish a version badge on nothing. Found while cutting this release, whose contents are playbooks, a lookup plugin and documentation.
- Terraform outputs that cross into a module no longer carry their scope. The Scaleway provider prefixes its identifiers with ``fr-par-1/``, and a module receiving one composes a URL the API rejects. Four of the five outputs kept it, which made the ``certificate_ids`` ordering measurement unreachable on the only target where it can run. A guard now refuses a scoped output before the first playbook starts, and names all the offending ones rather than the first. See #186.
- inventory - the ``strict`` option promised a stop it cannot produce on its own. Ansible downgrades an inventory plugin failure to a warning and exits zero, so a revoked key made a run green on an empty fleet while the option sat at its default ``true``. The option description now says so, and names ``ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED``, which is the setting that makes the refusal visible. The behaviour itself does not change: it was already measured both ways on every integration run, and already explained in the dynamic inventory guide.
- playbooks - ``power_schedule`` reported ``acted on`` in check mode, where the action module announces a change without sending it. An operator rehearsing a shutdown read that their machines were off while they were still running. The report now distinguishes a rehearsal from a run.

New Plugins
-----------

Lookup
~~~~~~

- stephrobert.scaleway.resource_id - Resolve a Scaleway resource name into its identifier.

v0.5.0
======

Minor Changes
-------------

- A new comparison strategy, ``id_list``, compares a requested list of IDs with the list of objects the API returns. It is **not** a human decision: the generator measures both sides of the contract, the request declaring an array and the read schema declaring an array of objects, and comparing those two directly has only one possible verdict. Exactly two managed parameters are in that case across both products, and a test names them so the count cannot drift in silence. The runtime refuses to project anything that is not a list of objects carrying an ``id``, and the diff goes through the same projection, which is the invariant ADR-009 already carried.
- Every generated module now publishes an ``attributes`` section, the place Ansible normalises for declaring ``check_mode`` and ``diff_mode`` support. Until now the collection README claimed both and the module pages said nothing, so a reader on Galaxy had to take the README's word for it, which is exactly what this repository's own criterion forbids. The values are not intuited from the class: a test exercises the runtime for each of the three kinds and asserts the declared support against what actually happens, and ``mise run docs:quality`` refuses a page announcing a support its kind does not hold. Three mutations prove those refusals bite.
  The attributes carry no ``version_added``: check mode has worked since each module's own first version, and only the declaration is new. Dating the declaration would suggest new support, which would be a second way of lying about a date.
- Every operation now carries a retry policy, and the runtime honours it. A read replays on ``429``, on the ambiguous ``5xx`` and on transport failures; a managing module's write replays only on ``429``, where the rate limiter answered before the API and the request was not processed; the operation an action module triggers is never replayed, because a reboot played twice is not a reboot. See ADR-018.
- Managing modules now say how to clear a field the contract declares clearable. Measured against the real account: the empty value of the type clears it (``description: ""``, ``tags: []``), while an explicit ``null`` is accepted with a 200 and changes nothing, because this API reads ``null`` as "field not provided". An explicit ``null`` is therefore refused before anything is read, and the refusal names the value to write. ``int`` and ``bool`` have no empty value and cannot be cleared; their pages say so. See ADR-016.
- Options for clearable fields recover their natural type on the published page. They were ``type: raw`` with the default ``__unchanged__``, and their ``choices`` and ``elements`` had to be stated in prose; they now publish the type, choices and elements of the contract, and no default at all. An omitted option is told from an explicit ``null`` by a witness that publishes nothing.
- The credential precedence now has a single definition, ``PRECEDENCE`` in the runtime. One test puts the three sources in conflict on the same field and asserts which wins; another reads the collection README, the documentation fragment and the runtime architecture page, and requires each to name the three sources in that order. A third pins the sentence published up to 0.4.0 and proves the check refuses it.
- The version of ``mise`` and the SHA of the action that installs it were copied into nine steps across four workflows. Dependabot keeps the SHA fresh, because that is a dependency to it; it does not keep ``version:`` fresh, because that is not. One of the nine could therefore drift alone with nothing to notice. Both now live in a single composite action, and ``mise run outillage`` refuses a second declaration, with two mutations proving the refusal bites. ``mise.toml`` also gained a ``min_version``, which is a different thing: the pin says what CI installs, the floor refuses a ``mise`` too old to read the file.
- ``Retry-After`` is honoured in both forms RFC 9110 allows, a number of seconds or an HTTP date. An unreadable header falls back to the default wait rather than failing the module, and a delay beyond the ceiling is not waited for: the module would look frozen, and the error carries the header.
- ``docs/architecture/runtime.md`` describes the transport that exists. It still explained that requests went through ``scaleway_core.api.API._request`` and that a guard watched that private method's signature, a decision reversed before 0.4.0. Every responsibility of the transport is now named with the place that holds it, and the absence of a retry policy is named as a deliberate gap rather than left to be discovered. See ADR-014.
- ``lb_backend`` gains the ``host`` option, and ``lb_backend_info`` returns it. Scaleway added the field upstream: it sets the HTTP Host header or the TLS SNI used when connecting to backend servers. Nobody wrote this option by hand; the drift was detected, the contract re-synced, and the generator produced it.
- ``mise run api:privee`` refuses an underscored attribute of a third-party library anywhere in what the collection ships. The rule existed as a paragraph and had already been broken once by the very change that stated it. Two mutations prove the refusal bites, including the counter-example that ``self._client`` stays allowed, without which the control would refuse the whole runtime and be turned off.
- ``mise run chiffres`` now reads numbers spelled out in letters, not only digits, for the vocabulary of CI: jobs, scanners, required checks, gates. That is the class of defect that had escaped it. A guard keeps it from reading a count inside a compound term such as ``Day-2 operations``, and two mutations prove both the reach and the guard. What the control still cannot see is written in its own docstring, with what it leaves to human review.
- ``mise run docs:examples`` now analyses both READMEs, not only ``docs/``. The collection README is what Galaxy publishes, so it holds the first playbook a user copies, and nothing checked it: a renamed module would have stayed there until somebody tried. Adding it surfaced that a README publishes **tasks**, not plays; those are wrapped in a minimal play before the syntax check rather than refused, since refusing them would leave the most-copied examples uncontrolled. Two mutations prove both halves.
- ``mise run introductions`` checks that the appearance journal still tells the truth about what is published: it refuses a version in preparation that is not later than the released one, and lists every module, option and return value that no dated block covers yet.
- ``mise run security`` and ``mise run security:trust`` now refuse to run when a workflow scanner installed locally is not the version CI installs. The gate that exists to replay CI had reported **12/12 green** on a tree CI then refused: zizmor was 1.28.0 locally against 1.30.0 in CI, and the audit that reddened the pull request was introduced in 1.30.0. A gate judging with a different tool than the one it claims to replay produces a green worth nothing. The versions are read from the workflows that install them, which keeps a single declaration.
- ``plumber`` moves from 0.4.51 to 0.4.55. The pin had three different values at once: the workflow said 0.4.51, the maintainer's toolchain 0.4.52, and upstream published 0.4.55. Verdict on this repository is unchanged, grade A with no finding at any severity.
- ``python scripts/example.py reel --enregistrer <file>`` puts ``feint proxy`` between the collection and the cloud and writes every exchange. An assertion returns a boolean; when it fails it says what it expected, never what the API answered, and a play that dies on one carries away everything after it. Two billed runs returned nothing about the question asked before the third recorded the answer even though the measurement task was skipped again. See ADR-015.
- ``scripts/example.py`` now takes a lock while a platform is up. It refuses a second run, and before destroying it compares the tree with the one that deployed, naming the commit to recover when the two diverge. A real run had left billed resources alive: the ``finally`` was reached and did launch the destroy, but ``examples/stack/`` is versioned, lock file included, and a branch switch during the run replaced the definition **under** the deployment. Terraform then refused to load a provider its own definition no longer named. A ``finally`` only protects if the command it launches can still run, and that limit was written nowhere. Three mutations prove the refusals bite, and the tests build a lock rather than touching any cloud.

Bugfixes
--------

- The collection README announced the credential precedence **backwards**. It read ``environment, then configuration file, then module parameters``, while the runtime has always let a module parameter win over the environment, which wins over the configuration file. The documentation fragment said it correctly, so two published pages contradicted each other. Someone managing several projects could believe an environment variable overrode an explicit parameter, and work on the wrong project without the API saying anything: the credentials are valid, just not the intended ones.
- The collection README claimed the inventory's variables were **all any module needs**. Measured: 25 of the 50 modules work with what the inventory posts, and the other 25 act on a sub-resource carrying its own identifier that no machine discovery can supply. The page now says which, and shows the ``_info``-then-manage chain that supplies the missing identifier.
- The examples of an action module no longer say "an Instance" whatever the product. The phrase was hard-coded, and it happened to be right only because ``instance_server_action`` is the only module whose action carries an enum; the next product with one would have published "Migrate an Instance" for a load balancer. The examples now name the resource the page is about.
- The repository README announced two contradictory counts of CI jobs fourteen lines apart, one derived and one written by hand, and described ``mise run check`` as what a pull request has to pass, which stopped being true when CI grew jobs that ``check`` does not replay. Both are corrected, and the supply-chain row now names the workflow scanners instead of counting them.
- The runtime no longer writes ``requests.Response._content``. It carried the ``x-total-count`` header into the response body by rewriting a private attribute of a third-party library, in a transport that had been rewritten precisely to stop depending on a private method of the Scaleway SDK. The header is now merged into the body **that was read**, which is what the paginator actually needed: the behaviour is unchanged and a regression test follows the header all the way to what ``request`` returns.
- Three ``*_type_info`` pages claimed "The API contract names no payload field for this operation", while the contract names ``servers`` or ``volumes``. Their response wraps a map, which the parser read as neither a list nor a single object, so the payload field was lost and the page published ``contains: {}`` alongside a sentence that says the opposite of what the contract says. The pages now return the field the contract names, and describe what it holds.
- ``--check`` on an action module now sees what a rehearsal is for. It exited before building the API client, so it reported ``changed`` with no SDK, no credentials and no check that the resource exists, while the same play without ``--check`` failed cleanly. The client is now built, and the resource read when the contract offers a unitary read, before returning without sending anything. When no unitary read exists, the message says the resource was not verified rather than implying it was. See #168.
- ``.github/zizmor.yml`` disables the ``self-repository`` audit, with the measurement that justifies it. zizmor 1.30.0 asks for ``uses: $/...``, which GitHub has supported since July 2026; **actionlint 1.7.12 rejects it** as an invalid format, and that is both the latest release and the one CI installs. Applying one gate's fix would turn it into the other gate's failure. Both were installed and run locally before writing that down, because a supposed conflict between gates is not a conflict between gates.
- ``galaxy.yml`` no longer claims the documentation site is unpublished. It has been online for months, and the comment stayed. The field keeps pointing at the repository tree **at the tag**, and now says why: the site publishes the state of ``main`` only, and Galaxy shows that link next to a version number, so a reader of an old release would land on today's documentation. The site is announced from the README instead, where no version frames it.
- ``instance_server`` rewrote ``public_ips`` and ``private_nics`` on **every** run, reporting ``changed`` each time. The request takes a list of IDs and the API returns the full objects, so the comparison found them different at every execution: a playbook using either field was never idempotent, whatever ``changed`` displayed. This is the plural form of the ``lb_frontend.backend_id`` defect, which the runtime handled only in the singular. Reproduced offline before being fixed, and the reproduction is kept as a test.
- ``lb_frontend`` rewrote ``certificate_ids`` on every run. Measured against the real account on 8 September 2026 through a recording proxy: the write answers in the order asked, and the **read reverses it**, stably, two hundred exchanges apart. Comparing in order therefore found a difference at every execution, and the module was never idempotent whatever ``changed`` displayed. The override sets ``set``, which keeps multiplicities: a certificate listed twice stays distinct from one listed once.
- ``version_added`` now says the version in which a module, option or return value **appeared**, instead of the version the generator happened to run in. Every module published up to 0.4.0 announced the release it shipped with, so a module present since 0.1.0 claimed to need 0.4.0. The dates are read from a journal versioned alongside the generator, reconstructed from the published tags; a name is dated once and never redated, and the loader refuses a journal that contradicts itself. See ADR-013.

v0.4.0
======

Release Summary
---------------

This release is about what the modules claim, rather than about how many
there are.

A managing module used to compare with strict equality, announce ``changed``
without looking at what it had just read back, and silently drop a
``description: null`` a playbook had explicitly asked for. Each of those
reports success on a state that was never reached. All three are fixed, and
each fix is measured rather than asserted: comparison strategies come from
the contract type or from an override carrying its reason, postconditions are
verified with the same comparison as the outbound decision, and an explicit
``null`` now fails the module instead of disappearing.

The generator also stopped losing what the contract says. ``x-one-of`` becomes
a real ``mutually_exclusive`` constraint, which fixes a shipped module that
accepted two options the API rejects together; clearable fields are carried by
the IR and counted; and constraint keywords the contract does not declare are
measured absent rather than assumed so.

Adding a product is no longer a matter of the tests passing. ``mise run
admission`` gives it a verdict, and publishes the price it enters with.

Minor Changes
-------------

- A parameter can be excluded from that verification through an override carrying its reason, for an API that applies a field asynchronously. None is excluded today.
- An execution environment image is published with every version, at ``ghcr.io/stephrobert/collection-scaleway/ee``. It carries the collection and the Scaleway SDK, so a playbook run in AWX, ``ansible-navigator`` or a CI runner no longer needs one built by hand. There is no ``latest`` tag, on purpose - a moving reference makes it impossible to say afterwards what was run - and the image is signed without a key and carries a build provenance attestation, verified the same way as the archive.
- Managing modules no longer compare with strict equality alone. Each managed parameter now carries a comparison strategy: the contract type decides what it can (``scalar``, ``ordered_list`` for an array, ``mapping`` for an object), and an override decides the rest with its reason (``set``, ``normalized_string``, ``object_id``, ``normalized_object``). A field the API reorders or normalises no longer reports ``changed`` on every run.
- Managing modules now verify what the write produced. After the second read, every field the playbook asked for is compared with what the API returns, using the same comparison strategy as the outbound decision. A divergence fails the module with ``failed_postconditions`` naming the field, the requested value and the observed one, and ``changed`` stays true because the resource did move.
- Options for clearable fields of managing modules are now published as ``type: raw`` with the marker ``__unchanged__`` as their default: it is the only public mechanism by which Ansible lets a module tell an explicit ``null`` from an omitted option, measured on every ``ansible-core`` the collection supports. The option description states the API type, and the runtime re-validates provided values against it, so a playbook sees no difference in conversions or error messages.
- The generation summary publishes how many managed parameters fall under each comparison strategy, so the ``ordered_list`` fallback stays visible.
- The generator now audits which writable fields the contract declares as clearable. ``mise run nullabilite`` names them, and the count is published in a derived block of the runtime architecture page: a playbook cannot currently clear such a field, because ``field: null`` and an absent ``field`` produce the same request. The number sizes that work rather than describing it.
- The generator now carries the constraints the contract declares. ``x-one-of`` becomes ``mutually_exclusive``; a clearable field (``oneOf: [X, null]`` or ``type: [X, "null"]``) is recorded and counted. Constraint keywords the contract does not carry are measured rather than assumed, and the coverage report publishes all three numbers.
- The parser is fuzzed by ClusterFuzzLite on every pull request and for ten minutes every Tuesday, and a smoke harness replays it offline in ``mise run check``. One proves the harness finds; the other proves it works.
- The published archive is now signed without a key and carries a build provenance attestation, both bound to the identity of the workflow that produced it rather than to a secret. ``SECURITY.md`` publishes the two commands that verify them, and the release workflow runs the first one on the archive before publishing it.
- ``SECURITY.md`` now carries the direct link to the private advisory form. It described the path in prose and held no link at all, which is also what OpenSSF Scorecard reads: the check scored 4 out of 10.
- ``mise run admission`` gives a product a verdict before it enters the index: OpenAPI syntactic coverage, semantic constraints, clearable fields, Day-2 classification, write completeness, comparison strategies and documentary coverage. It runs in ``mise run check`` over every indexed product, so adding a refused one turns the gate red. Not every stage blocks; the others publish the number that is the price of admission.

Bugfixes
--------

- A restated field description kept the abbreviation in lowercase. ``ips_count`` read ``Count of ips.`` on a page whose short description already said ``Instance IPs``: the acronym table was applied to the schema name and not to the field name.
- Managing modules no longer ignore an explicit ``null`` on a field the contract declares clearable. ``description: null`` used to produce the same request as an omitted ``description``, and the module reported ``ok`` with the description still there. The module now fails before reading anything, names the field, and says to omit the option to leave the value unchanged. Clearing a field is still not supported.
- The ``diff`` of a management module read its two sides differently. The ``before`` went through the projection that reconciles a written ``backend_id`` with a read ``backend: {id: ...}``; the ``after`` read the key directly and found nothing. On ``lb_frontend`` a user saw ``after: {backend_id: null}`` while the API had returned ``backend.id``. The module worked and the diff lied, which is worse than a module that fails.
- The archive check no longer assumes how many plugins the collection ships. It discovered exactly one inventory plugin and refused any other count; it now interrogates every plugin of every known type, and refuses a ``plugins/`` directory it does not know how to handle rather than silently skipping it.
- The parser now refuses a malformed contract instead of crashing on it. A fuzzer found twelve real defects on its first pass, all of the same family: a shape assumed without being checked. What made them expensive was where they surfaced - a non-textual ``operationId`` travelled through the whole parse and came out at the final sort, on a ``TypeError`` naming neither the operation nor the file.
- The published archive is now checked against every module it carries. The check interrogated a single "representative" module, so a module the installed collection could not document passed unnoticed among the other forty-nine.
- lb_subscriber - the module accepted ``email_config`` and ``webhook_config`` together, which the API rejects with a 400. The contract marks them with a shared ``x-one-of`` group, and the module now declares them mutually exclusive, so the error arrives from Ansible before any request is sent.

v0.3.0
======

Release Summary
---------------

Every field a module returns now carries a description. 0.2.0 published one
hundred ``Not documented by the Scaleway API contract.`` lines inside its
``RETURN`` blocks, on nine modules: the generator had just gained the right to
publish the fields of a resource, and the documentation gate still only looked
at top-level keys.

The gate now counts them, and it runs on every pull request rather than only
at release time, which is where it was and where refusing costs a version
number rather than a round trip.

Minor Changes
-------------

- A returned field with no description in the contract is now filled by one of three mechanisms before the gate refuses it: a human decision carrying its reason, what the same contract says of that field name when it says it exactly once, or a restatement that says nothing more than the field name. ``volumes_count`` reads ``Count of volumes.`` and not ``Number of volumes in the selected zone``, which the contract nowhere supports.
- The compatibility table, the versioning examples and the module count in the READMEs are derived from ``galaxy.yml`` and the CI matrix. They were hand-written, and 0.2.0 shipped announcing the 0.1.x series.

Bugfixes
--------

- 0.2.0 published one hundred ``Not documented by the Scaleway API contract.`` lines inside its ``RETURN`` blocks. The generator had just gained the right to publish the fields of a resource, and the documentation gate still only looked at top-level keys: the published surface had grown, the measurement had not. Every published field now carries a description, and the gate counts them.
- A returned field the contract declares deprecated now says so. The notice existed for options and was lost for return values, so a reader could build on ``default_bootscript`` with nothing saying it was deprecated.
- Resource names no longer appear in lowercase where they are acronyms. ``Manage a Scaleway Instance ip`` reads ``Manage a Scaleway Instance IP``, and the same for ACL and NIC.

v0.2.0
======

Release Summary
---------------

Every published page now explains its module on its own. All 297 options and
all 62 returned keys carry a description, every example can be copied as is,
and 53 of the 57 composite return keys list the fields of the resource they
return, each with the description the contract gives it.

None of this is a documentation pass over the produced files: the fixes are in
the generator, so the next product inherits them. A quality gate now refuses a
release that would publish a page unable to explain itself, and a page on
Galaxy is published for good.

Minor Changes
-------------

- Documentation links published next to a version now point at that version's tag rather than at ``main``. A reader of an older release used to land on today's files, with nothing on the page saying so.
- Examples now show what an operator actually looks for. An information module shows how to filter a list, not only how to read one resource and how to list them all; a management module shows check mode with ``--diff``, which its own preamble had always described without ever showing.
- Module documentation no longer inherits the gaps of the API contract. Every option and every returned key of the 50 published modules now carries a description, and every example is copyable as is.
- Modules now name the product the way Scaleway publishes it. ``Manage a Scaleway Lb backend`` used the index slug; the short descriptions read ``Manage a Scaleway Load Balancer backend``, and the product is no longer repeated when the resource already carries its name.
- Overrides gained a documentation layer. A ``description`` fills a gap the contract leaves, an ``example`` supplies a value the contract cannot give, and both require a ``reason``. The contract always wins over an override, and an override that no longer fills anything is reported as orphaned.
- The inventory plugin now ships four complete inventory files as examples, each one meant to be copied whole. Three of the four used to be commented out line by line, so none of them could be used without editing.
- ``RETURN`` blocks now list the fields of the resource they return. A page said ``server: {type: dict}`` and nothing more; it now names the 36 fields the contract declares on an Instance, each with its description and type. 53 of the 57 composite return keys carry them; the four others return a payload for which the contract declares no schema, and the quality report names them.

Bugfixes
--------

- An example with no summary in the contract was named after the SDK operation, ``Run GetDashboard``. It now says what the task does.
- Enum examples no longer show the ``unknown_*`` protobuf sentinel that opens most Scaleway enumerations, which the API rejects.
- Examples of the management modules published ``<zone>``, ``<name>`` and ``<backend_id>`` rather than values. They now use the zone the contract declares, a UUID, and the enum values an operator would really write.
- Loading an override file now refuses a key declared twice. YAML silently keeps the last one, which had erased a ``resource`` decision and renamed a published module without any check turning red.
- The description of four Load Balancer management modules carried the contract sentence ``Note that the request type is PUT and not PATCH. You must set all parameters.`` That is true of the API and false of the module, which reads the resource before writing and fills in what you leave out.
- Two example tasks sharing a value made ``safe_dump`` emit a YAML anchor, ``tags: &id001`` then ``tags: *id001``. Valid YAML that cannot be copied task by task, and whose second task no longer says what it sends.
- ``instance_server_action``: the ``RETURN`` block described the seven actions of the contract on a module whose ``argument_spec`` accepts four. ``terminate``, ``backup`` and ``enable_routed_ip`` are no longer documented as available.

v0.1.0
======

Release Summary
---------------

First version of the collection, produced by this repository's generator from the OpenAPI documents Scaleway publishes.

The complete chain, from contract to playbook, is proven before being widened: the generator, the shared runtime and the drift mechanisms come first, and the modules follow from them.

Major Changes
-------------

- New module ``instance_server_info``, which serves ``GetServer`` and ``ListServers`` behind a single interface. A supplied identifier reads one Instance, an absent one lists the whole zone, every page walked.
- Shared runtime in ``plugins/module_utils/scaleway.py``: one way to build the client, centralised error handling that never copies a secret, complete pagination and check mode.
- ``scaleway`` documentation fragment for the common parameters, which a module therefore never redeclares.

Minor Changes
-------------

- Discovery failures are classified: credentials refused (fatal), missing permission on a product (named error), product absent from a zone (warning). ``strict: true`` turns any error into a refusal.
- Group names are sanitised properly: ``production/web`` becomes ``production_web`` and ``2024`` becomes ``_2024``, where Ansible would make ``_024``.
- Hostname collisions no longer lose a machine: a name already taken receives the zone as a suffix, then the identifier, deterministically, and every disambiguation is reported.
- New ``waitable`` documentation fragment for ``wait`` and ``wait_timeout``, with the values used by the official collection.
- New guide ``docs/guides/dynamic-inventory.md``, which documents a measured trap along the way: ``ansible-inventory`` downgrades an inventory plugin's failure to a warning and exits 0, unless ``ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED`` is asked for.
- New inventory plugin ``stephrobert.scaleway.compute``. It discovers machines product by product, then links them to their private networks and their VPCs by listing IPAM **once per region** instead of once per network card, and it keeps the network relation rather than a single private address with no network attached.
- New module ``instance_server_action``, which triggers an action on an Instance: ``poweron``, ``poweroff``, ``reboot`` and ``stop_in_place``. In check mode it announces the change without triggering anything, and it waits until the Instance has actually reached the target state before returning.
- New shipped playbook ``arreter_un_serveur``, which stops a named Instance and reads its state back rather than taking the module's word for it.
- The IPAM and VPC index is no longer built when no requested product carries private network cards. An inventory with ``products: [apple_silicon]`` used to issue twelve API calls it made nothing of. The capability is declared by each provider, not guessed by the core.
- The action module does **not** expose ``terminate``, ``backup`` or ``enable_routed_ip``, which the contract nevertheless puts in the same enum. The first deletes the Instance and its local volumes, the second creates an image, the third migrates the network stack with no way back: none of them operates an existing resource. Every exclusion is written with its reason in the generator's overrides.
- The cache key covers everything that changes the result, including the profile, the API URL, the filters and the address policy. Two different configurations no longer share an inventory.
- The collection composes its own HTTP requests and no longer calls ``API._request``, a private method of the SDK. Carrying the ``x-total-count`` header into the body's ``total_count`` field, on which the pagination guard depends, was that method's quietest behaviour: it is now explicit and tested.
- The example now exercises **all four** actions of the power module against the real cloud, not two: ``poweroff``, ``poweron``, ``reboot`` and ``stop_in_place``, each confirmed by the state the API returns. ``reboot`` and ``stop_in_place`` were exercised nowhere, while two closed defects bore precisely on them.
- The generator refuses a wait override that promises a state absent from the contract. The enum is derived without guessing, from the resource schema and the field name, and a typo can no longer produce a module that waits for a state the API will never reach.
- The inventory discovers ``instance``, ``elastic_metal`` and ``apple_silicon`` behind one normalised model. An unknown product in ``products`` is refused, not ignored.
- The zoned Load Balancer joins the collection: twenty-one modules, from ``lb_load_balancer_info`` to ``lb_backend_stat_info``, produced by the same generator and through the same mechanism as those of Instance.
- Two example playbooks in ``playbooks/``, played on every run of the integration target rather than written once.
- ``SCW_API_URL`` is honoured end to end, which makes it possible to exercise a playbook against a local emulator, with no credentials and no spend.
- ``ansible_host`` is chosen by order of address families, or by a named private network when a machine has several. The reason for the choice is exposed in ``scaleway_address_source``.
- ``compose``, ``groups`` and ``keyed_groups`` are actually applied, and not merely inherited from the ``constructed`` documentation fragment.
- ``instance_server_info`` now accepts ``tags`` as a **list**, and the runtime joins it with commas on the way out. The contract declares this filter as a ``string`` while describing its shape in its own description, "to filter with several tags, use commas to separate them": the override reads that sentence, it guesses nothing.

Bugfixes
--------

- A missing permission on IPAM or VPC failed the whole inventory in strict mode, including when every machine had a perfectly reachable public address. It is now a warning: it is an enrichment that does not happen, not a discovery that fails.
- A misspelled zone was discarded in silence: zero zones queried, zero calls, zero warnings, and an empty inventory with code 0. An unknown zone is now refused, as products, group axes and address families already were.
- A network failure now produces a named error instead of a Python traceback. Exceptions from ``requests`` were left as they were, and Ansible displayed ``MODULE FAILURE``: the user could not tell whether their playbook was at fault or the network was.
- API calls are now bounded in time. The Scaleway SDK issues its requests **with no timeout at all**: a silent connection froze a playbook indefinitely. An ``api_timeout`` parameter bounds every call, at 60 seconds by default.
- An API announcing a ``total_count`` it does not honour now produces a named error. Returning the partial list in silence would be exactly what this function exists to prevent.
- An action module whose wait failed reported ``changed=false`` even though the API had accepted the action and the resource had changed. A replayed playbook believed it had done nothing. The result now carries ``changed=true`` from acceptance onward, whatever the outcome of the wait.
- An authentication refusal was never fatal. Scaleway returns ``{"message": "denied authentication"}`` on a 401, and the classification rule looked for the word ``denied`` to identify a missing permission: no revoked token therefore raised ``AuthenticationFailed``, and the inventory came out **empty with a return code of 0**. The rule now looks for ``permission``, and the nuance on permission 401s survives.
- An unknown hostname source was accepted, and every machine was then discarded for lack of a name. A source naming a non-textual field, ``private_networks``, returned an object where the type promises a string.
- Load Balancer lists are now paginated. Scaleway uses two spellings for page size depending on the product, ``per_page`` on Instance and ``page_size`` on the Load Balancer, and the rule knew only one: eleven operations were not declared as paginated, their pagination parameters became module options, and a list would have returned its **first page in silence**.
- Pagination no longer truncates a list when the API caps the page size. The condition "the page is shorter than requested" was tested **before** ``total_count``, while the information needed to continue was in the same response: facing an API that caps ``per_page`` at 50 for 100 requested while announcing 120 items, the function returned 50 items, requested only one page, and reported nothing. That is the defect its own documentation named as the worst of the three, an incomplete list presenting itself as complete. Instance caps at 100, so the case was latent; this runtime is shared by every product to come.
- The inventory plugin's ``organizations`` option filtered nothing. It was read, carried by the discovery context and counted in the cache key, but no provider passed it on and no local filtering applied it: the inventory was silently wider than requested. It is now passed to the API when a single organisation is requested, and **always** applied locally.
- The secret key could appear in clear text in the failure message. The SDK's validation raises ``Invalid secret key format 'SCW...'``, value included, and Ansible only censors values that came from module parameters, not those read from the configuration file: the key landed in the playbook log and in CI artefacts. The message now names the rejected field, never its value.
- Two accounts could share a cached inventory. With no ``profile`` declared, two different access keys produced the same fingerprint, and the second run received the first one's fleet. Only the key's fingerprint enters the cache key, never its value.
- Writing ``tags: [example]`` returned no machine at all, without raising any error. Ansible converted the list into the string ``"['example']"``, the API found nothing, and a playbook read zero machines from a fleet of five. Measured by capturing the request that was sent. Both forms now work, the list as well as the comma-separated string already in use.
- ``api_url`` and ``api_allow_insecure`` carried a default value in the ``argument_spec``. Since a default value is never absent, they **always** overrode what the Scaleway configuration file declared: a user whose profile points at an emulator saw their playbook go to production, with real credentials and real resources. The default is now applied after the profile is read, and the announced order, parameter then environment then file, is honoured.
- ``include_raw`` was entirely inert. The option was documented, counted in the cache key and tested on the provider side, but the raw response did not enter the serialisation **every** run goes through: ``scaleway_raw`` never appeared.
- ``instance_server_action`` returned immediately on ``reboot``, having observed nothing: the target state is the starting state, so the first read satisfied the wait in zero seconds and the next task ran during the reboot. The module now requires observing a transition, and says so when it sees none.
- ``instance_server_action`` waited for the ``stopped`` state after ``stop_in_place``, while the contract declares ``stopped in place``, a **distinct** state. The action therefore failed after ``wait_timeout`` on an Instance that was properly stopped. It has been played against the emulator since, which is the only check that could have caught it: the defect was in the value, not in the shape.
- ``strict`` did not enter the cache key. A partial inventory recorded with ``strict: false`` was therefore served as is to a run asking for ``strict: true``, and since discovery was not replayed, the errors already present no longer caused a failure.
- ``tags_match: any``, which is the default, lost machines. The Instance API applies an **AND** on ``tags`` and not an OR, measured on three concordant sources: asking for two tags returned only the machines carrying both, and local filtering cannot recover what was never downloaded. With several tags in ``any`` mode, the filter is no longer delegated to the API.

New Modules
-----------

- stephrobert.scaleway.instance_server_info - Gather information about Scaleway Instance servers.
