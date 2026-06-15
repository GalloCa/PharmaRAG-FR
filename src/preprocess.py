# IMPORTS
import json 
import re
import os 
import pandas as pd 
from tqdm import tqdm

# CONSTANTS
# Mapping of SMPC (RCP) block index to section title - 
# is standardized across all BDPM entries
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

# Chunking parameters
MAX_WORDS = 500
OVERLAP_WORDS = 75

NOISE = [
    "sommaire", "imprimer", "ansm", "résumé des caractéristiques",  
    "sans objet", "à compléter", "liste i", "liste ii",
    "date de première autorisation", "date de dernier renouvellement",
    "médicament non soumis", "médicament soumis",
    "médicament réservé"
    ]

def clean_text(text):
    """
    Cleaning raw SmPCs text
    
    Input : 
        text (str) : the raw text of SmPC extradted from the BDPM website
    Return : 
        text (str) : the cleaned text, stripped of leading/trailing whitespace
    """
    if not text: 
        return ""
    
    # Remove invisible Unicode separators causing JSONL reading issues
    text = text.replace('\u2028', ' ').replace('\u2029', ' ')
    # Fix fragmented text (e.g., A\nB\nA\nC in acneed PDFs) 
    text = re.sub(r"([A-ZÉÀÈ])\n(?=[A-ZÉÀÈ])", r"\1", text)

    # Attempt to remove the table of contents - cut everything before "1.DENOMINATION"
    match_start = re.search(r"(?:\n|^)(?:#+\s*)?1\.\s*D[EÉ]NOMINATION", text, flags=re.IGNORECASE)
    if match_start:
        text = text[match_start.start():]

    # Clean up multiple spaces and newlines
    text = re.sub(r"[ \t]+", " ", text) 
    text = re.sub(r"\n{3,}", "\n\n", text) 

    return text.strip()

def split_long_chunk(chunk):
    """ Splits long chunks while eliminating micro-chunks """
    words = chunk["texte"].split()
    
    # Élimination des déchets de moins de 20 mots
    if len(words) < 20:
        return []
        
    if len(words) <= MAX_WORDS:
        return [chunk]
    
    sub_chunks = []
    step = MAX_WORDS - OVERLAP_WORDS

    for i, start in enumerate(range(0, len(words), step)):
        sub_text = " ".join(words[start:start + MAX_WORDS])
        
        # Filtre les reliquats de fin de découpage
        if len(sub_text.split()) < 20:
            continue
            
        sub_chunk = chunk.copy()
        sub_chunk["id"] = f"{chunk['id']}_part{i}"
        sub_chunk["texte"] = sub_text
        sub_chunks.append(sub_chunk)

    return sub_chunks

def deduplicate_rcp(jsonl_path, tsv_path):
    """
    Deduplicating SmPCs by keeping the most complete one per active substance

    Input :
        jsonl_path (str) : path to the raw JSONL file containing all scraped SmPCS
        tsv_path (str) : path to the TSV file containing BDPM metadata 
    Return : 
        deduplicated_rcp (list) : a list of dictionaries, each representing a unique and cleaned SmPC
    """

    print("Loading metadata for deduplication")
    # Linking CIS to active substance
    df_notices = pd.read_csv(tsv_path, sep="\t", dtype = str)
    # Clean empty substances to avoid errors
    df_notices["substances_actives"] = df_notices["substances_actives"].fillna("INCONNUE")
    cis_to_substance = dict(zip(df_notices["CIS"], df_notices["substances_actives"]))

    print("Reading and grouping by active substance")
    substance_groups = {}

    with open(jsonl_path, "r", encoding="utf-8", newline="\n") as f:
        for line in f:
            try:
                data= json.loads(line)
            except Exception:
                continue
            cis = data.get("CIS")
            rcp_text = data.get("rcp_text", "")

            # Skip empty RCP (SmPC)
            if not rcp_text.strip():
                continue
            
            substance = cis_to_substance.get(cis, f"INCONNUE_{cis}")

            if substance not in substance_groups:
                substance_groups[substance] = []
            
            substance_groups[substance].append({
                "CIS" : cis, 
                "denomination" : data.get("denomination", ""),
                "substance_active" : substance,
                "rcp_text" : rcp_text
             })
            
    print(f"Found {len(substance_groups)} unique active substances (generic groups).")

    deduplicated_rcp = []
    for substance, rcp_list in substance_groups.items():
        # Sorted by length (descending) and kee the richest one
        best_rcp = sorted(rcp_list, key=lambda x: len(x["rcp_text"]), reverse=True)[0]
        # Apply cleaning funtion on best candidate
        best_rcp["rcp_text"] = clean_text(best_rcp["rcp_text"])
        deduplicated_rcp.append(best_rcp)
    
    print(f"After deduplication : {len(deduplicated_rcp)} unique SmPCs retained for indexing")
    return deduplicated_rcp

