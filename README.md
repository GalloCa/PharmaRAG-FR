# PharmaRAG-FR

Pipeline de RAG appliqué aux résumés des caractéristiques du produit (RCP) issus de la Base de Données Publique des Médicaments (BDPM) française.


--- Projet en cours de finalisation --- (ce README reflète l'état actuel).

## Contexte

Ce projet d'initiation m'a permis d'explorer les défis spécifiques d'un pipeline RAG appliqué au domaine du biomédical.

Travailler sur ce corpus a mis en lumière plusieurs défis concrets : 
- **La structure et le bruit textuel** : parser des pages web et documents complexes sans perdre les rubriques clés.
- **Les limites des modèles NLP généralistes** : observer empiriquement la perte de performance des outils non adaptés (NER, plongements lexicaux vs denses) face au jargon médical.
- **La fiabilité clinique** : imposer des contraintes strictes aux modèles de langage afin qu'ils s'appuient exclusivement sur les passages récupérés et cite précisément ses sources.

## Pipeline

- **Scraping** :
- **Chunking sémantique**
- **Indexation** :
- **Génération** :

## NER : pourquoi pas un modèle prêt-à-l'emploi ? 

**Résultat**

Quelques exemples : 


**Conclusion** : les modèles NER généralistes n'ont pas de représentation adaptée au vocabulaire pharmacologique / médical.

## Comparaison des embeddings : sémantique vs lexicale

## Evaluation : 

**En cours**


## Extensions futures (non implémentées)

- **Base structurée (MySQL)** :
- **Fine-tuning NER biomédical** :

## Stack technique

Python · ChromaDB · sentence-transformers · spaCy · Hugging Face Transformers · Ollama (Mistral) · MySQL *(prévu)*

## Références

- Lewis et al. (2020), *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*
- Xiong, G., Jin, Q., Lu, Z., & Zhang, A. (2024). *Benchmarking Retrieval-Augmented Generation for Medicine*. Findings of the Association for Computational Linguistics: ACL 2024, 6233–6251. [arXiv:2402.13178](https://arxiv.org/abs/2402.13178) / [ACL Anthology](https://aclanthology.org/2024.findings-acl.372/)
- Corpus QUAERO (annotations biomédicales françaises, format BRAT)
- Principes FAIR pour la gestion de données de recherche





