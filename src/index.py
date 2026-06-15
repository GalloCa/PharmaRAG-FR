print("ALLO")
# IMPORTS
import json
import os 

try: 
    from tqdm import tqdm
    from langchain_core.documents import Document
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    print("import ok")
except ImportError as e:
    print(f"erreur d'import : manque {e}")
    exit()

JSONL_PATH = "data/processed/chunks_rcp.jsonl"
CHROMA_PATH = "data/chroma_db"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

def load_documents(file_path):
    docs = []
    with open(file_path, "r", encoding="utf-8") as f :
        for line in f:
            chunk = json.loads(line)

            doc = Document(
                page_content = chunk["texte"],
                metadata={
                    "id" : chunk["id"],
                    "CIS" : chunk["CIS"],
                    "denomination" : chunk["denomination"],
                    "substance_active" : chunk["substance_active"],
                    "section" : chunk["section"],
                    "titre_section" : chunk["titre_section"],
                    "source" : chunk["source"]
                }
            )
            docs.append(doc)
    
    return docs

def main():
    print("Step 1: Loading JSONL data")
    documents = load_documents(JSONL_PATH)
    print(f"{len(documents)} chunks loaded in memory")

    print(f"\nStep 2: Initializing AI model ({MODEL_NAME}), the first time can be a bit long")
   
    embeddings = HuggingFaceEmbeddings(
       model_name = MODEL_NAME,
       model_kwargs = {'device' : 'cpu'},
       encode_kwargs = {'normalize_embeddings' : True}
    )

    print("\nStep 3: Creating ChromaDB vectorial database")

    vectorstore = Chroma(
        collection_name= "medrag-fr",
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH
    )

    BATCH_SIZE = 1000

    for i in tqdm(range(0, len(documents), BATCH_SIZE), desc="Vector indexing"):
        batch = documents[i : i + BATCH_SIZE]
        vectorstore.add_documents(documents=batch)

    print(f"\nDone, database saved ine the file : '{CHROMA_PATH}")
    
if __name__ == "__main__":
    print("testing")
    os.makedirs(CHROMA_PATH, exist_ok=True)
    main()