# IMPORTS
import os 
import time 
import json 
import pandas as pd 
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from tqdm import tqdm

BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr"
HEADERS = {"User-Agent" : "Mozilla/5.0 (compatible; medrag-fr/1.0; research)"}
PAUSE = 1.5

def scrape_rcp(cis):
    """
    Scraping the SmPC  (Summary of Product Characteristics) - RCP in French -
    and leaflet for a given CIS code

    Input :
        cis (str) : the unique medecine identifier (Code Identifiant de Spécialité)

    Return :
        dict : dictionnary containing the CIS, denomination, and Markdown formatted SmPC
               and leaflet texts
    """

    url = f"{BASE_URL}/medicament/{cis}/extrait"
    reponse = requests.get(url, headers=HEADERS, timeout=30)
    reponse.raise_for_status()

    soup = BeautifulSoup(reponse.text, "html.parser")

    titre = soup.find("h3")
    denomination = titre.get_text(strip=True) if titre else ""

    def html_to_markdown(panel):
        if not panel :
            return ""
        for tag in panel.find_all("a"):
            tag.unwrap()
        return md(str(panel), heading_style="ATX", strip=['img'])

    rcp_panel = soup.find("div", {"id" : "tabpanel-rcp-panel"})
    rcp_md = html_to_markdown(rcp_panel)
    
    notice_panel = soup.find("div", {"id" : "tabpanel-notice-panel"})
    notice_md = html_to_markdown(notice_panel)
    
    return {
        "CIS" : cis,
        "denomination" : denomination,
        "rcp_text" : rcp_md,
        "notice_text" : notice_md
    }

def scrape_batch(notices_path, output_path, n=None, resume=True):
    """
    Running a batch scraping process for mutliple medecines with resume capabilities

    Input :
        notices_path (str) : path to the TSV file containing the list of CIS codes
        output_path (str) : path to the JSONL output file where scraped data will be appended
        n (int, optional) : limit the number of medecines to scrape. Defaults to None (= all)
        resume (bool) : whether to skip already scraped CIS codes based on the output file. 
                        Default to True
    """
    df = pd.read_csv(notices_path, sep="\t", encoding="utf-8", dtype=str)
    
    # Extract the full list of CIS codes
    cis_list = df["CIS"].dropna().tolist()

    # Apply limit if 'n' is specified
    if n is not None:
        cis_list = cis_list[:n]

    done = set()
    if resume and os.path.exists(output_path):
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["CIS"])
                except Exception:
                    pass
        print(f"Resuming : {len(done)} medecines already scraped")
    
    todo = [cis for cis in cis_list if cis not in done]
    print(f"To scrape : {len(todo)} medecines")

    if not todo:
        print(f"Everything is already scraped")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "a", encoding="utf-8") as f:
        for cis in tqdm(todo, desc="Scraping in progress", unit="SmPC"):
            try:
                data = scrape_rcp(cis)

                # Skip if both texts are empty
                if not data["rcp_text"] and not data["notice_text"]:
                    tqdm.write(f"[{cis}] - Empty SmPC and leaflet, skipped")
                    continue

                f.write(json.dumps(data, ensure_ascii=False) + "\n")
                f.flush()

                time.sleep(PAUSE)

            except Exception as e:
                tqdm.write(f" [{cis}] - ERROR: {e}")
                time.sleep(PAUSE)
    print(f"\nFinished -> {output_path}")

if __name__ == "__main__":
    print("\nStarting BDPM Web scraping")
    scrape_batch(
        notices_path="data/raw/notices_bdpm.tsv",
        output_path="data/raw/rcp_complet.jsonl",
        n=None,  
        resume=True
        )