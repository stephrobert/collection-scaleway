# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Stéphane Robert
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Le moteur de l'inventaire dynamique, hors du plugin lui-même.

Le plugin `plugins/inventory/scaleway.py` ne porte que le dialogue avec
Ansible. Tout ce qui décide vit ici, en couches qui se testent seules :

    config      lire et valider ce que l'utilisateur a demandé
    providers   traduire une API Scaleway en modèle normalisé
    network     indexer IPAM, réseaux privés et VPC, puis joindre
    address     choisir `ansible_host`, et savoir l'expliquer
    hostname    choisir `inventory_hostname`, et refuser les collisions
    groups      nommer les groupes, et assainir ces noms
    models      le modèle normalisé, seul objet qui traverse les couches
    errors      distinguer un droit refusé d'une panne et d'une absence
"""
