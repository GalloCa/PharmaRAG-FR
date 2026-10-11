# PharmaRAG-FR

Pipeline de RAG appliqué aux résumés des caractéristiques du produit (RCP) issus de la Base de Données Publique des Médicaments (BDPM) française.

> **Projet en cours de finalisation** - ce README reflète l'état actuel du dépôt.

## Contexte

Ce projet d'initiation explore la capacité des grands modèles de langue à générer des réponses médicales précises et sourcées à partir de textes réglementaires officiels en français. En s'appuyant sur une architecture RAG, il interroge la fidélité de la génération aux sources et l'impact de la structure discursive des RCP sur la qualité du retrieval.

Travailler sur ce corpus a mis en lumière plusieurs défis concrets : 

- **La structure et le bruit textuel** : parser des pages web et documents complexes sans perdre les rubriques clés.
- **Les limites des modèles NLP généralistes** : observer empiriquement la perte de performance des embedding non spécialisés face au jargon pharmaceutique. 
- **La fiabilité clinique** : imposer des contraintes strictes aux LLM afin qu'ils s'appuient exclusivement sur les passages récupérés et citent précisément leurs sources, et de ne pas répondre si l'information est absente du contexte.

## Pipeline

| Étape | Description | Volume |
|-------|-------------|--------|
| **Scraping** | Collecte des RCP depuis la BDPM (HTML → Markdown) | ~10 000 RCP |
| **Chunking sémantique** | Nettoyage, déduplication par substance active, découpage par rubrique | ~43 000 chunks |
| **Indexation** | Vectorisation avec `paraphrase-multilingual-mpnet-base-v2`, stockage ChromaDB | 43 094 chunks |
| **Génération** | Retrieval vectoriel → prompt contraint → Ollama (Mistral, temperature=0.0)   | — |


## NER : pourquoi pas un modèle prêt-à-l'emploi ? 

Trois modèles ont été testés sur 50 chunks issus des rubriques contre-indications (4.3) et effets indésirables (4.8).

### Modèles testés 

| Modèle | Type | Résultat |
|--------|------|---------|
| `spaCy fr_core_news_lg` | Généraliste FR | Détecte des entités hors-sujet : `LOC` pour "Malabsorption", `PER` pour "Stevens-Johnson", `LOC` pour "Agence" |
| `Jean-Baptiste/camembert-ner` | Généraliste FR | Classe "vitamine A" comme `LOC`, "Agence nationale" comme `ORG` — pas d'entités pharmaceutiques |
| `d4data/biomedical-ner-all` | Biomédical EN | Détecte des symptômes (`Sign_symptom`) mais fragmente les tokens et produit des entités parasites sur des sous-mots |

**Note** : CamemBERT-bio-base est un encodeur biomédical français pré-entraîné (Labrak et al., 2023) mais sans tête de classification NER. Il est utilisé dans ce projet pour l'indexation mais sans fine-tuning supervisé sur corpus annoté il n'est pas utilisable en NER.

### Observations 

**spaCy** confond des termes médicaux avec des entités géographiques ou des personnes : "Malabsorption" → `LOC` ; "Stevens-Johnson" → `PER`.
Les 30 entités `MISC` détectées sont quasi toutes des artefacts.

**CamemBERT-ner** ne détecte aucune entité pharmaceutique pertinentes : substances actives, dénominations et codes CIS sont invisibles pour ce modèle.

**d4data/biomedical-ner-all** est entraîné en anglais, il détecte des symptômes génériques mais fragmente les tokens français (`##ille`, `##nse`) et produit des scores faibles et incohérents.

### Conclusion

Aucun modèle généraliste ne reconnait les entités clés des RCP : dénominations de spécialités, substance actives, codes CIS, dosages pharmaceutiques. Un fine-tuning sur corpus biomédical français annoté (comme QUAERO) est nécessaire pour obtenir un NER exploitable.

## Evaluation : 

### Protocole

Benchmark manuel de 10 questions cliniques couvrant 6 rubriques RCP :

