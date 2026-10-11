import chromadb
import ollama
import textwrap

import sys
from pathlib import Path
# ensure project root is in python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentence_transformers import SentenceTransformer
from config import( CHROMA_DB_PATH,
    COLLECTION_NAME,
    EMBED_MODEL_NAME,
    NORMALIZE_EMBEDDINGS,
    EMBED_DEVICE,
    LLM_MODEL_NAME,
    TEMPERATURE,
    TOP_K_DEFAULT)

_client = None
_collection = None
_embed_model = None

def _get_collection():
    """
    Retrieve or initialize the cached persistent ChromaDB collection.
    """
    global _client, _collection
    if _collection is None :
        _client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        _collection = _client.get_collection(name=COLLECTION_NAME)

    return _collection

def _get_embed_model():
    """
    Retrieve or initialize the cached SentenceTransformer emdebbing model.
    """
    global _embed_model
    if _embed_model is None: 
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME, device=EMBED_DEVICE)
    return _embed_model

def retrieve(query, top_k =TOP_K_DEFAULT, filtre_section: str | None = None):
    """
    Encode the query and retrieve the top-k nearest neighbor chunks from ChromaDB,
    with an optional metadata filter on the Smpc (RCP) section.
    """
    model = _get_embed_model()
    _collection = _get_collection()

    where_clause = {"section" : filtre_section} if filtre_section else None
    query_vector = model.encode([query], normalize_embeddings=NORMALIZE_EMBEDDINGS).tolist()

    return _collection.query(
        query_embeddings=query_vector,
        n_results= top_k,
        where = where_clause
    )

def build_context(results):
    """
    Format retrieved ChromaDB candidate chunks into a structured prompt context block
    """
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    
    if not documents:
        return ""
    
    elements = []
    for doc, meta in zip(documents, metadatas):
        elements.append(
            f"### {meta.get('denomination')} (CIS: {meta.get('CIS')}) \n"
            f"Section{meta.get('section')} - {meta.get('titre_section')} :\n"
            f"{doc}"
        )
    
    return "\n\n---\n\n".join(elements)

def build_prompt(query, context):
    """
    Assemble the contrained medical QA prompt with strict grounding guidelines.
    """

    prompt = f"""
    Tu es un assistant médical d'aide à la décision expert sur les RCP de la BDPM.
    Réponds à la question posée en te basant EXCLUSIVEMENT sur les extraits du Résumé des Caractéristiques du Produit (RCP) ci-dessous.

    Consignes impératives :
    1. Base-toi uniquement sur les faits décrits dans les extraits, sans rien extrapoler.
    2. Cite explicitement la dénomination exacte du médicament concerné.
    3. Mentionne impérativement la section ou rubrique source sous la forme formelle (ex: rubrique 4.1, rubrique 4.3).
    4. Si l'information n'est pas présente dans les extraits, réponds exactement : "La documentation fournie ne permet pas de répondre."

    Extraits RCP :
    {context}

    Question :
    {query}

    Réponse :
    """
    return textwrap.dedent(prompt.strip())

def generate(query, top_k=TOP_K_DEFAULT, filtre_section: str | None = None, model_name = LLM_MODEL_NAME):
    """
    End-to-end RAG inference: retrieve candidates, assemble prompt an generate answer via Ollama
    """
    
    results = retrieve(query, top_k=top_k, filtre_section=filtre_section)
    context = build_context(results)

    if not context:
        return "No documents found in the database for this query"

    prompt = build_prompt(query, context)
    
    answer = ollama.chat(
            model = model_name,
            messages=[{"role" : "user", "content" : prompt}],
            options = {"temperature" : TEMPERATURE, "num_predict" : 150},
            
        )
    
    return answer["message"]["content"]

