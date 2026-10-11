# IMPORTS
import json 
import re
import os 
import pandas as pd 
from tqdm import tqdm

from config import MAX_WORDS, OVERLAP_WORDS, NOISE,  CLINICAL_PATTERN, CLINICAL_SUB_SECTIONS, RCP_TITLE, NOTICE_TSV_PATH, CHUNKS_PATH, RAW_DATA_PATH

def clean_text(text):
    if not text: 
        return ""
    
    text = text.replace('\u2028', ' ').replace('\u2029', ' ')
    text = re.sub(r"([A-ZÉÀÈ])\n(?=[A-ZÉÀÈ])", r"\1", text)

    match_start = re.search(r"(?:\n|^)(?:#+\s*)?1\.\s*D[EÉ]NOMINATION", text, flags=re.IGNORECASE)
    if match_start:
        text = text[match_start.start():]

    text = re.sub(r"[ \t]+", " ", text) 
    text = re.sub(r"\n{3,}", "\n\n", text) 
    return text.strip()

def split_long_chunk(chunk):
    words = chunk["texte"].split()
    
    if len(words) < 20:
        return []
        
    if len(words) <= MAX_WORDS:
        return [chunk]
    
    sub_chunks = []
    step = MAX_WORDS - OVERLAP_WORDS

    for i, start in enumerate(range(0, len(words), step)):
        sub_text = " ".join(words[start:start + MAX_WORDS])
        
        if len(sub_text.split()) < 20:
            continue
            
        sub_chunk = chunk.copy()
        sub_chunk["id"] = f"{chunk['id']}_part{i}"
        sub_chunk["texte"] = sub_text
        sub_chunks.append(sub_chunk)

    return sub_chunks

def deduplicate_rcp(jsonl_path, tsv_path):
    print("Loading metadata for deduplication")
    df_notices = pd.read_csv(tsv_path, sep="\t", dtype=str)
    df_notices["substances_actives"] = df_notices["substances_actives"].fillna("INCONNUE")
    cis_to_substance = dict(zip(df_notices["CIS"], df_notices["substances_actives"]))

    print("Reading and grouping by active substance")
    substance_groups = {}

    with open(jsonl_path, "r", encoding="utf-8", newline="\n") as f:
        for line in f:
            try:
                data = json.loads(line)
            except Exception:
                continue
            cis = data.get("CIS")
            rcp_text = data.get("rcp_text", "")

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

    deduplicated_rcp = []
    for substance, rcp_list in substance_groups.items():
        best_rcp = sorted(rcp_list, key=lambda x: len(x["rcp_text"]), reverse=True)[0]
        best_rcp["rcp_text"] = clean_text(best_rcp["rcp_text"])
        deduplicated_rcp.append(best_rcp)
    
    return deduplicated_rcp

def extract_clinical_subsections(content, rcp_data, section_index):
    chunks = []
    matches = list(CLINICAL_PATTERN.finditer(content))
    
    if not matches:
        return [{
            "id": f"{rcp_data['CIS']}_bloc_{section_index}_global",
            "CIS": rcp_data['CIS'],
            "denomination": rcp_data["denomination"],
            "substance_active": rcp_data["substance_active"],
            "section": str(section_index),
            "titre_section": "Données cliniques (Global)",
            "texte": content,
            "source": "RCP"
        }]

    for idx, match in enumerate(matches):
        sub_id = f"4.{match.group(1)}" 
        
        start_pos = match.start() 
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
    text = rcp_data["rcp_text"]
    chunks = []

    blocs = re.split(r"Redirection vers le haut de page", text, flags=re.IGNORECASE)

    if len(blocs) <= 1:
        chunk = {
            "id": f"{rcp_data['CIS']}_complet",
            "CIS": rcp_data["CIS"],
            "denomination": rcp_data["denomination"],
            "substance_active": rcp_data["substance_active"],
            "section": "0",
            "titre_section": "Notice complète",
            "texte": text.strip(),
            "source": "RCP"
        }
        return split_long_chunk(chunk)
    
    for i, bloc in enumerate(blocs):
        content = bloc.strip()

        first_line = content.split('\n')[0].lower() if content else ""
        is_noise = any(word in first_line for word in NOISE)

        if len(content) <= 50 or is_noise:
            continue
        
        matches = list(CLINICAL_PATTERN.finditer(content))
        if matches:
            clinical_chunks = extract_clinical_subsections(content, rcp_data, i)
            for c in clinical_chunks:
                chunks.extend(split_long_chunk(c))
            continue

        section_title = RCP_TITLE.get(i, None)
        if section_title is None:
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            section_title = lines[0][:80] if lines else f"Section {i}"

        chunk = {
                "id": f"{rcp_data['CIS']}_bloc_{i}",
                "CIS": rcp_data['CIS'],
                "denomination": rcp_data["denomination"],
                "substance_active": rcp_data["substance_active"],
                "section": f"{i}",
                "titre_section": section_title,
                "texte": content,
                "source": "RCP"
        }

        chunks.extend(split_long_chunk(chunk))

    return chunks

def run_pipeline(jsonl_input, tsv_input, output_path):
    print("\nSTARTING NLP PREPROCESSING")
    deduplicated_data = deduplicate_rcp(jsonl_input, tsv_input)

    print("\nSemantic chunking of SmPCs")
    all_chunks = []

    for rcp in tqdm(deduplicated_data, desc="Processing texts", unit="doc"):
        chunks = chunk_semantic(rcp)
        all_chunks.extend(chunks)
    
    print(f"\nSuccessfully generated {len(all_chunks)} semantic chunks ready for RAG")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    if not os.path.exists(RAW_DATA_PATH):
        print(f"ERROR: File {RAW_DATA_PATH} not found. Check the path.")
    elif not os.path.exists(NOTICE_TSV_PATH):
        print(f"ERROR: File {NOTICE_TSV_PATH} not found. Check the path.")
    else:
        run_pipeline(RAW_DATA_PATH, NOTICE_TSV_PATH, CHUNKS_PATH)