# stephrobert.scaleway

Modules Ansible **Day-2** pour les APIs Scaleway. La collection ne provisionne
rien : elle exploite ce qui existe.

> Terraform provisionne les ressources. Ansible exploite les ressources
> existantes.

Cette collection est **produite par un générateur** qui lit les documents
OpenAPI publiés par Scaleway. Le code des modules n'est pas écrit à la main et
ne se corrige pas à la main : voir le dépôt qui l'héberge, à la racine.

## Installer

```bash
ansible-galaxy collection install build/dist/local-scaleway-0.1.0.tar.gz
```

Le namespace `local` n'est pas publié sur Galaxy : la collection s'installe par
chemin ou par archive.

Les modules exécutent leurs appels par le SDK Scaleway :

```bash
pip install 'scaleway>=2.9.0'
```

## Modules

| module | ce qu'il fait |
|---|---|
| `stephrobert.scaleway.instance_server_info` | lit une Instance par son identifiant, ou liste une zone entière, toutes pages parcourues |
| `stephrobert.scaleway.instance_server_action` | allume, arrête, redémarre ou fige une Instance, et attend l'état visé |

`instance_server_action` accepte `poweron`, `poweroff`, `reboot` et
`stop_in_place`. Il **n'accepte pas** `terminate`, `backup` ni
`enable_routed_ip` : la première supprime l'Instance et ses volumes, la
deuxième crée une image, la troisième migre la pile réseau sans retour. Cette
collection exploite l'existant, elle ne provisionne pas.

## Inventaire dynamique

```yaml
# production.scaleway.yml
plugin: stephrobert.scaleway.scaleway
products:
  - instance
states:
  - running
group_by:
  - product
  - zone
  - tags
```

```bash
ansible-inventory -i production.scaleway.yml --graph
```

Le nom du fichier doit se terminer par `scaleway.yml` ou `scw.yml`, sinon
Ansible ignore la source. Les machines découvertes portent `scaleway_id`,
`scaleway_zone` et `scaleway_product`, ce qui suffit à enchaîner sur les
modules ci-dessus en `delegate_to: localhost`.

Le guide complet, avec le choix de `ansible_host` par réseau privé, les
collisions de noms et le piège d'Ansible sur le mode strict :
[docs/guides/inventaire-dynamique.md](../../../docs/guides/inventaire-dynamique.md).

## Playbooks livrés

Ils s'appellent par leur nom complet une fois la collection installée :

```bash
ansible-playbook stephrobert.scaleway.inventaire_serveurs -e zone=fr-par-1
ansible-playbook stephrobert.scaleway.detail_dun_serveur -e zone=fr-par-1
ansible-playbook stephrobert.scaleway.arreter_un_serveur -e zone=fr-par-1 -e server_id=<uuid>
```

Voir [playbooks/README.md](playbooks/README.md).

## Identifiants

Par l'environnement, par le fichier de configuration Scaleway, ou par les
paramètres du module, dans cet ordre de priorité :

```bash
export SCW_ACCESS_KEY=... SCW_SECRET_KEY=...
```

`SCW_API_URL` est honorée de bout en bout : pointer la collection vers un
émulateur local permet de l'exercer sans compte et sans dépense.

## Licence

GPL-3.0-or-later. Voir [LICENSE](LICENSE).
