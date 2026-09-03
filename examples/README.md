# La plateforme d'exemple, et ce qu'elle prouve

Ce répertoire porte une **plateforme complète** décrite en Terraform, et les
playbooks qui l'exploitent avec la collection. Elle n'existe pas pour faire
joli : elle est le banc sur lequel se prouve ce que la collection sait faire.

```text
examples/stack/       la plateforme, 7 produits Scaleway
examples/playbooks/   l'inventaire, le déploiement, la vérification
```

## Ce que la plateforme contient

Trois étages, écrits comme un vrai projet et non comme une fixture :

* **un VPC avec `enable_routing`**, et trois réseaux privés dedans : gestion,
  web, applicatif ;
* **un bastion**, seule machine à porter une adresse publique, et seule porte
  d'entrée ;
* **un tier web** sans adresse publique, exposé par un **load balancer** ;
* **un tier applicatif** sans adresse publique du tout, qui sort par une
  **passerelle publique** ;
* une **liste de contrôle** en refus par défaut sur le VPC, des groupes de
  sécurité par étage, un **groupe de placement**, des **volumes Block Storage**,
  un **instantané** et une **image d'or**, et les adresses du tier web
  **réservées dans IPAM** avant que les machines les portent.

**Un VPC et non deux, et c'est une correction plutôt qu'une simplification.**
La première version copiait la stack d'exemple de feint : deux VPC qui ne
partagent aucun réseau, le bastion dans l'un, les tiers dans l'autre. Elle
valide, elle s'applique, elle se détruit, et elle ne peut pas marcher, parce
que rien ne relie les deux. Le défaut ne se voyait pas chez feint, dont la
stack ne démarre aucune machine et éprouve le plan de contrôle seul.

## Pourquoi cette forme, et pas un parc plat

Un parc où toutes les machines ont une adresse publique ne prouverait rien du
plugin d'inventaire. Ici, **quatre machines sur cinq n'en ont aucune** : les
joindre demande de lire IPAM, de le joindre aux cartes réseau, et de choisir
la bonne adresse dans le bon réseau privé. C'est exactement ce que ce plugin
fait mieux que l'officiel, et c'est vérifié à chaque exécution. Mesuré sur le
cloud réel :

```text
machine        ansible_host   source         réseau privé
bastion        10.10.0.2      private_ipv4   [gestion]
web-1          10.20.0.3      private_ipv4   [web]
web-2          10.20.0.2      private_ipv4   [web]
worker-a       10.30.0.4      private_ipv4   [app]
worker-b       10.30.0.2      private_ipv4   [app]
```

## Trois cibles, une seule stack

```bash
mise run example            # l'émulateur, plan de contrôle seul, hors ligne
mise run example:machines   # l'émulateur avec de vraies machines (incus-ovn)
mise run example:reel       # le compte Scaleway réel, facturé
```

Seul `endpoint` change : renseigné, il vise l'émulateur ; vide, il vise le vrai
Scaleway. Écrire deux stacks reviendrait à n'en prouver aucune, puisque ce qui
tourne contre l'émulateur ne serait plus ce qui tourne contre le cloud.

C'est aussi ce qui fait de l'exercice un **test différentiel** de l'émulateur :
tout écart entre les deux exécutions est un défaut de l'émulateur, et se
remonte chez lui.

## Ce que chaque cible ne prouve pas

Un vert doit se lire sans aller chercher ailleurs ce qu'il vaut.

| cible | ce qu'elle prouve | ce qu'elle ne peut pas prouver |
|---|---|---|
| `example` | la stack s'applique, l'inventaire retrouve les 5 machines, 12 contrôles sur le plan de contrôle | rien de ce qui tourne dans les machines |
| `example:machines` | les playbooks se connectent, l'inventaire joint par adresse privée | le filtrage et le routage |
| `example:reel` | tout, y compris l'ACL, le routage, et la chaîne HTTP complète | |

L'émulateur **n'applique pas les ACL de VPC** : il l'écrit lui-même, une ACL y
est un enregistrement et non un filtre de paquets. Il ne pousse pas non plus de
route par défaut. Toute la classe des défauts de filtrage et de routage lui est
donc invisible, et cinq d'entre eux ne sont sortis que du run réel : ports
source d'ACL inertes, ACL sans état, sortie qui réautorise le VPC,
`push_default_route` qui écrase la route publique du bastion, et la chaîne
`b_ssd` retiré puis instantané d'une racine SBS.

L'image d'or n'est bâtie que par `example:reel` : l'émulateur crée l'instantané
par l'API Block puis rend 404 sur le même identifiant côté Instance (feint#651).
Le contrôle ne se tait pas pour autant, il **exige l'absence** de l'image.

## Aucune ressource ne doit survivre

`terraform destroy` ne suffit pas comme garantie, et ce n'est pas une opinion :
un `apply` interrompu laisse un état partiel, et supprimer un serveur Scaleway
ne supprime pas son volume si personne ne le demande. Mesuré avant d'écrire
une ligne de cette stack : un volume de 10 Go, zéro référence, survivait déjà
à un serveur disparu sur le projet dédié.

`scripts/residue.py` prend une **référence** de ce que le compte contient
avant, la recompare après, et échoue si quoi que ce soit est apparu. Il refuse
aussi le cas inverse, une ressource préexistante qui aurait disparu, ce qui
serait plus grave qu'un résidu. Un échec de `scw` y est une erreur et jamais un
zéro : une commande muette ne prouve pas qu'il ne reste rien, elle prouve qu'on
ne sait pas.

La destruction est dans un `finally`, donc elle part aussi quand un playbook
échoue et quand on interrompt.
