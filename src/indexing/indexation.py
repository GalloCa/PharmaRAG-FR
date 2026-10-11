import json
import os 
from pathlib import Path
from tqdm import tqdm 
import chromadb
from sentence_transformers import SentenceTransformer
from config import (EMBED_MODEL_NAME, 
                    EMBED_DEVICE,
                    BATCH_SIZE_ENCODE,
                    BATCH_SIZE_INDEX, 
                    CHROMA_DB_PATH, 
                    COLLECTION_NAME, 
                    CHUNKS_PATH)


def index_main():
    """
    
    """
    print(f"Testing embedding model loading")

    model = SentenceTransformer(EMBED_MODEL_NAME, device=EMBED_DEVICE)

    print(f"Testing ChromaDB persistent connection")
    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f" Existing collection '{COLLECTION_NAME}' purged.")
    except Exception:
        pass

    collection = client.create_collection(
        name = COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    print(f"Loading chunks from disk")
    with open(CHUNKS_PATH, mode = "r", encoding="utf8") as f:
        raw_chunks = [json.loads(line) for line in f]
    total_chunks = len(raw_chunks)
    print(f"Total chunks loaded: {total_chunks}")

    for i in tqdm(range(0, len(raw_chunks), BATCH_SIZE_INDEX), desc="Native indexing"):
        batch = raw_chunks[i : i + BATCH_SIZE_INDEX]

        # in-batch deduplication to avoir duplicate key errors during upsert
        seen_ids = set()
        clean_batch = []
        for chunk in batch:
            chunk_id = str(chunk["id"])
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                clean_batch.append(chunk)
        
        idx = [chunk["id"] for chunk in clean_batch]
        docs = [chunk["texte"] for chunk in clean_batch]
        metadatas = [{
            "CIS" : str(chunk["CIS"]),
            "denomination": chunk.get("denomination", ""),
            "substance_active" : chunk.get("substance_active", ""),
            "section" : str(chunk.get("section", "")),
            "titre_section" : chunk.get("titre_section", ""),
            "source" : chunk.get("source", "RCP"),
        } 
        for chunk in clean_batch
        ]

        # dense vector encoding with L2 normalization for cosine space
        embeddings = model.encode(
            docs,
            batch_size = BATCH_SIZE_ENCODE,
            normalize_embeddings=True, 
            show_progress_bar=False
        ).tolist()

        # insert or update vectors into collection
        collection.upsert(
            ids = idx, 
            documents = docs,
            metadatas = metadatas,
            embeddings = embeddings
        )

    print(f"Indexing complete. {collection.count()} chunks stored in '{COLLECTION_NAME}'")

if __name__== "__main__":
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    index_main()

        