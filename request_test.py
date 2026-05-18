import requests

url = "https://base-donnees-publique.medicaments.gouv.fr/download/file/CIS_bdpm.txt"
headers = {"User-Agent": "Mozilla/5.0 (compatible; medrag-fr/1.0)"}

response = requests.get(url, headers=headers, timeout=30)

print(f"Status : {response.status_code}")
print(f"Taille : {len(response.content)} octets")
print(response.text[:300])