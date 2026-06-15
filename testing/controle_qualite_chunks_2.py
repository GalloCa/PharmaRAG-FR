import json
from collections import Counter

with open("data/processed/chunks_rcp.jsonl", encoding="utf-8") as f:
    chunks = [json.loads(line) for line in f]

# Distribution des titres
titres = Counter(c["titre_section"] for c in chunks)
print("Top 15 titres :")
for titre, n in titres.most_common(15):
    print(f"  {n:5d}  {titre[:50]}")

# Tailles
longueurs = [len(c["texte"].split()) for c in chunks]
print(f"\nLongueur moyenne : {sum(longueurs)//len(longueurs)} mots")
print(f"Min : {min(longueurs)} mots")
print(f"Max : {max(longueurs)} mots")
print(f"Chunks > 500 mots : {sum(1 for l in longueurs if l > 500)}")
print(f"Chunks < 20 mots  : {sum(1 for l in longueurs if l < 20)}")

# Vérifier un chunk médical concret
paracetamol_chunks = [c for c in chunks if "PARACÉTAMOL" in c.get("substance_active", "")]
print(f"\nChunks paracétamol : {len(paracetamol_chunks)}")
for c in paracetamol_chunks[:3]:
    print(f"  [{c['titre_section']}] {len(c['texte'].split())} mots")
    print(f"  {c['texte'][:150]}")
    print()