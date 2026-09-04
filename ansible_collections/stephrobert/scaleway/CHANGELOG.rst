==================================
stephrobert.scaleway Release Notes
==================================

.. contents:: Topics

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