def extract_clinical_subsections(content, rcp_data, section_index, default_title):
    """ Extract sub-sections (4.1, 4.2...) using a robust Multiline Regex """
    chunks = []
    
    pattern = re.compile(
        r"(4\.[1-9])[ \.\-\*]+(Indication|Posologie|Contre[\-\s]indication|Mises|Interaction|Fertil|Grossesse|Allaitement|Effet|Surdosage)", 
        re.IGNORECASE
    )
    matches = list(pattern.finditer(content))
    
    if not matches:
        return [{
            "id": f"{rcp_data['CIS']}_bloc_{section_index}",
            "CIS": rcp_data['CIS'],
            "denomination": rcp_data["denomination"],
            "substance_active": rcp_data["substance_active"],
            "section": str(section_index),
            "titre_section": default_title,
            "texte": content,
            "source": "RCP"
        }]

    for idx, match in enumerate(matches):
        sub_id = match.group(1) 
        start_pos = match.end() 
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        
        sub_content = content[start_pos:end_pos].strip()
        
        if len(sub_content.split()) > 15: 
            chunks.append({
                "id": f"{rcp_data['CIS']}_bloc_{sub_id.replace('.', '_')}",
                "CIS": rcp_data['CIS'],
                "denomination": rcp_data["denomination"],
                "substance_active": rcp_data["substance_active"],
                "section": sub_id,
                "titre_section": CLINICAL_SUB_SECTIONS.get(sub_id, f"Section {sub_id}"),
                "texte": sub_content,
                "source": "RCP"
            })
            
    return chunks

def chunk_semantic(rcp_data):
    """
    Semantic chunking based on the website separator "Redirection vers le haut de la page"

    Input : 
        rcp_data (dict) : a dictionary containing metadata and cleaned text of a single SmPC
    Return : 
        chunks (list) : a list of dictonaries, where each dictionarie representes a specific
                        semantic section (chunk) of the SmPC
    """
    text = rcp_data["rcp_text"]
    chunks = []

    # Using website "Redirection vers le haut de page" as separator to split text into logical blocks
    blocs = re.split(r"Redirection vers le haut de page", text, flags = re.IGNORECASE)

    # Fallback if no separator is found
    if len(blocs) <= 1 :
        chunk = {
            "id" : f"{rcp_data['CIS']}_complet",
            "CIS" : rcp_data["CIS"],
            "denomination" : rcp_data["denomination"],
            "substance_active" : rcp_data["substance_active"],
            "section" : "0",
            "titre_section": "Notice complètes",
            "texte" : text.strip(),
            "source" : "RCP"
        }
        return split_long_chunk(chunk)
    
    # Create a chunk for each semantic block found
    for i, bloc in enumerate(blocs):
        content = bloc.strip()

        first_line = content.split('\n')[0].lower() if content else ""
        is_noise = any(word in first_line for word in NOISE)

        # Ignore empty blocks or those containing just "Sans objet"
        if len(content) <= 50 or is_noise:
            continue
        
        section_title = RCP_TITLE.get(i, None)
        if section_title is None:
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            section_title = lines[0][:80] if lines else f"Section {i}"

        if re.search(r"4\.1[ \.\-\*]+Indication", content, re.IGNORECASE):
            clinical_chunks = extract_clinical_subsections(content, rcp_data, i, section_title)
            for c in clinical_chunks:
                chunks.extend(split_long_chunk(c))
            continue

        chunk = {
                "id": f"{rcp_data['CIS']}_bloc_{i}",
                "CIS" : rcp_data['CIS'],
                "denomination" : rcp_data["denomination"],
                "substance_active": rcp_data["substance_active"],
                "section" : f"{i}",
                "titre_section" : section_title,
                "texte" : content,
                "source" : "RCP"
                }

        chunks.extend(split_long_chunk(chunk))

    return chunks

def run_pipeline(jsonl_input, tsv_input, output_path):
    """
    Executing the full NLP preprocessing pipeline => Cleaning, Deduplication, Chunking

    Input : 
        jsonl_input (str) : path to the raw JSON file containing all scrapend SmPCs
        tsv_input (str) : path to the TSV file containing BDPM metadata
        output_path (str) : path where the final JSONL file containing the semantic chunks will be saved
    Return :
        None : the function saves the output directly to the specifies file path

    """
    print("\n STARTING NLP PREPROCESSING")

    deduplicated_data = deduplicate_rcp(jsonl_input, tsv_input)

    print("\nSemantic chunking of SmPCs")
    all_chunks = []

    for rcp in tqdm(deduplicated_data, desc="Processing texts", unit="doc"):
        chunks = chunk_semantic(rcp)
        all_chunks.extend(chunks)
    
    print(f"\nSuccessfully generatied {len(all_chunks)} semantic chunks ready for RAG")

    print(f"Saving file")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Done, external memory is saved in '{output_path}")

if __name__ == "__main__":
    RAW_JSONL = "data/raw/rcp_test_VMD.jsonl"
    NOTICE_TSV = "data/raw/notices_bdpm.tsv"
    OUTPUT_PATH = "data/processed/chunks_rcp.jsonl"

    if not os.path.exists(RAW_JSONL):
        print(f"ERROR: File {RAW_JSONL} not found. Check the path")
    elif not os.path.exists(NOTICE_TSV):
        print(f" ERROR: File {NOTICE_TSV}  not found. Check the path")
    else:
        run_pipeline(RAW_JSONL, NOTICE_TSV, OUTPUT_PATH)
            

