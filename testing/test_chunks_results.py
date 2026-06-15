import json

noms_uniques = set()

with open("data/processed/chunks_rcp.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        
        # Si la ligne contient une liste de chunks
        if isinstance(data, list):
            for chunk in data:
                noms_uniques.add(chunk.get("denomination", "Inconnu"))
        
        # Si la ligne est directement un dictionnaire (chunk unique)
        elif isinstance(data, dict):
            noms_uniques.add(data.get("denomination", "Inconnu"))

print(f"J'ai bien {len(noms_uniques)} médicaments uniques découpés dans ce fichier !")