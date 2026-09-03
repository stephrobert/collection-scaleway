# Le runtime de la collection

Ce que `plugins/module_utils/scaleway.py` porte, pourquoi, et ce que ça coûte.

État au 1er septembre 2026 : écrit, mesuré par 15 tests unitaires, jugé par
`ansible-test sanity`, et exercé de bout en bout contre un émulateur local.

## Le partage des rôles

```text
generator/                              lit le contrat, décide, écrit le module
ansible_collections/stephrobert/scaleway/
  plugins/modules/                      la documentation, l'argument_spec, l'opération
  plugins/module_utils/                 le client, l'erreur, la pagination, le check mode
```

Un module généré ne contient **aucune** logique. C'est mesuré, pas affirmé :
`test_le_module_ne_porte_aucune_logique` analyse le fichier produit et exige
qu'il ne définisse que `main`, que `main` fasse deux choses, et qu'il n'y ait
ni condition ni boucle dedans. Une logique qui s'inviterait dans le template
ferait immédiatement rougir ce test.

## Décision 1 : exécuter la méthode et le chemin du contrat

Le SDK Python est le client d'exécution. Restait à savoir **comment** un module
généré atteint une opération. Deux chemins existaient :

| chemin | ce qu'il demande de savoir | ce qu'il coûte |
|---|---|---|
| les classes générées du SDK (`InstanceV1API.get_server`) | traduire `GetServer` en `get_server`, et espérer | une seconde source, jamais mesurée, qui dérive en silence |
| `scaleway_core.api.API._request(method, path, ...)` | la méthode et le chemin, que l'IR porte déjà | une dépendance à une méthode préfixée d'un underscore |

Le second est retenu. Le contrat reste **la seule source** : le générateur ne
devine aucun nom de méthode SDK, et l'IR porte déjà `http_method` et `path`.

Le prix est réel, et il est tenu par une garde plutôt que par un espoir :
`test_le_sdk_expose_toujours_le_point_dexecution_attendu` vérifie la signature
de `API._request`. Si le SDK la déplace, c'est `mise run check` qui le dit, pas un
playbook en production.

## Décision 2 : une seule construction de client

La collection officielle en a deux, et la seconde ignore silencieusement
`access_key` passé en paramètre.

`build_client()` est la seule, et son ordre de priorité est celui qu'un
utilisateur attend :

```text
paramètres du module  >  variables d'environnement  >  fichier de configuration
```

Le journal du SDK reçoit un `NullHandler` : sans lui, chaque exécution sans
fichier de configuration écrit un avertissement sur la sortie d'erreur, ce qui
est le cas normal en CI.

## Décision 3 : la validation dépend de la cible

Le SDK valide le format des clés (`SCWXXXXXXXXXXXXXXXXX`) dès la construction
d'une `API`. C'est utile contre l'API de production, et ça interdirait le seul
scénario de test sans credentials du projet.

La règle tient en une phrase, et elle est dans le code :

* **contre `https://api.scaleway.com`**, la validation complète du SDK
  s'applique ;
* **contre toute autre `api_url`**, seule la présence des identifiants est
  exigée, avec un message qui nomme le paramètre et sa variable
  d'environnement.

C'est ce qui donne son sens à la règle 7 du projet : `SCW_API_URL` honoré de
bout en bout n'est pas une intention, c'est ce qui rend `mise run integration`
possible.

## Décision 4 : la pagination va jusqu'au bout, et sait s'arrêter

`page` et `per_page` **ne sont pas des options de module**. Les exposer
permettrait de rendre une première page en silence, présentée comme une liste
complète. Le runtime parcourt, et s'arrête sur trois conditions, dans cet
ordre :

1. la page rendue contient moins d'éléments que demandé ;
2. `total_count` est présent et le compte est atteint. Le contrat publié ne
   déclare pas ce champ ; le SDK le reconstitue depuis l'en-tête
   `x-total-count`, et l'émulateur le rend dans le corps. On s'en sert s'il est
   là, on ne l'exige pas ;
3. `MAX_PAGES` est atteint, et **c'est une erreur**. Une API qui ignorerait
   `per_page` ferait boucler la fonction indéfiniment ; mieux vaut échouer
   bruyamment.

Les trois sont mesurées, et la première est falsifiée : remplacer `<` par `<=`
fait rougir `test_la_pagination_va_jusquau_bout`.

## Décision 5 : une erreur dit quoi diagnostiquer, et rien d'autre

