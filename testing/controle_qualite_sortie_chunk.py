import json

with open("data/processed/chunks_rcp.jsonl", encoding="utf-8") as f:
    chunks = [json.loads(line) for line in f]

# Distribution des titres détectés
from collections import Counter
titres = Counter(c["titre_section"] for c in chunks)
print("Top 15 titres :")
for titre, n in titres.most_common(15):
    print(f"  {titre:30s} : {n}")

# Taille des chunks
longueurs = [len(c["texte"].split()) for c in chunks]
print(f"\nLongueur moyenne : {sum(longueurs)//len(longueurs)} mots")
print(f"Min : {min(longueurs)} mots")
print(f"Max : {max(longueurs)} mots")

# Exemple d'un chunk
print("\nExemple chunk :")
print(chunks[10])


import json
import re

with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data["CIS"] == "61876780":
            text = data["rcp_text"]
            n_sep = len(re.findall(r"Redirection vers le haut de page", text, re.IGNORECASE))
            print(f"Séparateurs AVANT clean_text : {n_sep}")
            
            # Simuler clean_text
            text2 = text.replace('\u2028', ' ').replace('\u2029', ' ')
            text2 = re.sub(r"([A-ZÉÀÈ])\n(?=[A-ZÉÀÈ])", r"\1", text2)
            match_start = re.search(r"(?:\n|^)(?:#+\s*)?1\.\s*D[EÉ]NOMINATION", text2, re.IGNORECASE)
            if match_start:
                text2 = text2[match_start.start():]
            n_sep2 = len(re.findall(r"Redirection vers le haut de page", text2, re.IGNORECASE))
            print(f"Séparateurs APRÈS clean_text : {n_sep2}")
            break



with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data["CIS"] == "61876780":
            text = data["rcp_text"]
            
            # Tester le split tel quel
            blocs = re.split(r"Redirection vers le haut de page", text, flags=re.IGNORECASE)
            print(f"Nombre de blocs : {len(blocs)}")
            
            # Regarder le texte brut autour du premier séparateur
            idx = text.lower().find("redirection vers le haut de page")
            print(f"\nContexte autour du 1er séparateur :")
            print(repr(text[idx-50:idx+80]))
            break



import json
import re
import pandas as pd

# Reproduire exactement ce que fait deduplicate_rcp
df = pd.read_csv("data/raw/notices_bdpm.tsv", sep="\t", dtype=str)
df["substances_actives"] = df["substances_actives"].fillna("INCONNUE")
cis_to_substance = dict(zip(df["CIS"], df["substances_actives"]))

substance_groups = {}
with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        cis = data.get("CIS")
        rcp_text = data.get("rcp_text", "")
        if not rcp_text.strip():
            continue
        substance = cis_to_substance.get(cis, f"INCONNUE_{cis}")
        if substance not in substance_groups:
            substance_groups[substance] = []
        substance_groups[substance].append({
            "CIS": cis,
            "rcp_text": rcp_text
        })

# Prendre Abacavir
substance_abacavir = "ABACAVIR, SULFATE D'ABACAVIR"
rcp_list = substance_groups.get(substance_abacavir, [])
print(f"Nombre de génériques pour Abacavir : {len(rcp_list)}")

best = sorted(rcp_list, key=lambda x: len(x["rcp_text"]), reverse=True)[0]
print(f"CIS retenu : {best['CIS']}")
print(f"Longueur brute : {len(best['rcp_text'])} caractères")

# Compter les séparateurs avant et après clean_text
n_avant = len(re.findall(r"Redirection vers le haut de page", best["rcp_text"], re.IGNORECASE))
print(f"Séparateurs avant clean_text : {n_avant}")

# Appliquer clean_text manuellement
from preprocess import clean_text
texte_propre = clean_text(best["rcp_text"])
n_apres = len(re.findall(r"Redirection vers le haut de page", texte_propre, re.IGNORECASE))
print(f"Séparateurs après clean_text : {n_apres}")
print(f"\nDébut du texte après clean_text :")
print(repr(texte_propre[:300]))

