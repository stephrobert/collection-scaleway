==================================
stephrobert.scaleway Release Notes
==================================

.. contents:: Topics

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