Un message de module finit dans un journal, et un journal se partage. L'erreur
porte l'opération, le statut HTTP, l'identifiant de requête et le `type` de
l'API. Elle ne recopie **jamais** le corps de la réponse : il peut contenir ce
que l'appelant a envoyé.

```json
{
  "msg": "resource is not found",
  "operation": "GetServer",
  "status_code": 404,
  "request_id": "req-42",
  "api_type": "not_found"
}
```

Mesuré par `test_une_erreur_ne_recopie_pas_le_corps_de_la_reponse`, et
falsifié : recopier la charge utile entière fait rougir ce test.

## Ce que ce runtime ne porte pas encore

* **`wait` et `wait_timeout`** existent (`scaleway_waitable_argument_spec`) mais
  aucune attente n'est implémentée : un module d'information ne déclenche rien.
  Elle arrive avec le module d'action, qui en a besoin ;
* **la comparaison et le diff** d'un module MANAGE : l'idempotence ne se
  généralise qu'après avoir été prouvée une fois ;
* **la conversion objet vers dict** n'a pas lieu d'être : en exécutant
  le chemin du contrat, le runtime reçoit du JSON, jamais un objet du SDK. Le
  défaut d'`object_to_dict` de la collection officielle est évité en ne
  traversant pas le terrain où il se produit.

## La preuve de bout en bout

`mise run sanity` juge le fichier produit. Il ne dit rien de son comportement.
`mise run integration` le dit :

```bash
mise run integration
```