- indication thérapeutiques (4.1),
- posologie (4.2),
- contre-indications (4.3),
- interactions médicamenteuses (4.5),
- fertilité/grossesse/allaitement (4.6),
- effets indésirables (4.8)
  
pour 4 substances actives :
- paracétamol,
- abacavir,
- aspirine,
- warfarine/tramadol

**Métriques**

- **Hit@k** : au moins un chunk correct dans les k résultats
- **Precision@k** : proportion de chunks corrects parmi les k résultats
- **MRR** (*Mean Reciprocal Rank*) : position du premier chunk correct
- **Ancrage nominal** : la dénomination attendue est citée dans la réponse
- **Traçabilité nosologique** : la rubrique attendue est mentionnée dans la réponse

### Résultats (V1 - retrieval vectoriel dense)

| Métrique | Score |
|----------|-------|
| Hit@5 moyen | 50% |
| Precision@5 moyenne | 18% |
| MRR moyen | 0.333 |
| Ancrage nominal | 80% |
| Traçabilité nosologique | 10% |
| Temps moyen de génération | 3.6 s |

### Interprétation 

Les 5 questions avec Hit@5 = 1.0 concernent les substances dont le nom commercial est connu ou dont la section est filtrée explicitement. Les 5 échecs partagent une cause commune : l'absence de correspondance DCI ↔ spécialité commerciale.

Exemples observés : 

| DCI (requête) | Spécialité dans la BDPM |
|---------------|------------------------|
| warfarine | COUMADINE |
| tramadol | CONTRAMAL |
| aspirine | ASPIRINE PROTECT |
| paracétamol | PARACETAMOL AGUETTANT |

Le modèle d'embedding généraliste ne capture pas ces équivalences. Une requête sur "warfarine" ne retrouve pas les chunks "COUMADINE". Ce résultat documente empiriquement une limite structurelle du retrieval vectoriel pur sur corpus pharmaceutique français.

La faible traçabilité nosologique (10%) indique que le LLM ne mentionne pas spontanément les rubriques RCP dans ses réponses. Une contrainte explicite dans le prompt est prévue dans une version V2.

### Limitations

Le benchmark V1 inclut le nom commercial entre parenthèses dans certaines requêtes et un filtre de section pour compenser l'absence de table de correspondance DCI ↔ spécialité. Ces résultats constituent un plafond de performance dans des conditions favorables.

L'évaluation ne dispose pas de vérité terrain annotée par des experts. Les métriques de génération (faithfulness, answer relevance) prévues en V2 nécessiteront un juge LLM ou une annotation humaine.

La BDPM indexe par spécialité commerciale et non par DCI, toute requête formulée en DCI sans correspondance explicite est structurellement défavorisée.


## Extensions futures 

- **Couche SQL(MySQL)** : table de correspondance DCI ↔ spécialité commerciales liée aux chunks vectoriels pour un retrieval hybride (filtrage SQL + recherche sémantique)
- **BM25** : comparaison retrieval lexical vs dense sur le même benchmark.
- **Fine-tuning** : spécialisation des modèles sur corpus biomédical français. Embeddings (CamemBERT-bio sur RCP) et NER (entraînement sur QUAERO) pour essayer de dépasser les limites des modèles généralistes identifiées lors de l'évaluation.
- **Evaluation V2** : faithfulness et answer relevance via LLM-as-judge
- **Refactorisation POO**


## Structure du dépot
```
pharmarag-fr/
├── config.py                   # Constantes globales, chemins Pathlib, hyperparamètres
├── src/
│   ├── scraping/
│   │   ├── fetch_bdpm.py       # Téléchargement 
│   │   └── fetch_rcp.py        # Scraping HTML
│   ├── chunking/
│   │   └── preprocess.py       # Nettoyage et segmentation sémantique par rubrique 
│   ├── indexing/
│   │   └── indexation.py            # Indexation ChromaDB + SentenceTransformer   
│   ├── generation/
│   │   └── rag.py              # Pipeline prompt
│   └── evaluation/
│       └── evaluation.py         # métriques d'évaluation
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





