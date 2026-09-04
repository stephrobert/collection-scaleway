# collection-scaleway

Générateur de modules Ansible **Day-2** pour les APIs Scaleway, et la
collection qu'il produit.

La responsabilité est partagée, et cette frontière décide de tout le reste :

> Terraform provisionne les ressources. Ansible exploite les ressources
> existantes.

Le générateur ne produit donc ni `create` ni `delete` : il produit des modules
d'information, d'action ponctuelle et de gestion d'état Day-2.

## État

Étape 3 terminée côté modules, étape 5 terminée côté inventaire. La chaîne va
du contrat au module, le module tourne, et la collection emporte un plugin
d'inventaire dynamique qui découvre trois produits derrière un même modèle.

<!-- compteurs:début, produits par scripts/readme_counters.py -->
```text
instance v1 : 74 opérations découvertes
  INFO 27 · ACTION 3 · MANAGE 10 · WORKFLOW 1 · LIFECYCLE 19 · IGNORE 14 · UNKNOWN 0
  Day-2 41 · AUTO 40 · MANUAL 1 · classées pour génération automatique 97,6 % (40/41)

collection stephrobert.scaleway : 46 modules produits sur 52 au plan
  instance_dashboard_info                Gather information about Scaleway Instance dashboards
  instance_image                         Manage a Scaleway Instance image
  instance_image_info                    Gather information about Scaleway Instance images
  instance_ip                            Manage a Scaleway Instance ip
  instance_ip_info                       Gather information about Scaleway Instance ips
  instance_placement_group               Manage a Scaleway Instance placement group
  instance_placement_group_info          Gather information about Scaleway Instance placement groups
  instance_placement_group_server_info   Gather information about Scaleway Instance placement group servers
  instance_security_group                Manage a Scaleway Instance security group
  instance_security_group_info           Gather information about Scaleway Instance security groups
  instance_security_group_rule           Manage a Scaleway Instance security group rule
  instance_server                        Manage a Scaleway Instance server
  instance_server_action                 Perform an action on a Scaleway Instance server
  instance_server_compatible_type_info   Gather information about Scaleway Instance server compatible types
  instance_server_info                   Gather information about Scaleway Instance servers
  instance_server_private_nic            Manage a Scaleway Instance server private nic
  instance_server_private_nic_info       Gather information about Scaleway Instance server private nics
  instance_server_type_availability_info Gather information about Scaleway Instance server type availabilities
  instance_server_type_info              Gather information about Scaleway Instance server types
  instance_server_user_data_info         Gather information about Scaleway Instance server user data
  instance_snapshot                      Manage a Scaleway Instance snapshot
  instance_snapshot_info                 Gather information about Scaleway Instance snapshots
  instance_volume                        Manage a Scaleway Instance volume
  instance_volume_info                   Gather information about Scaleway Instance volumes
  instance_volume_type_info              Gather information about Scaleway Instance volume types
  lb_acl                                 Manage a Scaleway Lb acl
  lb_acl_info                            Gather information about Scaleway Load Balancer acls
  lb_backend                             Manage a Scaleway Lb backend
  lb_backend_info                        Gather information about Scaleway Load Balancer backends
  lb_backend_stat_info                   Gather information about Scaleway Load Balancer backend stats
  lb_certificate                         Manage a Scaleway Lb certificate
  lb_certificate_info                    Gather information about Scaleway Load Balancer certificates
  lb_frontend                            Manage a Scaleway Lb frontend
  lb_frontend_acl_info                   Gather information about Scaleway Load Balancer frontend acls
  lb_frontend_info                       Gather information about Scaleway Load Balancer frontends
  lb_ip                                  Manage a Scaleway Lb ip
  lb_ip_info                             Gather information about Scaleway Load Balancer ips
  lb_load_balancer                       Manage a Scaleway Lb load balancer
  lb_load_balancer_info                  Gather information about Scaleway Load Balancer load balancers
  lb_load_balancer_private_network_info  Gather information about Scaleway Load Balancer load balancer private networks
  lb_load_balancer_stat_info             Gather information about Scaleway Load Balancer load balancer stats
  lb_load_balancer_type_info             Gather information about Scaleway Load Balancer load balancer types
  lb_route                               Manage a Scaleway Lb route
  lb_route_info                          Gather information about Scaleway Load Balancer routes
  lb_subscriber                          Manage a Scaleway Lb subscriber
  lb_subscriber_info                     Gather information about Scaleway Load Balancer subscribers
  scaleway (inventaire)                  instance, elastic_metal, apple_silicon
  477 tests unitaires · 100 mutations prouvées par /falsify
  CI : cinq jobs, Générateur · collection · Archive · Intégration · Plateforme d'exemple
  ansible-test sanity, playbooks et inventaire contre l'émulateur :
  comptes rendus par `mise run sanity` et `mise run integration`
```
<!-- compteurs:fin -->

