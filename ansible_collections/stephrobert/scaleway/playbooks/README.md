# Playbooks de la collection

Des playbooks qui se lancent, pas des extraits qui illustrent.

Ils vivent dans `playbooks/`, l'emplacement qu'Ansible reconnaît : une fois la
collection installée, ils s'appellent par leur nom complet, sans chemin.

Chacun est joué par `mise run integration` contre un émulateur local, à chaque
exécution de la cible. Un exemple que personne n'exécute pourrit, et un exemple
faux dans une documentation coûte plus cher qu'une documentation absente.

| playbook | ce qu'il montre |
|---|---|
| [inventaire_serveurs.yml](inventaire_serveurs.yml) | lister une zone entière, répartir par état et par type |
| [detail_dun_serveur.yml](detail_dun_serveur.yml) | le même module en lecture unitaire, et le `changed=false` d'un module d'information |
| [arreter_un_serveur.yml](arreter_un_serveur.yml) | arrêter une Instance désignée, attendre l'état visé, puis le relire |

## Les lancer

Contre un vrai compte Scaleway, avec les identifiants dans l'environnement ou
dans le fichier de configuration :

```bash
export SCW_ACCESS_KEY=... SCW_SECRET_KEY=...

# depuis le dépôt
ansible-playbook playbooks/inventaire_serveurs.yml -e zone=fr-par-1

# depuis la collection installée, par son nom complet
ansible-playbook stephrobert.scaleway.inventaire_serveurs -e zone=fr-par-1
```

Sans compte et sans dépense, contre un émulateur local :

```bash
mise run integration          # démarre feint, amorce, joue tout
```

## Ce qu'ils n'illustrent pas encore

Deux modules existent : la lecture et l'action. La gestion d'état durable
(étape 4) manque encore, et c'est elle qui rendra un rôle utile — il y aura
alors une séquence à tenir plutôt qu'un appel à faire.

`arreter_un_serveur.yml` ne choisit jamais tout seul quelle machine arrêter :
sans `-e server_id=<uuid>` il ne fait rien et le dit. Un playbook d'exemple qui
décide à votre place est un piège, pas une documentation.

La collection s'installe par chemin ou par archive : son namespace est `local`,
qui n'est pas publié sur Galaxy.
