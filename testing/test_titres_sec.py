import json

with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data["CIS"] == "61876780":  # Abacavir Arrow
            text = data["rcp_text"]
            # Afficher les 50 caractères avant et après chaque séparateur
            parts = text.split("Redirection vers le haut de page")
            for i, part in enumerate(parts[:10]):
                print(f"--- BLOC {i} ---")
                print(repr(part[-100:]))  # fin du bloc
                print()
            break