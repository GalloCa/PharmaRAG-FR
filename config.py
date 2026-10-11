from pathlib import Path
import re

# PATHS 
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "rcp_complet.jsonl"
NOTICE_TSV_PATH = BASE_DIR / "data" / "raw" / "notices_bdpm.tsv"
CHUNKS_PATH = BASE_DIR / "data" / "processed" / "chunks_rcp.jsonl"
CHROMA_DB_PATH = BASE_DIR / "data" / "chroma_db"

# SCRAPING
BDPM_BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr"
BDPM_BASE_URL_DOWNLOAD ="https://base-donnees-publique.medicaments.gouv.fr/download/file/"
SCRAPING_PAUSE = 1.5
SCRAPING_USER_AGENT = "Mozilla/5.0 (compatible; pharmarag-fr/1.0; research)"


FILES= {
    "medicaments" : "CIS_bdpm.txt",
    "compositions" : "CIS_COMPO_bdpm.txt",
    "presentations" : "CIS_CIP_bdpm.txt",
    "generiques" : "CIS_GENER_bdpm.txt",
    "info_importantes": "CIS_InfoImportantes_bdpm.txt",
}

ROWS = {
    "medicaments" : [
        "CIS", "denomination", "forme_pharma", "voie_admin",
        "statut_AMM", "type_procedure", "etat_commercialisation",
        "date_AMM", "statut_BdM", "num_autorisation_europeenne", 
        "titulaires", "surveillance_renforcee"
    ],
    "compositions" : [
        "CIS", "designation_element", "code_substance",
        "denomination_substance", "dosage", "ref_dosage",
        "nature_composant", "num_liaison"
    ],
    "presentations" : [
        "CIS", "CIP7", "libelle", "statut_admin", "etat_commercialisation",
        "date_declaration", "CIP13", "agrement_collectivites", 
        "taux_remboursement", "prix", "indic_remboursement", 
        "info_importantes"
    ],
    "generiques" : [
        "id_groupe_generique", "libelle_groupe_generique", "CIS",
        "type_generique", "numero_tri"
    ],
    "info_importantes" : [ 
        "CIS", "date_debut_info", "date_fin_info", "text_info"
    ]
}


# CHUNKING 
MAX_WORDS = 500
OVERLAP_WORDS = 75
MIN_WORDS = 20

RCP_TITLE = {
    1 : "Dénomination",
    2 : "Composition",
    3 : "Forme pharmaceutique",
    4 : "Indications / Posologie",
    5 : "Données précliniques",
    6 : "Données pharmaceutiques",
    7 : "Titulaire AMM",
    8 : "Numéro AMM"
}

CLINICAL_SUB_SECTIONS = {
    "4.1": "Indications thérapeutiques",
    "4.2": "Posologie et mode d'administration",
    "4.3": "Contre-indications",
    "4.4": "Mises en garde spéciales",
    "4.5": "Interactions",
    "4.6": "Fertilité, grossesse et allaitement",
    "4.7": "Effets sur l'aptitude à conduire",
    "4.8": "Effets indésirables",
    "4.9": "Surdosage"
}

CLINICAL_PATTERN = re.compile(
    r"(?:^|\n)[ \t#\*]*4[\.\\]+\s*([1-9]).{0,30}?(?:Indication|Posolog|Contre|Mise|Interaction|Fertilit|Grossesse|Allaitement|Effet|Surdosage)",
    re.IGNORECASE | re.DOTALL
)
NOISE = [
    "sommaire", "imprimer", "ansm", "résumé des caractéristiques",  
    "sans objet", "à compléter", "liste i", "liste ii",
    "date de première autorisation", "date de dernier renouvellement",
    "médicament non soumis", "médicament soumis",
    "médicament réservé"
]

#  ChromaDB
COLLECTION_NAME = "pharmarag-fr"

# EMBEDDING MODEL 
EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
EMBED_DEVICE = "cpu"
NORMALIZE_EMBEDDINGS = True

