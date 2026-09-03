# Architecture du générateur

Ce dépôt ne contient pas une collection Ansible écrite à la main : il contient
le générateur qui l'écrit, et les décisions qui transforment une API technique
en interface Ansible cohérente. Ce que le runtime de la collection porte et ce
qu'il coûte est dans [runtime.md](runtime.md) ; la source des contrats et ses
limites mesurées sont dans [contrats-scaleway.md](contrats-scaleway.md).

## Le pipeline

```text
specs/scaleway/instance.v1.yml          contrat versionné (OpenAPI 3.1)
        |
        v  generator/parser/openapi.py
   ApiService                            IR canonique, sans Ansible ni SDK
        |
        v  generator/classifier/rules.py
   Classification                        INFO ACTION MANAGE WORKFLOW
        |                                LIFECYCLE IGNORE UNKNOWN
        v  generator/overrides/*.yml
   ProductPlan                           décision + module cible + raison
        |
        +--> generator/report/render.py  texte, JSON, Markdown
        |
        +--> generator/ansible/models.py modèle intermédiaire
                    |
                    v  generator/renderer + templates/
             plugins/modules/*.py
                    |
                    v  plugins/module_utils/scaleway.py
             exécution : client unique, erreurs, pagination
```

Chaque étape se teste seule, et chacune a son test : le parser sur un contrat
de laboratoire (`tests/fixtures/widget/`), le classifieur sur des opérations
construites à la main, le plan sur le contrat Instance réel.

**Pourquoi une représentation intermédiaire.** Sans elle, chaque évolution de
l'API ou d'Ansible retouche le même code. Avec elle, le parser ignore Ansible,
le renderer ignore OpenAPI, et la frontière entre les deux est ce qui rend les
tests possibles.

## Les décisions structurantes

### 1. Le contrat est versionné, pas téléchargé à la volée

`mise run sync:api` télécharge, `mise run report` lit le disque. Une génération
ne dépend jamais du réseau, donc elle est reproductible, et une évolution de
l'API Scaleway apparaît comme un diff dans une revue.

### 2. L'IR est immuable et se sérialise de façon déterministe

`ApiService.to_json()` produit le même octet à chaque exécution : opérations
triées par identifiant, enums triés par nom, clés nulles retirées. C'est ce qui
rend possible le golden `tests/fixtures/instance/expected_ir.json`, donc la
détection de dérive.

### 3. La clé d'opération est stable

`instance.v1.Server.ServerAction` : produit, version, ressource, identifiant.
C'est la clé des overrides et celle du rapport. Elle dépend de la ressource
déduite, donc une correction de ressource change la clé, et un override devenu
orphelin est signalé plutôt qu'ignoré.

### 4. La ressource se déduit du chemin, pas du nom de l'opération

La règle : **premier et dernier segment porteur de ressource**, après retrait
du produit, de la version, de la portée, des identifiants, des segments
d'action et des segments de valeur.

Prendre les deux extrémités plutôt que le dernier segment est ce qui donne le
même nom à `/security_groups/{id}/rules` et `/security_groups/{id}/rules/{id}`.
Une règle qui ne regarde qu'une extrémité nomme la même ressource
`security_group_rule` dans un cas et `rule` dans l'autre, soit deux modules
pour une seule chose. Le rapport le montre immédiatement, parce qu'il affiche
la ressource déduite de chaque opération.

### 5. La classification est mécanique, les exceptions sont écrites

Six règles, fondées sur le verbe de l'`operationId` et la méthode HTTP :

| verbe | méthode | classe |
|---|---|---|
| `get`, `list`, `describe` | GET | INFO |
| `create` | POST | LIFECYCLE |
| `delete`, `destroy` | DELETE | LIFECYCLE |
| `update`, `set`, `patch` | PATCH, PUT | MANAGE |
| autre | POST | ACTION |
| autre | GET | INFO |
| autre | autre | **UNKNOWN** |

Sur les 74 opérations d'Instance v1, ces règles tranchent tout : zéro UNKNOWN.
Ce n'est pas une preuve qu'elles ont raison, seulement qu'elles ont décidé, et
c'est pourquoi le rapport affiche la raison de chaque décision.

Une correction qui se répéterait sur dix opérations serait une règle manquante,
pas dix overrides.

### 6. Ce que les overrides tranchent sur Instance

Chaque décision porte sa raison dans `generator/overrides/instance.yml`, et le
chargeur refuse un changement de classification qui n'en a pas :

* **le PUT de remplacement n'est pas exposé.** Scaleway publie `Update*`
  (PATCH partiel) et `Set*` (PUT complet) pour la même ressource. Un module
  MANAGE idempotent compare et n'écrit que la différence : c'est le PATCH.
  Exposer les deux donnerait un module capable d'effacer en silence les champs
  non fournis. Sept opérations concernées ;
* **attacher un volume relève de Terraform.** `AttachServerVolume`,
  `DetachServerVolume` et leurs équivalents `FileSystem` créent une relation
  entre deux ressources ; c'est la frontière posée par le projet ;
