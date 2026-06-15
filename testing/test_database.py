from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

vectorstore = Chroma(
    collection_name="medrag-fr",
    embedding_function=embeddings,
    persist_directory="data/chroma_db"
)

# Vérifier le nombre de documents indexés
print(f"Documents dans ChromaDB : {vectorstore._collection.count()}")

# Tester une requête simple
results = vectorstore.similarity_search(
    "Quels sont les effets indésirables du paracétamol ?",
    k=3
)

print(f"\nTop 3 résultats pour 'effets indésirables paracétamol' :")
for i, doc in enumerate(results):
    print(f"\n[{i+1}] {doc.metadata['denomination']} — {doc.metadata['titre_section']}")
    print(f"     {doc.page_content[:200]}")