import json

cis_set = set()
with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("rcp_text", "").strip():
                cis_set.add(data["CIS"])
        except:
            pass

print(f"CIS avec rcp_text non vide : {len(cis_set)}")

# Compter les lignes totales
with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    total = sum(1 for line in f if line.strip())
print(f"Lignes totales dans le JSONL : {total}")


import json
import pandas as pd

# CIS du JSONL
cis_jsonl = set()
with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("rcp_text", "").strip():
                cis_jsonl.add(data["CIS"])
        except:
            pass

# CIS du TSV
df = pd.read_csv("data/raw/notices_bdpm.tsv", sep="\t", dtype=str)
cis_tsv = set(df["CIS"].dropna())

print(f"CIS dans JSONL : {len(cis_jsonl)}")
print(f"CIS dans TSV   : {len(cis_tsv)}")
print(f"CIS en commun  : {len(cis_jsonl & cis_tsv)}")
print(f"CIS dans JSONL mais pas dans TSV : {len(cis_jsonl - cis_tsv)}")

# Comparer le format
print(f"\nExemple CIS JSONL : {repr(list(cis_jsonl)[:3])}")
print(f"Exemple CIS TSV   : {repr(list(cis_tsv)[:3])}")

import json
import pandas as pd
from collections import Counter

df = pd.read_csv("data/raw/notices_bdpm.tsv", sep="\t", dtype=str)
df["substances_actives"] = df["substances_actives"].fillna("INCONNUE")
cis_to_substance = dict(zip(df["CIS"], df["substances_actives"]))

# Compter combien de CIS par substance dans le JSONL
substance_counts = Counter()
with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("rcp_text", "").strip():
                cis = data["CIS"]
                substance = cis_to_substance.get(cis, f"INCONNUE_{cis}")
                substance_counts[substance] += 1
        except:
            pass

print(f"Substances uniques : {len(substance_counts)}")
print(f"\nTop 10 substances avec le plus de génériques :")
for substance, n in substance_counts.most_common(10):
    print(f"  {n:4d} génériques — {substance[:60]}")

print(f"\nSubstances avec 1 seul RCP : {sum(1 for n in substance_counts.values() if n == 1)}")
print(f"Substances avec 2-5 RCPs   : {sum(1 for n in substance_counts.values() if 2 <= n <= 5)}")
print(f"Substances avec >5 RCPs    : {sum(1 for n in substance_counts.values() if n > 5)}")


import json
import re
import pandas as pd
from preprocess import clean_text, chunk_semantic

# Récupérer le meilleur RCP du paracétamol
df = pd.read_csv("data/raw/notices_bdpm.tsv", sep="\t", dtype=str)
df["substances_actives"] = df["substances_actives"].fillna("INCONNUE")
cis_to_substance = dict(zip(df["CIS"], df["substances_actives"]))

candidats = []
with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        cis = data.get("CIS")
        rcp_text = data.get("rcp_text", "")
        if not rcp_text.strip():
            continue
        if cis_to_substance.get(cis) == "PARACÉTAMOL":
            candidats.append({"CIS": cis, "denomination": data["denomination"],
                               "substance_active": "PARACÉTAMOL", "rcp_text": rcp_text})

best = sorted(candidats, key=lambda x: len(x["rcp_text"]), reverse=True)[0]
print(f"CIS retenu : {best['CIS']} — {best['denomination']}")
print(f"Longueur brute : {len(best['rcp_text'])} caractères")

# Appliquer clean_text
best["rcp_text"] = clean_text(best["rcp_text"])
n_sep = len(re.findall(r"Redirection vers le haut de page", best["rcp_text"], re.IGNORECASE))
print(f"Séparateurs après clean_text : {n_sep}")

# Chunker
chunks = chunk_semantic(best)
print(f"Chunks produits : {len(chunks)}")
for c in chunks[:5]:
    print(f"  [{c['titre_section']}] {len(c['texte'].split())} mots")
    