Le scénario démarre [feint](https://github.com/stephrobert/feint), un émulateur
local des clouds européens, y crée 104 serveurs, assemble la collection et joue
un vrai playbook contre elle. 104 et non 10 : en dessous d'une page, la
pagination ne serait jamais exercée, et une liste incomplète passerait pour
complète.

Ce que le playbook prouve, et qu'aucun test unitaire ne peut prouver :

* la liste rend tous les serveurs, donc les deux pages ;
* l'identifiant fourni bascule sur la lecture unitaire, et le module rend
  `server` et non `servers` ;
* un filtre du contrat (`name`) arrive bien jusqu'à l'API ;
* le check mode rend la même chose et ne change rien ;
* un identifiant inconnu produit l'erreur décrite plus haut, sans secret.

### Ce que le scénario demande à l'émulateur plutôt que de l'écrire

* **les identifiants**, par `feint env scaleway --endpoint <url>`. Les écrire
  dans ce dépôt créerait une seconde source de ce que l'émulateur accepte. La
  commande écrit ses exports sur la sortie standard et ses remarques sur la
  sortie d'erreur, ce qui rend la lecture sûre ;
* **la sonde**, par `feint wait`, qui rend 0 quand l'émulateur répond et 1
  sinon. `feint status` ne convient pas : mesuré, il sort en 0 dans les deux
  cas, et l'utiliser aurait fait croire qu'un émulateur répondait toujours ;
* **le nombre de serveurs attendu**, relu à l'émulateur après amorçage plutôt
  que supposé. Un émulateur adopté peut déjà en contenir.

Une garde tient tout cela : si `feint env` ne rend pas `SCW_API_URL` pointant
vers l'émulateur, le scénario s'arrête. C'est la garde la plus coûteuse à
perdre du dépôt, parce que sans elle le playbook partirait avec ce qui traîne
dans le shell, c'est-à-dire éventuellement vers l'API Scaleway réelle.

### Deux backends pour le même scénario

`FEINT_VM` choisit ce qui porte un serveur allumé. Le scénario ne change pas ;
seul le sujet durcit.

```bash
mise run integration                        # off : l'état est de la comptabilité
mise run integration FEINT_VM=incus-ovn     # une machine démarre pour de bon
```

Mesuré le 1er septembre 2026 sur feint 0.12.1, hôte avec Incus 7.2 et OVN :

| mode | `CreateServer` | `poweron` jusqu'à `running` | ce qui existe derrière |
|---|---|---|---|
| `off` | 0,02 s | 0,0 s | rien, l'état est un enregistrement |
| `incus-ovn` | 0,02 s | 1,0 s | un conteneur `feint-scw-<uuid>` RUNNING dans Incus |

Créer un serveur ne démarre rien dans les deux cas : chez Scaleway un serveur
naît `stopped`, et seul `poweron` allume. C'est ce qui rend l'amorçage de 104
serveurs aussi bon marché sous `incus-ovn` que sous `off`.

Ce que le mode machine ajoute à la preuve : le playbook lit un serveur dont
l'état `running` correspond à un vrai processus, pas à un champ que l'émulateur
s'est écrit à lui-même. `feint doctor --vm incus-ovn` dit avant tout démarrage
si l'hôte peut le délivrer, et refuse plutôt que de se rabattre sur un mode plus
faible.

Deux choses apprises en le branchant, toutes deux tenues par un test et une
falsification :

* **`--cleanup` n'est pas du confort.** Sans lui, une exécution sous `incus-ovn`
  laisse derrière elle le conteneur qu'elle a démarré. Constaté sur la machine
  de développement, `incus list` à l'appui ;
* **adopter un émulateur peut mesurer autre chose que ce qui est demandé.** Un
  `mise run integration FEINT_VM=incus-ovn` lancé pendant qu'un émulateur en `off`
  écoutait déjà a été adopté et est passé au vert **sans démarrer une seule
  machine**. La sortie était celle d'un run réussi ; seule la durée de démarrage,
  0,0 s au lieu de 1,0 s, disait que rien ne s'était passé. Le scénario lit
  maintenant `feint status --format json`, compare le champ `machines`, et
  refuse d'adopter un émulateur dans un autre mode. `FEINT_ADDR` permet de
  prendre un autre port plutôt que d'arrêter celui de quelqu'un d'autre.

### En CI

Le job `integration` démarre l'émulateur avec l'action que feint publie :

```yaml
- uses: stephrobert/setup-feint@b7eba1d4fcaccf65cf9124bf97a0d995996709b9 # v1
  with:
    version: "0.12.1"
    addr: 127.0.0.1:4599
```

Elle télécharge le binaire de la release, **contrôle sa somme SHA-256** contre
le `checksums.txt` publié, puis lance `feint start`. Le dépôt feint tient
lui-même la garde qui compte ici : un job de son `workflow-security` compare le
miroir `stephrobert/setup-feint@v1` à `.github/actions/setup-feint/action.yml`
de son propre dépôt, et échoue tant que les deux diffèrent.

`scripts/integration.py` **adopte** un émulateur déjà en écoute et ne l'arrête
pas : le cycle de vie appartient à qui l'a démarré. C'est ce qui permet au même
script de servir en local, où il démarre et range, et en CI, où l'action s'en
charge.

**L'émulateur est un backend de test, pas une dépendance.** Rien dans
`plugins/` ne le connaît, `mise run check` tourne sans lui, et la collection livrée
ne le mentionne pas. La cible est séparée, et elle **échoue** quand feint est
absent plutôt que de se sauter : un test qui se saute tout seul finit par ne
plus jamais tourner.

### Ce que l'émulateur sert de notre feuille de route

Mesuré en comparant **méthode et chemin** — les identifiants d'opération ne se
comparent pas, le contrat et le SDK Go ne les nomment pas pareil.

| version de feint | INFO | ACTION | MANAGE | Day-2 servies |
|---|---|---|---|---|
| 0.12.1, la version épinglée par la CI | 23/27 | 1/3 | 10/11 | **35/42** |
| `main`, non publiée au 1er septembre 2026 | 25/27 | 1/3 | 11/11 | **38/42** |

`ServerAction` et `UpdateServer` sont servies dans les deux : **les étapes 3 et
4 sont prouvables** sans attendre quoi que ce soit.

Les six refus remontés en amont ont tous été arbitrés, et quatre ont changé
d'avis :

| opération | issue | verdict |
|---|---|---|
| `UpdatePrivateNIC` | [#624](https://github.com/stephrobert/feint/issues/624) | servie |
| `GetDashboard` | [#626](https://github.com/stephrobert/feint/issues/626) | servie |
| `GetServerCompatibleTypes` | [#626](https://github.com/stephrobert/feint/issues/626) | servie |
| `GetServerTypesAvailability` | [#626](https://github.com/stephrobert/feint/issues/626) | refus maintenu |
| `ListVolumesTypes` | [#625](https://github.com/stephrobert/feint/issues/625) | refus maintenu |
| `ExportSnapshot` | [#627](https://github.com/stephrobert/feint/issues/627) | refus maintenu |

`UpdatePrivateNIC` méritait l'argument qu'il a reçu, et la vérification le
confirme du côté consommateur : le `PATCH` écrit les étiquettes, le `GET` les
relit, et une seconde écriture identique laisse le même état. C'est la fixture
d'idempotence minimale dont l'étape 4 a besoin, et elle tient sur un seul champ
de type liste, là où la normalisation mord.

**Tester une version non publiée ne demande rien de particulier** :
`FEINT=/chemin/vers/le/binaire mise run integration`. C'est ainsi que le
tableau ci-dessus a été rempli, sur un binaire construit depuis `main` sans
poser de tag. La CI, elle, reste épinglée à une **release** : une CI qui suit
une branche mesure une cible mouvante.

### Ce que l'émulateur ne sert pas, et comment il le dit

Une route non montée reçoit **501 `not_emulated`**, avec un message qui renvoie
à `/_feint/routes`. C'est une réponse honnête : rien ne peut passer pour un
succès. Utile à savoir pour les étapes suivantes, parce que la surface montée
n'est pas la surface publiée.

Mesuré le 1er septembre 2026, sur `instance/v1` : le contrat publie huit routes
`PUT`, l'émulateur en sert trois. `SetImage`, `SetSecurityGroup`,
`SetSecurityGroupRule`, `SetSnapshot` et `SetVolume` répondent 501. Aucune
n'est exposée par ce projet (elles sont toutes `ignore` dans les overrides,
parce qu'un PATCH existe), donc rien n'est bloqué ; mais un scénario d'étape 4
qui voudrait les exercer se heurterait au mur, et il vaut mieux le savoir
avant.

L'écart de comptage qui allait avec a été remonté en amont, corrigé et livré
dans feint 0.12.1 ([#622](https://github.com/stephrobert/feint/issues/622)) :
les six opérations que le document publie et que le SDK Go n'enveloppe pas sont
maintenant triées dans `coverage/contract-only.json`, cinq en `backlog` et une
`declined`, chacune avec sa raison. **Rien d'observable n'a bougé** : ces cinq
routes répondaient 501 avant, elles répondent 501 après, et c'est vérifié.

Pour ce projet, cela ne change rien : les cinq `PUT` sont déjà écartées par
override, parce qu'un `PATCH` existe pour chacune. Elles sont en `backlog` chez
feint précisément parce qu'une collection générée depuis le document du portail
est le seul client capable de les atteindre.

## Le piège rencontré en écrivant tout ceci

`ansible-test` demande à git la liste des fichiers à examiner. La première
version de ce dépôt rangeait la collection à la racine et en assemblait une
copie sous `build/`, qui est ignorée par git. Il n'y trouvait donc aucun
fichier :

```text
WARNING: All targets skipped.
```

...et il **sortait en 0**. Vingt-quatre tests annoncés, zéro fichier examiné,
un vert parfait, indiscernable de celui d'une collection irréprochable.

La correction n'a pas été de contourner le symptôme mais de retirer sa cause :
la collection est rangée dans `ansible_collections/stephrobert/scaleway/`, suivie par
git, et `ansible-test` y travaille **en place**. Le script qui fabriquait la
copie a été supprimé.

Ce qui reste est la garde, et elle porte maintenant sur la vraie condition :

* **avant**, `scripts/sanity.py` refuse de mesurer si git ne suit aucun fichier
  de la collection — le cas exact qui produisait le faux vert ;
* **après**, il refuse la sortie si la phrase `All targets skipped` apparaît.

Les deux sont falsifiées (`sanity-sur-collection-invisible`,
`sanity-qui-ne-mesure-rien`). Hors d'un dépôt git, la première ne s'applique
pas : `ansible-test` parcourt alors le disque, et refuser là serait refuser une
mesure qui a bien lieu.

## Le moteur de l'inventaire, couche par couche

Le plugin `plugins/inventory/scaleway.py` ne porte que le dialogue avec
Ansible. Tout ce qui décide vit sous `plugins/module_utils/inventory/`, en
couches qui se testent seules :

| couche | ce qu'elle décide |
|---|---|
| `config` | lire et valider ce que l'utilisateur a demandé |
| `providers` | traduire une API Scaleway en modèle normalisé |
| `network` | indexer IPAM, réseaux privés et VPC, puis joindre |
| `address` | choisir `ansible_host`, et savoir l'expliquer |
| `hostname` | choisir `inventory_hostname`, et refuser les collisions |
| `groups` | nommer les groupes, et assainir ces noms |
| `models` | le modèle normalisé, seul objet qui traverse les couches |
| `errors` | distinguer un droit refusé d'une panne et d'une absence |

Cette carte vivait dans la docstring de `inventory/__init__.py`, jusqu'à ce
qu'`ansible-test sanity` la refuse : sous `module_utils`, les `__init__.py`
doivent être **vides** pour ansible-core 2.17 et 2.18, que `meta/runtime.yml`
déclare supporter. Les versions récentes l'acceptent, et c'est le genre
d'écart qu'une matrice existe pour attraper.
