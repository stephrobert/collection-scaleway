# Les contrats Scaleway : la source, ses limites, sa surveillance

Le générateur lit des documents **OpenAPI 3.1** publiés par Scaleway et
versionnés dans `specs/scaleway/`. Cette page dit d'où ils viennent, ce qu'ils
portent, ce qu'ils ne portent pas, et comment le dépôt s'aperçoit qu'ils ont
bougé.

## La source

Chaque page produit du portail developers expose un document téléchargeable :

```text
https://www.scaleway.com/en/developers/api/<slug>/<version>/schema.yml
```

`mise run sync:api` les télécharge, `specs/scaleway/products.txt` les indexe.
La génération, elle, ne lit que le disque : elle ne dépend jamais du réseau,
donc elle est reproductible hors ligne, et une évolution d'API arrive comme un
diff relisible plutôt que comme un résultat qui change tout seul.

**Le slug du portail n'est pas toujours le nom du produit dans le SDK.** Il se
vérifie sur la page du produit plutôt qu'il ne se devine :

| nom SDK | slug du portail |
|---|---|
| `baremetal` | `elastic-metal` |
| `k8s` | `kubernetes` |
| `lb` | `load-balancer/zoned` |
| `vpcgw` | `public-gateway` |

Certains produits sont scindés côté portail : `account/v3` répond 404, alors
que `account/project/v3` et `account/contract/v3` répondent 200.

**Il n'existe aucun index lisible par une machine.** Aucun dépôt public de
Scaleway ne publie ces documents, et l'URL sans version répond 404. La liste
des produits suivis est donc tenue à la main dans `specs/scaleway/products.txt`.
C'est un fait sur Scaleway, pas un choix de conception.

## Ce que le document porte

Mesuré sur `instance.v1.yml` : **38 chemins, 74 opérations, 134 schémas, 18
enums**, et pour chaque opération :

* un `operationId` (`ListServers`, `ServerAction`, ...) ;
* la portée dans le chemin, avec l'énumération fermée des zones :
  `/instance/v1/zones/{zone}/servers`, `zone ∈ {fr-par-1, …, it-mil-1}`. VPC v2
  fait la même chose avec `{region}` ;
* les paramètres de requête typés, pagination `page` et `per_page` comprise ;
* les enums, atteints par référence :
  `#/components/schemas/scaleway.instance.v1.Server.Action` vaut
  `[poweron, backup, stop_in_place, poweroff, terminate, reboot, enable_routed_ip]` ;
* les corps de requête, propriété par propriété, avec leurs descriptions ;
* les réponses, par référence vers un schéma nommé ;
* les dépréciations au niveau du champ (`routed_ip_enabled`, `enable_ipv6`) ;
* une extension `x-properties-order` qui donne l'ordre d'origine des champs.

## Ce que le document ne porte pas

Le document publié est une **projection avec pertes** de l'IDL interne de
Scaleway, plus pauvre que les SDK générés depuis la même source. Ces limites
sont mesurées sur `instance.v1.yml`, et le générateur les **signale** au lieu
de les combler par des suppositions : elles apparaissent dans le rapport sous
« limites du contrat ».

### `total_count` est absent des réponses de liste

Le document déclare `ListServersResponse` avec le seul champ `servers`. Le SDK
Python déclare pour le même type :

```python
class ListServersResponse:
    total_count: int
    servers: list[Server]
```

Une pagination qui compte sur `total_count` doit donc le lire au runtime, pas
dans le contrat.

### Les tableaux d'un corps de requête ne déclarent pas leurs éléments

```yaml
tags:
  type: [array, "null"]
  description: Tags of the Instance.
```

Ni `items`, ni type d'élément. Dix-sept paramètres d'Instance v1 sont dans ce
cas. Le générateur pose `elements: str` par défaut **et** inscrit le paramètre
dans les limites du rapport, pour qu'un type faux ne passe pas inaperçu.

### Aucun champ de corps n'est déclaré `required`

`ServerActionRequest` marque `requestBody.required: true`, mais son schéma ne
porte aucune liste `required`. Le champ `action`, que l'API refuse d'omettre,
n'est donc pas obligatoire selon le contrat. Les obligations de corps viennent
des overrides, et elles portent leur raison.

### Les enveloppes protobuf transparaissent

`google.protobuf.BoolValue`, `Int32Value`, `StringValue` et `UInt32Value`
apparaissent comme schémas et se résolvent en types nullables. Le parser les
traverse ; l'IR ne porte que le type utile.

### Il n'y a ni waiter ni règle d'idempotence

Le contrat ne dit pas quel champ observer pour savoir qu'une action est
terminée. Le SDK, lui, expose des waiters. La configuration d'attente vient
donc des overrides.

## Deux rôles qui ne se confondent jamais

| rôle | qui le tient |
|---|---|
| décrire l'API pour la génération | les documents OpenAPI du portail, versionnés dans `specs/scaleway/` |
| appeler l'API à l'exécution | le SDK Python officiel, comme la collection Scaleway |

Le générateur ne lit pas le SDK, et les modules ne lisent pas le contrat. Les
SDK officiels sont générés depuis un IDL interne non publié : en dépendre
demanderait d'analyser du code Python ou Go pour en extraire un contrat, soit
un parser sur une cible mouvante. Ils servent ici de source d'arbitrage quand
le document OpenAPI est ambigu ou muet.

## Risques et surveillance

| risque | pourquoi il est réel | ce qui le rend visible |
|---|---|---|
| l'URL `schema.yml` n'est pas contractuelle | c'est un lien de page web, et le portail a déjà été refondu | `mise run sync:api` échoue bruyamment sur un 404 plutôt que de laisser un fichier périmé |
| pas d'index des produits | aucun dépôt public n'en publie | `specs/scaleway/products.txt`, tenu à la main, avec le slug mesuré |
| la projection perd de l'information | mesuré sur `total_count`, `items`, `required` | le rapport liste les limites rencontrées, opération par opération |
| l'API bouge | Scaleway a ajouté 453 méthodes SDK et en a retiré 26 en douze mois | le golden IR et `report --strict` échouent sur toute opération non triée |

## Reproduire les mesures

```bash
curl -sL -o /dev/null -w '%{http_code} %{size_download}\n' \
  'https://www.scaleway.com/en/developers/api/instance/v1/schema.yml'

mise run sync:api
python -m generator inspect instance
python -m generator report instance --strict
```
