# L'inventaire dynamique Scaleway

`local.scaleway.scaleway` construit un inventaire Ansible à partir d'un compte
Scaleway. Il découvre les machines produit par produit, puis les relie à leurs
réseaux privés et à leurs VPC.

Tout ce que ce document affirme est mesuré : les tests unitaires vivent dans
[tests/unit/inventory/](https://github.com/stephrobert/collection-scaleway/blob/main/tests/unit/inventory/), et le scénario joué à
chaque `mise run integration` est
[tests/integration/feint/inventaire.scaleway.yml](https://github.com/stephrobert/collection-scaleway/blob/main/tests/integration/feint/inventaire.scaleway.yml).

## Le fichier de configuration

Ansible reconnaît un plugin d'inventaire au **nom du fichier**. Celui-ci doit
se terminer par `scaleway.yml` ou `scw.yml`, sinon il est ignoré en silence :

```bash
ansible-inventory -i production.scaleway.yml --graph
```

Le minimum tient en une ligne, et le profil Scaleway habituel décide du reste :

```yaml
plugin: local.scaleway.scaleway
```

## Identifiants

Les identifiants se lisent dans l'environnement, dans le fichier de
configuration Scaleway, ou dans le fichier d'inventaire, dans cet ordre :

```bash
export SCW_ACCESS_KEY=... SCW_SECRET_KEY=...
```

`SCW_API_URL` est honorée : la pointer vers un émulateur local construit un
inventaire sans compte et sans dépense. C'est ainsi que ce plugin est
réellement testé.

## Produits

Trois produits d'hébergement sont découverts :

| `products` | ce qui est listé |
|---|---|
| `instance` | les Instances |
| `elastic_metal` | les serveurs Elastic Metal |
| `apple_silicon` | les machines Apple Silicon |

`all`, la valeur par défaut, désigne **ces trois-là**, et non toutes les APIs
Scaleway existantes. Un nom inconnu est refusé plutôt qu'ignoré : un produit
mal orthographié produirait un inventaire silencieusement partiel.

```yaml
plugin: local.scaleway.scaleway
products:
  - instance
  - elastic_metal
```

## Zones et régions

Sans `zones`, chaque produit interroge les dix zones qu'il déclare. Une zone
où le produit n'existe pas se retire d'elle-même, parce que l'API le dit.

`regions` ne sert qu'à l'index réseau : il se déduit des zones, et n'a besoin
d'être écrit que pour l'élargir.

```yaml
zones:
  - fr-par-1
  - fr-par-2
```

## Le nom des machines

`hostnames` donne les sources de `inventory_hostname`, dans l'ordre :

```yaml
hostnames:
  - tag:role      # lit un tag « role=web »
  - name
  - id
```

Sont acceptés `name`, `id`, `public_ipv4`, `public_ipv6`, `private_ipv4`,
`private_ipv6` et `tag:CLE`. Les noms `hostname`, `vpc_ipv4` et `vpc_ipv6`
employés par la collection officielle restent compris, pour qu'une
configuration existante continue de fonctionner.

**Les collisions ne perdent pas de machine.** Un nom Scaleway n'est unique ni
dans une zone, ni dans un projet : deux machines peuvent s'appeler `web01`. La
seconde reçoit alors `web01_fr-par-1`, et la troisième `web01_<identifiant>`.
Chaque désambiguïsation est signalée par un avertissement, et le résultat est
le même d'une exécution à l'autre.

## Par où Ansible joint la machine

`ansible_host` est choisi dans l'ordre des familles demandées :

```yaml
address_priority:
  - private_ipv4
  - public_ipv4
  - private_ipv6
  - public_ipv6
```

C'est l'ordre par défaut : un contrôleur qui gère un parc Scaleway est le plus
souvent dans le VPC, et une adresse privée ne dépend pas de l'attribution
d'une IP publique. Un poste de travail hors VPC inverse simplement la liste.

Une machine sur plusieurs réseaux privés se joint par le réseau qu'on nomme,
et pas par celui qui arrive en premier :

```yaml
address:
  private_network: backend    # un nom, ou un identifiant
```

`scaleway_address_source` porte, sur chaque machine, la famille retenue ou la
raison de l'échec. `-vvvv` donne la ligne complète, du genre
`web01: 10.10.0.5 par private_ipv4, réseau backend`.

**Une machine sans adresse reste dans l'inventaire.** Elle n'a pas de route
SSH, mais elle reste pilotable par l'API en `delegate_to: localhost`, ce qui
est le cas d'usage Day-2 courant. `require_address: true` demande l'inverse.

## Les groupes

`group_by` choisit les axes des groupes `scw_*` :

```yaml
group_by:
  - product          # scw_product_instance
  - project          # scw_project_<identifiant>
  - region           # scw_region_fr_par
  - zone             # scw_zone_fr_par_1
  - state            # scw_state_running
  - tags             # scw_tag_env_prod
  - vpc              # scw_vpc_socle
  - private_network  # scw_private_network_backend
```

Les noms sont assainis pour Ansible : `production/web` devient
`production_web`, `pré-prod` devient `pre_prod`, et `2024` devient `_2024`
plutôt que `_024`, qui est ce qu'Ansible en ferait lui-même.

Le produit est un **axe**, pas un tag injecté : `scaleway_tags` porte ce que
Scaleway porte, et rien d'autre.

`compose`, `groups` et `keyed_groups` fonctionnent, parce qu'ils sont appelés
et pas seulement documentés :

```yaml
compose:
  ansible_user: scaleway_apple_silicon.ssh_username | default('root')
keyed_groups:
  - prefix: type
    key: scaleway_instance.commercial_type
```

## Filtrer

```yaml
organizations:
  - 99999999-9999-4999-8999-999999999999
tags:
  - env=production
tags_match: all      # « any » par défaut ; l'API ne sait exprimer que « any »
states:
  - running
exclude:
  tags:
    - canary
  states:
    - stopping
```

Ce qui peut se filtrer côté API l'est côté API, pour ne pas transférer ce
qu'on va jeter. Le reste se décide localement, et `-vvv` dit pourquoi chaque
machine écartée l'a été.

`organizations` est passé à l'API quand **une seule** est demandée, jamais en
boucle : plusieurs organisations multiplieraient les appels par les zones, les
états et les projets. Le filtrage local reste la garantie dans tous les cas,
et il n'est pas décoratif : une API qui ignore ce paramètre rendrait tout le
parc, et l'inventaire serait silencieusement plus large que demandé.

## Le cache

```yaml
cache: true
cache_plugin: jsonfile
cache_connection: ~/.ansible/tmp/scaleway
```

La clé de cache couvre **tout ce qui change le résultat** : le profil, l'URL
de l'API, les produits, les zones, les projets, les filtres, les sources de
nom, la politique d'adresse et les axes de groupes. Deux configurations
différentes ne partagent jamais un inventaire, même depuis le même répertoire.

## Le mode strict, et un piège qui n'est pas le nôtre

`strict: true`, la valeur par défaut, fait échouer l'inventaire quand un
provider échoue, au lieu de rendre un parc incomplet. Les échecs sont classés :

| ce qui arrive | ce que le plugin en fait |
|---|---|
| identifiants refusés | fatal, tout de suite, sans essayer les autres zones |
| droit manquant sur un produit | erreur nommée ; un jeton peut n'avoir qu'une partie du parc |
| produit absent d'une zone | avertissement, parce que ce n'est pas une panne |
| toute autre panne d'API | erreur nommée, avec le produit et la zone |

**Mais Ansible déclasse cet échec en avertissement.** Mesuré : sur un point de
terminaison injoignable, le plugin lève avec un message qui nomme la cause, et
`ansible-inventory` sort quand même en **0** avec un inventaire vide. Une
source d'inventaire qui ne se lit pas n'est pas une erreur pour Ansible par
défaut. Pour qu'un échec arrête une CI, il faut le lui demander :

```bash
export ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED=True
```

ou, dans `ansible.cfg` :

```ini
[inventory]
any_unparsed_is_failed = True
```

Sans ça, `strict: true` écrit la raison et ne bloque rien. Ce contrôle est
joué dans les deux sens à chaque `mise run integration`.

## Les variables posées sur chaque machine

| variable | contenu |
|---|---|
| `scaleway_id` | l'identifiant, celui qu'attendent les modules de la collection |
| `scaleway_product` | `instance`, `elastic_metal` ou `apple_silicon` |
| `scaleway_name` | le nom Scaleway, avant désambiguïsation |
| `scaleway_zone`, `scaleway_region` | la localisation |
| `scaleway_state` | l'état tel que l'API le rend |
| `scaleway_project_id`, `scaleway_organization_id` | la portée |
| `scaleway_tags` | les tags Scaleway, et rien d'autre |
| `scaleway_public_ipv4`, `scaleway_public_ipv6` | toutes les adresses, pas la première |
| `scaleway_private_ipv4`, `scaleway_private_ipv6` | idem, tous réseaux confondus |
| `scaleway_private_networks` | par réseau : identifiant, nom, VPC, adresses, MAC |
| `scaleway_address_source` | pourquoi cette `ansible_host` |
| `scaleway_<produit>` | ce qui n'appartient qu'à ce produit |
| `scaleway_raw` | la réponse brute, seulement avec `include_raw: true` |

`scaleway_<produit>` range ce qui est propre à chaque API sous son propre
préfixe, au lieu de le verser dans l'espace global : `commercial_type` pour
Instance, `offer_name` pour Elastic Metal, `ssh_username` pour Apple Silicon.

## Enchaîner sur les modules de la collection

C'est ce que l'inventaire sert à faire, et les trois variables d'identité y
suffisent, sans lookup supplémentaire :

```yaml
- name: Arrêter les machines de préproduction
  hosts: scw_tag_env_preprod
  gather_facts: false
  tasks:
    - name: Extinction
      local.scaleway.instance_server_action:
        zone: "{{ scaleway_zone }}"
        server_id: "{{ scaleway_id }}"
        action: poweroff
        wait: true
      delegate_to: localhost
```

## Diagnostiquer

```bash
ansible-inventory -i production.scaleway.yml --graph
ansible-inventory -i production.scaleway.yml --list -vvv    # le rapport
ansible-inventory -i production.scaleway.yml --list -vvvv   # et chaque adresse
```

Le rapport dit le nombre d'appels d'API, le nombre d'adresses IPAM indexées,
le nombre de machines par produit, puis chaque avertissement et chaque écart.

Un détail de lecture : `--list` sérialise les chaînes venues d'un plugin sous
la forme `{"__ansible_unsafe": "..."}`. C'est le marquage d'Ansible, pas une
anomalie ; `--graph` et les playbooks voient la chaîne.

## Combien d'appels d'API

Les réseaux privés sont listés **une fois par région**, puis joints en
mémoire. La collection officielle interroge IPAM une fois par carte réseau,
soit deux mille appels pour mille Instances à deux cartes, et en tire moins :
elle ne garde qu'une adresse privée par machine, sans dire de quel réseau.

Ici le coût de la jointure est linéaire en cartes réseau, et c'est prouvé par
comptage des consultations d'index, pas par un chronomètre.

L'index lui-même n'est construit que si un produit demandé porte des cartes
réseau privées. `products: [apple_silicon]` ne paie donc plus les douze appels
dont il n'aurait rien fait. Le filtrage s'arrête là volontairement : couper
aussi quand `address_priority` ne cite que du public viderait en silence
`scaleway_private_ipv4` et `scaleway_private_networks`, dont un `compose` peut
dépendre. Ne pas appeler et ne rien rendre ne sont pas la même chose.

Un droit manquant sur IPAM ou VPC est un **avertissement**, pas une erreur :
un jeton qui n'a pas ce droit construit très bien un inventaire de machines
publiques, et faire échouer tout l'inventaire en mode strict pour un
enrichissement dont personne n'a besoin serait un refus mal placé.

## Ce que ce plugin ne fait pas encore

* les ressources managées (Kubernetes, Load Balancers, bases de données) ne
  sont pas découvertes ; seules les machines le sont ;
* la découverte est séquentielle : pas encore de parallélisme entre produits ;
* Elastic Metal et Apple Silicon sont prouvés par des tests avec des réponses
  simulées, faute d'émulateur qui les serve (feint#631, feint#632). Instance
  est prouvé de bout en bout contre un émulateur réel.
