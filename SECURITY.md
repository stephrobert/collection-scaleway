# Politique de sécurité

## Signaler une faille

Ouvrez un **avis de sécurité privé** sur GitHub, par
`Security` puis `Report a vulnerability`, plutôt qu'une issue publique.

Délais engagés :

| étape | délai |
|---|---|
| accusé de réception | 3 jours ouvrés |
| première évaluation, avec la gravité retenue et sa raison | 10 jours ouvrés |
| correctif ou décision motivée de ne pas corriger | 90 jours |

Le dépôt est tenu par une seule personne. Ces délais sont ceux qu'une personne
seule peut tenir, et ils sont écrits pour cette raison plutôt que copiés d'un
modèle : un engagement à 24 heures que personne ne peut honorer vaut moins
qu'un engagement à 3 jours qui est tenu.

## Le périmètre, et ce qu'il exclut

Ce dépôt produit un **générateur** et une **collection Ansible**. Il n'héberge
aucun service, ne stocke aucune donnée, et ne détient aucun identifiant.

Entrent dans le périmètre :

* une faille dans le code généré ou dans le runtime des modules
  (`ansible_collections/local/scaleway/plugins/`), notamment tout ce qui
  écrirait un secret dans un journal, contournerait `no_log`, ou exécuterait
  une donnée venue de l'API ;
* une faille dans le générateur (`generator/`) qui produirait un module
  dangereux à partir d'un contrat OpenAPI hostile ;
* une faiblesse de la chaîne d'approvisionnement : workflow exploitable,
  dépendance non épinglée, action compromise.

N'entrent pas dans le périmètre :

* les vulnérabilités des APIs Scaleway elles-mêmes, à signaler à Scaleway ;
* les vulnérabilités d'`ansible-core` ou du SDK Scaleway, à signaler à leurs
  projets respectifs. Signalez-les quand même ici si ce dépôt les **aggrave**,
  par exemple en épinglant une version connue vulnérable.

## Ce que le dépôt fait déjà, et qui se vérifie

Les affirmations ci-dessous sont contrôlées par une porte de CI, pas par cette
page. Une phrase décrivant un contrôle que personne n'applique se lit
exactement comme le contrôle.

| affirmation | ce qui la tient |
|---|---|
| aucune action tierce référencée par un tag mobile | `zizmor` et `poutine`, dans `Sécurité des workflows` |
| aucune action tierce hors de la liste autorisée | `plumber`, qui lit `.plumber.yaml` : une action absente de la liste fait échouer l'analyse |
| aucun droit par défaut sur le `GITHUB_TOKEN` | `permissions: {}` au niveau de chaque workflow, vérifié par `poutine` |
| aucune dépendance Python non épinglée | `requirements-dev.lock` avec empreintes, installé par `pip install --require-hashes` |
| aucun secret dans le dépôt | `TruffleHog` en mode `--results=verified --fail` |
| la protection de branche appliquée est celle qui est déclarée | le job `La protection de branche est celle qui est déclarée` compare le ruleset vivant à `.github/rulesets/main.json` |
| aucun identifiant Scaleway nécessaire pour la CI | les contrats sont versionnés, et le scénario d'intégration refuse de jouer si `SCW_API_URL` ne pointe pas sur l'émulateur |

## Ce que le dépôt ne fait pas

* **Aucune release signée, aucune provenance.** La collection n'est pas publiée
  sur Ansible Galaxy : son namespace est `local`, et l'archive ne circule que
  par artefact de CI ou construction locale. Le jour où elle sera publiée, la
  signature et l'attestation de provenance seront la condition de cette
  publication, pas un ajout ultérieur.
* **Aucune revue par un second relecteur.** Il y a un mainteneur. Ce que ce
  dépôt substitue à un second lecteur est de la machinerie, décrite dans
  `docs/scorecard.md` : elle ne remplace pas un relecteur, et les deux phrases
  sont vraies en même temps.
