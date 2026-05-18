
# MODULES
import requests
import csv
import pandas as pd 
import os


BDPM_URL ="https://base-donnees-publique.medicaments.gouv.fr/download/file/"
headers = {"User-Agent": "Mozilla/5.0 (compatible; medrag-fr/1.0)"}

FICHIERS = {
    "medicaments" : "CIS_bdpm.txt",
    "compositions" : "CIS_COMPO_bdpm.txt",
    "presentations" : "CIS_CIP_bdpm.txt",
    "generiques" : "CIS_GENER_bdpm.txt",
    "info_importantes": "CIS_InfoImportantes_bdpm.txt",
}

COLONNES = {
    "medicaments" : [
        "CIS", "denomination", "forme_pharma", "voie_admin",
        "statut_AMM", "type_procedure", "etat_commercialisation",
        "date_AMM", "statut_BdM", "num_autorisation_europeenne", 
        "titulaires", "surveillance_renforcee"
    ],
    "compositions" : [
        "CIS", "designation_element", "code_substance",
        "denomination_substance", "dosage", "ref_dosage",
        "nature_composant", "num_liaison"
    ],
    "presentations" : [
        "CIS", "CIP7", "libelle", "statut_admin", "etat_commercialisation",
        "date_declaration", "CIP13", "agrement_collectivites", 
        "taux_remboursement", "prix", "indic_remboursement", 
        "info_importantes"
    ],
}

def dowload_files(name, output_dir="data/raw") : 
    os.makedirs(output_dir, exist_ok=True)
    file_name = FICHIERS[name]
    url = BDPM_URL + file_name
    path = os.path.join(output_dir, file_name)
    if os.path.exists(path):
        print(f"{file_name} déjà présent, téléchargement ignoré.")
        return path
    print(f"Téléchargement de {file_name}...")
    reponse = requests.get(url, headers=headers, timeout=30)
    reponse.raise_for_status()

    with open(path, "wb") as f :
        f.write(reponse.content)

    print(f" sauvegardé : {path} ({len(reponse.content)/1024:.1f} Ko)")
    return path

def load_files(name, output_dir="data/raw") :
    path = dowload_files(name, output_dir)
    colonnes = COLONNES.get(name, None)

    df = pd.read_csv(
        path,
        sep="\t",
        encoding="latin-1",
        header=None, 
        names=colonnes,
        on_bad_lines="skip",
        dtype=str,
    )

    print(f"{len(df)} lignes chargées pour '{name}'")
    return df

def notice_builder(output_dir="data/raw") :
    df_med = load_files("medicaments", output_dir)
    df_compo = load_files("compositions", output_dir)
    print(df_med["etat_commercialisation"].value_counts(dropna=False))
    df_med = df_med[df_med["etat_commercialisation"]== "Commercialisée"].copy()
        
    substances = (
        df_compo
        .groupby("CIS")["denomination_substance"]
        .apply(lambda x : ", ".join(x.dropna().unique()))
        .reset_index()
        .rename(columns={"denomination_substance" : "substances_actives"})
    )

    df =df_med.merge(substances, on="CIS", how="left")

    print(f"Notices fusionnées : {len(df)} médicaments, {len(df.columns)} colonnes")
    return df 

def save_notices(output_dir="data/raw") :
    df = notice_builder(output_dir)
    path = os.path.join(output_dir, "notices_bdpm.tsv")
    df.to_csv(path, sep="\t", index= False, encoding="utf-8")
    print(f"Sauvegarde des notices {path}")
    return path

if __name__ == "__main__" :
    print("test récup des données")

    for name in FICHIERS:
        try :
            dowload_files(name)
        except Exception as e :
            print(f"erreur sur {name} : {e}")
    print()

    try:
        path = save_notices()
        print("Test option 2")
    except Exception as e :
        print(f"Erreur lors de la construction des notices")