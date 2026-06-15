import json
import re

print("🔍 INSPECTION DE LA SECTION 4 🔍\n")

# Assure-toi que le chemin correspond à ton fichier RAW
with open("data/raw/rcp_test_VMD.jsonl", "r", encoding="utf-8") as f:
    count = 0
    for line in f:
        try:
            data = json.loads(line)
            texte = data.get("rcp_text", "")
            blocs = re.split(r"Redirection vers le haut de page", texte, flags=re.IGNORECASE)
            
            # Si le médicament a bien au moins 4 blocs
            if len(blocs) > 4:
                print(f"--- {data.get('denomination', 'Inconnu')} ---")
                # repr() nous montre la stricte réalité (les \n, les \t, les * etc.)
                print(repr(blocs[4][:400])) 
                print("\n" + "="*50 + "\n")
                count += 1
                
            if count >= 3:
                break
        except:
            continue