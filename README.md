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

```text
instance v1 : 74 opérations découvertes
  INFO 27 · ACTION 3 · MANAGE 11 · WORKFLOW 1 · LIFECYCLE 19 · IGNORE 13 · UNKNOWN 0
  Day-2 42 · AUTO 41 · MANUAL 1 · couverture 97,6 %

collection local.scaleway : 2 modules produits sur 2 demandés
  instance_server_info    lire une Instance, ou lister une zone entière
  instance_server_action  allumer, arrêter, redémarrer, figer
  scaleway (inventaire)   instance, elastic_metal, apple_silicon
  ansible-test sanity : 24 tests, 0 échec
  playbook contre feint : 104 serveurs listés, 1 arrêté puis relu
  inventaire contre feint : 104 machines, 6 groupes natifs, joué par un playbook
  366 tests unitaires · 46 mutations prouvées par /falsify
  CI : quatre jobs, générateur · collection · archive · intégration
```

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
└── ansible_collections/local/scaleway/    le livrable, et rien d'autre
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
| runtime | `ansible_collections/local/scaleway/plugins/module_utils/` | client, erreurs, pagination, check mode |

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
* [Les playbooks livrés](ansible_collections/local/scaleway/playbooks/README.md), joués à chaque `mise run integration`

## Licence

GPL-3.0-or-later, comme la collection Scaleway officielle.