**Ce que l'inventaire a coûté au cœur.** Ajouter Elastic Metal et Apple Silicon
après Instance a demandé douze lignes dans le registre de `discovery.py`, et
aucune dans le modèle normalisé, la sélection d'adresse, les groupes, le nom
d'hôte, la jointure réseau ni le plugin. C'est la mesure de l'étape 5, et un
test la tient : aucune couche du cœur ne nomme un produit dans son code.

Elastic Metal et Apple Silicon sont prouvés par des réponses simulées :
l'émulateur ne sert ni l'un ni l'autre, et ne le fera pas à court terme
(feint#631, feint#632). Instance est prouvé de bout en bout.

Deux modules sont produits, et c'est délibéré : le périmètre est déclaré dans
`mise.toml` (`MODULES`), pas deviné. Les 29 autres modules du plan sont écartés
**avec leur raison**, que `mise run generate` affiche.

Le module d'action n'expose que quatre des sept valeurs du contrat. Les trois
autres sont nommées dans le rapport de génération : `terminate` supprime
l'Instance et ses volumes, `backup` crée une image, `enable_routed_ip` migre la
pile réseau sans retour. Le contrat les range dans le même enum ; les recopier
aurait fait entrer le cycle de vie par la porte d'une action.

## Démarrer

```bash
mise run setup                 # environnement de développement
mise run report                # rapport de couverture d'Instance
mise run generate              # écrire les modules dans plugins/modules
mise run check                 # ce qu'une pull request doit passer
mise run sanity                # ce qu'Ansible dit du fichier produit
mise run docs                  # juge la doc avec antsibull-docs, puis produit les pages
mise run package               # construit l'archive, l'installe et l'interroge
mise run integration           # les playbooks, dont les exemples, contre un émulateur
mise run security              # actionlint, zizmor et poutine sur les workflows
mise run security:trust        # plumber, la politique de confiance du pipeline
mise run lock                  # recalculer le verrou des dépendances
```

```bash
python -m generator inspect instance     # ce que le contrat déclare
python -m generator classify instance    # la décision, opération par opération
python -m generator report instance --strict
python -m generator generate instance --module instance_server_info
```

## Deux produits, deux emplacements

```text
.                                     le producteur
├── generator/                        lit le contrat, décide, écrit le module
├── scripts/                          les lanceurs de contrôles
├── specs/scaleway/                   les contrats versionnés
└── ansible_collections/stephrobert/scaleway/    le livrable, et rien d'autre
```

La collection est rangée à l'emplacement qu'Ansible exige. Ce n'est pas du
rangement : `ansible-test`, `antsibull-docs` et `ansible-playbook` travaillent
**en place**, sans copie assemblée ailleurs. Le premier découpage mettait la
collection à la racine, et la copie qu'il fallait alors fabriquer a produit un
`ansible-test sanity` vert sur **zéro fichier examiné**.

## Comment ça marche

| étape | code | ce qu'elle produit |
|---|---|---|
| source | `generator/source/` | le contrat OpenAPI versionné dans `specs/` |
| parser | `generator/parser/` | l'IR canonique, sans Ansible ni SDK |
| classifieur | `generator/classifier/` | INFO, ACTION, MANAGE, WORKFLOW, LIFECYCLE, IGNORE, UNKNOWN |
| overrides | `generator/overrides/` | les décisions humaines, avec leur raison |
| rapport | `generator/report/` | texte, JSON et Markdown |
| modèle | `generator/ansible/models.py` | la source unique de l'`argument_spec` et de la doc |
| renderer | `generator/renderer/`, `generator/templates/` | les fichiers de `plugins/modules/` |
| runtime | `ansible_collections/stephrobert/scaleway/plugins/module_utils/` | client, erreurs, pagination, check mode |

La source de vérité est le document OpenAPI 3.1 publié par produit sur le
portail developers de Scaleway. Ce qu'il porte, ce qu'il ne porte pas et
comment le dépôt s'aperçoit qu'il a bougé sont documentés dans
[docs/architecture/contrats-scaleway.md](docs/architecture/contrats-scaleway.md).

## Quatre règles qui priment sur le reste

1. **Aucune opération ne disparaît.** Ce qu'aucune règle ne tranche est
   `UNKNOWN`, et `report --strict` sort en code 2.
2. **La métrique ne se maquille pas.** La couverture rapporte `AUTO + OVERRIDE`
   aux seules opérations Day-2 ; LIFECYCLE et IGNORE sont comptés à part, pas
   effacés.
3. **La génération est déterministe.** Même contrat, même sortie, octet pour
   octet. Deux golden le tiennent : `tests/fixtures/instance/expected_ir.json`
   pour ce que le parser lit, `tests/fixtures/widget/expected_modules/` pour ce
   que le renderer écrit.
4. **Un vert qui n'a rien mesuré est refusé.** `ansible-test` saute toutes ses
   cibles et sort en 0 quand git ne lui liste rien ; `mise run sanity` refuse cette
   sortie-là. 17 gardes du dépôt sont prouvées en les neutralisant
   (`mise run falsify`).

## La qualité du livrable

La collection suit la [liste de contrôle d'inclusion](https://github.com/ansible-collections/ansible-inclusion/blob/main/collection_checklist.md)
de la communauté Ansible, et chaque point est tenu par une commande plutôt que
par une intention :

| exigence | ce qui la tient |
|---|---|
| licence livrée avec la collection | `LICENSE`, et `mise run package` refuse une archive qui l'oublie |
| version minimale d'ansible-core **mesurée** | matrice de CI sur 2.17 à 2.20 ; 2.16 échoue, la borne le dit |
| changelog, de préférence `changelogs/changelog.yaml` | fragments et `antsibull-changelog`, jugés par `mise run check` |
| documentation aux standards | `ansible-test sanity` **et** `antsibull-docs`, qui voit ce que le premier laisse passer |
| CI sur chaque pull request et régulièrement | quatre jobs, plus un déclenchement hebdomadaire |
| pas de fichier inutile dans le dépôt | `mise run check:worktree` échoue si un build laisse un fichier non ignoré |
| dépendances déclarées pour un environnement d'exécution | `meta/execution-environment.yml` et `meta/ee-requirements.txt` |
| chaîne d'approvisionnement tenue | actions épinglées par SHA, dépendances verrouillées avec empreintes, quatre scanners de workflow en porte |

L'archive n'est pas seulement construite : `mise run package` contrôle son contenu,
l'installe dans un répertoire jetable, puis demande sa documentation à
`ansible-doc` et fait résoudre chaque playbook par `ansible-playbook`. Un
fichier présent dans une archive n'est pas un module qu'Ansible sait charger.

## Documentation

* [Architecture du générateur](docs/architecture/generateur.md)
* [Les contrats Scaleway](docs/architecture/contrats-scaleway.md) : la source, ses limites, sa surveillance
* [Le runtime de la collection](docs/architecture/runtime.md)
* [L'inventaire dynamique](docs/guides/inventaire-dynamique.md), et le piège d'Ansible sur le mode strict
* [Ce que dit OpenSSF Scorecard, et ce qu'il ne dit pas](docs/scorecard.md)
* [SECURITY.md](SECURITY.md) : comment signaler une faille, et ce que le dépôt tient déjà
* [Les playbooks livrés](ansible_collections/stephrobert/scaleway/playbooks/README.md), joués à chaque `mise run integration`

## Licence

GPL-3.0-or-later, comme la collection Scaleway officielle.
