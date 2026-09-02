# Ce que dit OpenSSF Scorecard, et ce qu'il ne dit pas

Scorecard audit un dépôt de l'extérieur : protection de branche, épinglage des
actions, motifs de workflow dangereux, politique de sécurité, outil de mise à
jour des dépendances. C'est un bon détecteur, et un mauvais objectif.

Cette page est écrite sous une règle : **un contrôle ne se relève pas en
satisfaisant son détecteur.** Chacun de ceux qui suivent a une forme qui note
bien et ne veut rien dire, exiger des approbations qu'un contournement saute
ensuite, afficher un badge décrivant des pratiques que personne ne suit. C'est
la même faute qu'un commentaire décrivant un contrôle que personne n'applique,
et c'est précisément ce que ce dépôt passe son temps à traquer ailleurs.

## L'état mesuré, et son honnêteté

**Au 2 septembre 2026, il n'y a pas encore de score.** Le dépôt vient d'être
créé et publié, et Scorecard n'a rien audité tant que le premier `git push`
n'a pas eu lieu. Tout ce qui suit est donc une **estimation lue dans les
fichiers**, pas un relevé. Elle sera remplacée par le score réel dès la
première exécution du workflow `Scorecard`, et cette phrase avec.

La référence est le dépôt jumeau, `stephrobert/feint`, mesuré à **7,9** le
25 août 2026. Sa configuration est reprise ici presque telle quelle, et ses
cinq contrôles sous 10 sont exactement ceux qu'aucune configuration ne règle.

## Ce que la configuration devrait donner

| contrôle | attendu | ce qui le tient |
|---|---|---|
| Token-Permissions | 10 | `permissions: {}` sur chaque workflow, puis le minimum par job |
| Pinned-Dependencies | 10 | toute action épinglée par SHA, dépendances Python verrouillées avec empreintes |
| Dangerous-Workflow | 10 | aucun `pull_request_target`, aucun `workflow_run`, aucune interpolation dans un `run:` |
| Security-Policy | 10 | `SECURITY.md`, avec des délais tenables plutôt que copiés |
| Dependency-Update-Tool | 10 | `.github/dependabot.yml`, pip et github-actions, quarantaine de 14 jours |
| SAST | 10 | CodeQL sur Python, plus quatre scanners de workflow qui font porte |
| License | 10 | `LICENSE` à la racine, GPL-3.0-or-later |
| CI-Tests | 10 | quatre jobs sur chaque pull request |
| Binary-Artifacts | 10 | aucun binaire versionné |
| Vulnerabilities | 10 | OSV-Scanner sur les pull requests et chaque semaine |
| Branch-Protection | 4 à 8 | ruleset versionné dans `.github/rulesets/main.json`, comparé au vivant par une porte |

## Les contrôles qui ne se règlent pas par une configuration

### Branch-Protection : le contournement, et ce qu'il permet vraiment

Le ruleset garde un contournement pour le rôle administrateur :

```json
"bypass_actors": [{ "actor_id": 5, "actor_type": "RepositoryRole",
                    "bypass_mode": "pull_request" }]
```

`bypass_mode` porte toute la décision. `"pull_request"` et non `"always"` :
l'administrateur peut fusionner une pull request que les règles retiendraient,
et **ne peut pas pousser sur `main` directement**. La suppression et le
non-fast-forward restent fermés à tout le monde.

Ce que ce contournement achète est une seule chose : fusionner quand une porte
est rouge pour une raison qui n'est pas le code, typiquement un scanner qui
n'arrive pas à télécharger son propre binaire.

Le coût est écrit, parce qu'une décision dont on ne liste que les bénéfices est
une justification : **une porte que le propriétaire peut lever mesure la
discipline du propriétaire, pas le code.** Rien ne garantit que la trappe
serve aux pannes de réseau plutôt qu'à un test rouge un vendredi. Ce qui la
rend visible plutôt qu'invisible, c'est que chaque usage est une fusion sur une
pull request dont les vérifications sont au dossier : une trace, pas une
prévention.

### Code-Review : il mesure le nombre de relecteurs

Chaque changement passe par une pull request dont toutes les vérifications
tournent, et aucune ne porte d'approbation humaine, parce qu'il y a un humain.
Le score est exact ; ce qu'il mesure est le nombre de relecteurs, pas si les
changements sont jugés contre quelque chose.

Ce que ce dépôt substitue à un second lecteur est de la machinerie, et cette
substitution **est** le projet : un changement est jugé sur le fait qu'un
playbook réel passe (`mise run integration`), que la surface de l'API n'a pas
bougé (le golden de l'IR et le rapport strict), qu'`ansible-test sanity` accepte
le fichier produit, et que la garde ajoutée mord vraiment (`mise run falsify`,
46 mutations). Scorecard ne sait pas lire ça, et ça ne remplace pas un
relecteur. Les deux phrases sont vraies en même temps.

### Maintained et Contributors : le temps et le nombre

Le premier est à 0 pour tout dépôt de moins de 90 jours, quoi qu'il contienne.
Le second compte les organisations distinctes parmi les contributeurs. Ni l'un
ni l'autre ne se corrige, et essayer serait du bruit dans l'historique.

### CII-Best-Practices : un badge, pas une pratique

Le badge s'obtient en répondant à un questionnaire sur soi-même. Il vaut ce que
vaut la personne qui le remplit. Il sera demandé quand les réponses seront
vraies, pas pour le score.

## Ce qui manque encore, et qui n'est pas un contrôle Scorecard

* **Aucune release, donc aucune signature ni provenance.** La collection n'est
  pas publiée sur Galaxy : son namespace est `local`. Le jour où elle sera
  publiée, la signature et l'attestation seront la condition de cette
  publication, pas un ajout d'après-coup.
* **`egress-policy: audit` et non `block`.** Une allowlist écrite sans avoir
  observé le trafic réel casse la CI sans rien prouver. Le passage à `block`
  se fera sur les relevés d'`audit`, quand il y en aura.
* **Fuzzing.** Le générateur lit des contrats OpenAPI, ce qui est une entrée
  structurée et un sujet de fuzzing raisonnable. Rien n'est fait, et le dire
  vaut mieux que de compter sur les 74 opérations du contrat versionné comme
  s'il s'agissait d'un corpus.
