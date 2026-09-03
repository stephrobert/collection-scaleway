# La plateforme d'exemple, et ce qu'elle prouve

Ce répertoire porte une **plateforme complète** décrite en Terraform, et les
playbooks qui l'exploitent avec la collection. Elle n'existe pas pour faire
joli : elle est le banc sur lequel se prouve ce que la collection sait faire.

```text
examples/stack/       la plateforme, 25 types de ressources, 7 produits Scaleway
examples/playbooks/   l'inventaire, le déploiement, la vérification
```

## Ce que la plateforme contient

Trois étages, écrits comme un vrai projet et non comme une fixture :

* **deux VPC qui ne se parlent pas**, la gestion et la charge de travail ;
* **un bastion**, seule machine à porter une adresse publique ;
* **un tier web** sans adresse publique, exposé par un **load balancer** ;
* **un tier applicatif** sans adresse publique du tout, qui sort par une
  **passerelle publique** ;
* une **liste de contrôle** en refus par défaut sur le VPC de charge, des
  groupes de sécurité par étage, un **groupe de placement**, des **volumes de
  données**, un **instantané** et une **image d'or**, une **clé IAM**, et les
  adresses du tier web **réservées dans IPAM** avant que les machines les
  portent.

## Pourquoi cette forme, et pas un parc plat

Un parc où toutes les machines ont une adresse publique ne prouverait rien du
plugin d'inventaire. Ici, **quatre machines sur cinq n'en ont aucune** : les
joindre demande de lire IPAM, de le joindre aux cartes réseau, et de choisir
la bonne adresse dans le bon réseau privé. C'est exactement ce que ce plugin
fait mieux que l'officiel, et c'est vérifié à chaque exécution :

```text
machine        ansible_host   source         réseau privé
bastion        10.10.0.2      private_ipv4   [bastion]
web-1          10.20.0.2      private_ipv4   [web]
web-2          10.20.0.3      private_ipv4   [web]
worker-a       10.30.0.3      private_ipv4   [app]
worker-b       10.30.0.4      private_ipv4   [app]
```

## Deux cibles, une seule stack

`endpoint` renseigné vise l'émulateur, `endpoint` vide vise le vrai Scaleway.
Écrire deux stacks reviendrait à n'en prouver aucune : ce qui tourne contre
l'émulateur ne serait plus ce qui tourne contre le cloud.

C'est aussi ce qui fait de l'exercice un **test différentiel** de l'émulateur :
tout écart entre les deux exécutions est un défaut de l'émulateur, et se
remonte chez lui.

## Aucune ressource ne doit survivre

`terraform destroy` ne suffit pas comme garantie, et ce n'est pas une opinion :
un `apply` interrompu laisse un état partiel, et supprimer un serveur Scaleway
ne supprime pas son volume si personne ne le demande. Mesuré avant d'écrire
une ligne de cette stack : un volume de 10 Go, zéro référence, survivait déjà
à un serveur disparu sur le projet dédié.

`scripts/residue.py` prend une **référence** de ce que le compte contient
avant, la recompare après, et échoue si quoi que ce soit est apparu. Il refuse
aussi le cas inverse, une ressource préexistante qui aurait disparu, ce qui
serait plus grave qu'un résidu.