# LLM 
LLM_PROVIDER = "ollama"
LLM_MODEL_NAME = "mistral"
TEMPERATURE = 0.0

# RETRIVAL
TOP_K_DEFAULT = 3
BATCH_SIZE_INDEX = 256
BATCH_SIZE_ENCODE = 64


# BENCHMARK

BENCHMARK_QUESTIONS = [
    {
        "id": "eval_01",
        "query": "Quelles sont les contre-indications absolues du paracétamol ?",
        "expected_cis": [],
        "expected_denomination": "PARACETAMOL",
        "expected_section": "4.3",
        "top_k": 5,
        "filtre_section": "4.3"
    },
    {
        "id": "eval_02",
        "query": "Quel dépistage génétique est obligatoire avant d'initier l'abacavir ?",
        "expected_cis": ["61876780"],
        "expected_denomination": "ABACAVIR",
        "expected_section": "4.1",
        "top_k": 5,
        "filtre_section": "4.1"
    },
    {
        "id": "eval_03",
        "query": "Quelle est la posologie usuelle recommandée du paracétamol chez l'adulte ?",
        "expected_cis": ["66534880"],
        "expected_denomination": "PARACETAMOL AGUETTANT",
        "expected_section": "4.2",
        "top_k": 5,
        "filtre_section": "4.2"
    },
    {
        "id": "eval_04",
        "query": "Quelles sont les manifestations cliniques d'hypersensibilité à l'abacavir ?",
        "expected_cis": ["61876780"],
        "expected_denomination": "ABACAVIR",
        "expected_section": "4.8",
        "top_k": 5,
        "filtre_section": "4.8"
    },
    {
        "id": "eval_05",
        "query": "Peut-on prescrire de l'aspirine (Aspirine Protect) ou des AINS au cours du troisième trimestre de grossesse ?",
        "expected_cis": ["61464022"],
        "expected_denomination": "ASPIRINE PROTECT",
        "expected_section": "4.6",
        "top_k": 5,
        "filtre_section": "4.6"
    },
    {
        "id": "eval_06",
        "query": "Dans quelles indications le traitement par abacavir est-il prescrit ?",
        "expected_cis": ["61876780"],
        "expected_denomination": "ABACAVIR",
        "expected_section": "4.1",
        "top_k": 5,
        "filtre_section": "4.1"
    },
    {
        "id": "eval_07",
        "query": "Quelles sont les interactions médicamenteuses majeures de la warfarine (Coumadine) ?",
        "expected_cis": ["64631925"],
        "expected_denomination": "COUMADINE",
        "expected_section": "4.5",
        "top_k": 5,
        "filtre_section": "4.5"
    },
    {
        "id": "eval_08",
        "query": "Quels sont les effets indésirables cutanés sévères du tramadol (Contramal) ?",
        "expected_cis": ["60477650"],
        "expected_denomination": "CONTRAMAL",
        "expected_section": "4.8",
        "top_k": 5,
        "filtre_section": "4.8"
    },
    {
        "id": "eval_09",
        "query": "Quelles sont les contre-indications liées à la fonction hépatique pour le tramadol (Contramal) ?",
        "expected_cis": ["60477650"],
        "expected_denomination": "CONTRAMAL",
        "expected_section": "4.3",
        "top_k": 5,
        "filtre_section": "4.3"
    },
    {
        "id": "eval_10",
        "query": "Quel suivi ou adaptation posologique est requis pour la warfarine (Coumadine) selon l'INR ?",
        "expected_cis": ["64631925"],
        "expected_denomination": "COUMADINE",
        "expected_section": "4.2",
        "top_k": 5,
        "filtre_section": "4.2"
    }
]

# EVALUATION
EVAL_OUTPUT_PATH = BASE_DIR / "data" / "evaluation" / "results.jsonl"
BENCHMARK_PATH = BASE_DIR / "data" / "evaluation" / "benchmark_questions.json"
BENCHMARK_N_QUESTIONS = 10     
BENCHMARK_SECTIONS = ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.8", "4.9"]  
EVAL_TOP_K = 5            

