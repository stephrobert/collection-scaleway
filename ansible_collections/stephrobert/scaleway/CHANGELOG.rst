============================
stephrobert.scaleway Release Notes
============================

.. contents:: Topics

v0.1.0
======

Release Summary
---------------

Première version de la collection, produite par le générateur du dépôt à
partir des documents OpenAPI publiés par Scaleway.

Un seul module est livré, et c'est délibéré : la chaîne complète, du contrat
au playbook, est prouvée sur lui avant d'être élargie.

Major Changes
-------------

- Fragment de documentation ``scaleway`` pour les paramètres communs, qui ne sont donc jamais redéclarés par un module.
- Nouveau module ``instance_server_info``, qui sert ``GetServer`` et ``ListServers`` derrière une seule interface. L'identifiant fourni lit une Instance, absent liste la zone entière, toutes pages parcourues.
- Runtime commun dans ``plugins/module_utils/scaleway.py`` : une seule construction de client, gestion d'erreur centralisée sans jamais recopier de secret, pagination complète et check mode.

Minor Changes
-------------

- Deux playbooks d'exemple dans ``playbooks/``, joués à chaque exécution de la cible d'intégration plutôt qu'écrits une fois.
- ``SCW_API_URL`` est honoré de bout en bout, ce qui permet d'exercer un playbook contre un émulateur local, sans identifiants et sans dépense.

New Modules
-----------

- stephrobert.scaleway.instance_server_info - Gather information about Scaleway Instance servers.