* **`SetSecurityGroupRules` est manuel.** Remplacer en un appel toutes les
  règles d'un groupe demande de comparer deux listes ordonnées et de définir ce
  qu'est une règle « identique » : de la logique métier ;
* **quatre ressources sont renommées.** `/products/servers` est un catalogue,
  pas une ressource `product` : `server_type`, `volume_type`,
  `server_type_availability`, `server_compatible_type`.

### 7. La couverture ne se calcule pas sur un dénominateur choisi

```text
couverture Day-2 = (AUTO + OVERRIDE) / (INFO + ACTION + MANAGE + WORKFLOW)
```

LIFECYCLE et IGNORE ne sont pas au dénominateur : ce n'est pas du travail à
automatiser, c'est du travail écarté. Le rapport les compte à part, pour que
l'écart reste visible. Sans opération Day-2, la couverture vaut `null` et non
`0.0` : un ratio sans dénominateur est indéfini, pas nul.

Mesuré sur Instance v1 : **42 candidates Day-2, 41 AUTO, 1 MANUAL, couverture
97,6 %**, sur 74 opérations découvertes dont 19 LIFECYCLE et 13 IGNORE.

Ce chiffre ne dit pas « le produit est couvert à 97,6 % ». Il dit que 41 des 42
opérations *retenues comme Day-2* sont **classées pour la génération
automatique**. Toute phrase publiée sur la couverture nomme son dénominateur.

Et il ne dit pas non plus qu'un module les porte. « Générables » le laissait
entendre, et c'était le défaut : la classification autorise la génération, elle
ne la produit pas. Le compte rendu de génération publie donc **deux** ratios
côte à côte, celui-ci et celui des opérations qu'un module écrit appelle
vraiment, chacun avec son nom et sa fraction. L'écart entre les deux se lit
module par module dans la liste des écarts, où chacun porte sa raison.

### 8. Ce que le générateur ne comprend pas reste visible

Trois mécanismes, et aucun n'est décoratif :

* une opération qu'aucune règle ne tranche est `UNKNOWN`, et `report --strict`
  sort en code 2 ;
* un override qui ne désigne aucune opération existante est *orphelin*, et sort
  aussi en code 2. Ce contrôle a attrapé une clé fautive dès sa première
  exécution ;
* ce que le contrat ne dit pas (tableau sans `items`, corps sans schéma) est
  listé dans les limites du rapport, opération par opération.

## Comment un module se construit

Dans cet ordre, chaque brique avant celle qui s'appuie dessus :

1. **`plugins/module_utils/scaleway.py`** : client unique, gestion d'erreur
   centralisée, pagination complète, check mode. Écrit **avant** tout template,
   sans quoi la logique atterrit dans le template et y reste. Les cinq
   décisions du runtime et leur coût sont dans [runtime.md](runtime.md) ;
2. **`generator/ansible/models.py`** : le modèle intermédiaire, seule source de
   l'`argument_spec`, de la `DOCUMENTATION`, des `EXAMPLES` et du `RETURN`. Le
   sélecteur d'un module INFO y est **calculé** : c'est le paramètre de chemin
   que le GET exige et que le LIST ne connaît pas. Plusieurs candidats, ou
   aucun, et le modèle refuse plutôt que de choisir ;
3. **`generator/renderer/modules.py` et `generator/templates/module.py.j2`** :
   Jinja2 pour le rendu seul. Les littéraux Python et les blocs YAML sont
   produits par le renderer, pas par `repr()` ni par un dictionnaire dont
   l'ordre dépendrait de l'exécution ;
4. **`galaxy.yml` est lu par le générateur.** Le namespace, la version et les
   auteurs finissent dans chaque module ; les recopier dans le code créerait
   une seconde source ;
5. **la dérive** : `mise run check:generated` régénère les golden **et** les
   modules, puis exige que git ne voie aucune différence, fichiers non suivis
   compris.

### Ce qui n'est pas décidé dans un template

La règle qui tranche tous les cas limites : **si un template a besoin d'un `if`
sur autre chose qu'une présence de valeur, la décision manque dans le modèle.**
Elle se mesure sur le fichier produit : il ne définit que `main`, `main` fait
deux choses, et il n'y a ni condition ni boucle dedans.

### Deux golden, deux mesures différentes

* `tests/fixtures/instance/expected_ir.json` fige ce que le **parser** lit du
  contrat réel. Il bouge quand Scaleway bouge ;
* `tests/fixtures/widget/expected_modules/` fige ce que le **renderer** écrit,
  depuis le contrat de laboratoire. Il ne doit pas bouger le jour où Scaleway
  ajoute un serveur.

## Ce que le projet ne fait pas

Pas de second provider Terraform, pas de génération des `create` et des
`delete`, pas d'abstraction multi-cloud. La frontière est posée une fois :

```text
Terraform provisionne les ressources. Ansible exploite les ressources existantes.
```

Une opération qui crée, supprime ou relie des ressources n'a pas sa place ici,
même quand le générateur sait la produire.
