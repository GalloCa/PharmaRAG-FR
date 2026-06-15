import json

with open("data/raw/rcp_test_VMD.jsonl", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i == 3:  # Abacavir Arrow — on sait qu'il a un RCP riche
            data = json.loads(line)
            print(data["rcp_text"][:2000])
            break