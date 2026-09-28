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

- **Scraping** : ~ 10 000 RCP collectés depuis la BDPM
- **Chunking sémantique** : ~43 000 chunks propres, découpés par rubrique
- **Indexation** :
- **Génération** : recherche vectorielle -> prompt contrait -> Ollama (Mistral), avec obligation de citer la dénomination exacte et la rubrique source, et de ne pas répondre si l'information est absente du contexte

## NER : pourquoi pas un modèle prêt-à-l'emploi ? 
A remplir avec mes données 

**Résultat**

Quelques exemples : 


**Conclusion** : les modèles NER généralistes n'ont pas de représentation adaptée au vocabulaire pharmacologique / médical.

## Comparaison des embeddings : sémantique vs lexicale

## Evaluation : 

**En cours**


## Extensions futures (non implémentées)

- **Base structurée (MySQL)** : table de métadonnées liées aux chunks vectoriels pour un retrieval hybride (filtrage SQL + recherche sémantique)
- **Fine-tuning NER biomédical** : Entraineemnt sur le corpus QUAERO pour dépasser les limites identifiées

## Structure du dépot
```
pharmarag-fr/
├── config.py                   # Constantes globales, chemins Pathlib, hyperparamètres
├── src/
│   ├── scraping/
│   │   ├── fetch_bdpm.py       # Téléchargment 
│   │   └── fetch_rcp.py        # Scraping HTML
│   ├── chunking/
│   │   └── preprocess.py       # Nettoyage et segmentation sémantique par rubrique 
│   ├── indexing/
│   │   └── index.py            # Indexation ChromaDB + SenntenceTransformer   
│   ├── generation/
│   │   └── rag.py              # Pipeline prompt
│   └── evaluation/
│       └── evaluate.py         # métriques d'évaluation
├── notebooks/
│   └── test_database.ipynb
├── data/
│   ├── raw/                    # Fichiers bruts BDPM et notices non traitées
│   ├── processed/              # Fichier chunks
│   └── chroma_db/              #  Dossier persistant ChromaDB (exclu par gitignore)
├── requirements.txt
└── README.md
└── README.fr (version FR du README)
```

## Stack technique

Python · ChromaDB · sentence-transformers · spaCy · Hugging Face Transformers · Ollama (Mistral) · MySQL *(prévu)*

## Références

- Lewis et al. (2020), *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*
- Xiong, G., Jin, Q., Lu, Z., & Zhang, A. (2024). *Benchmarking Retrieval-Augmented Generation for Medicine*. Findings of the Association for Computational Linguistics: ACL 2024, 6233–6251. [arXiv:2402.13178](https://arxiv.org/abs/2402.13178) / [ACL Anthology](https://aclanthology.org/2024.findings-acl.372/)
- Corpus QUAERO (annotations biomédicales françaises, format BRAT)
- Principes FAIR pour la gestion de données de recherche





