
# IMPORTS
import requests
import pandas as pd 
import os
import traceback
from config import FILES, ROWS, BDPM_BASE_URL_DOWNLOAD, SCRAPING_USER_AGENT 

def dowload_files(name, output_dir="data/raw"):
    """
    Dowloading raw text files from the BDPM public database

    Input :
        name (str) : the key corresponding to the file in the FILES dictionnary
        output_dir (str) : the directory where the file will be saved

    Return :
        path (str) : the local path to the download file

    """
    os.makedirs(output_dir, exist_ok=True)
    file_name = FILES[name]
    url = BDPM_BASE_URL_DOWNLOAD + file_name
    path = os.path.join(output_dir, file_name)

    if os.path.exists(path):
        print(f"{file_name} already exists, download skipped")
        return path
    
    print(f"Downloading {file_name}...")
    HEADER = {"User-Agent" : SCRAPING_USER_AGENT}
    reponse = requests.get(url, headers=HEADER, timeout=30)
    reponse.raise_for_status()

    with open(path, "wb") as f :
        f.write(reponse.content)

    print(f" Saved: {path} ({len(reponse.content)/1024:.1f} KB)")
    return path

def load_files(name, output_dir="data/raw") :
    """
    Loading downloaded BDPM files into pandas DataFrames

    Input : 
        name (str) : the key corresponding to the file in the FICHIERS dictionnary
        output_dir (str) : the directory where files are stored
    Return : 
        df (pd.DataFrame) : the formatted DataFrame containing the file's data
    """
    path = dowload_files(name, output_dir)
    rows = ROWS.get(name, None)

    df = pd.read_csv(
        path,
        sep="\t",
        encoding="latin-1",
        header=None, 
        names=rows,
        on_bad_lines="skip",
        dtype=str,
    )

    print(f"{len(df)} lines loaded for '{name}'")
    return df

def notice_builder(output_dir="data/raw") :
    """
    Merging multiple BDPM DataFrames to build a comprehensive metadata table for each medecine

    Input : 
        output_dir (str) : the directory where raw files are stored
    
        Return : 
            df (pd.DataFrame) : the merged DataFrame containing all relevant medecine metadata

    """
    df_med = load_files("medicaments", output_dir)
    df_compo = load_files("compositions", output_dir)
    df_gener = load_files("generiques", output_dir)
    df_info = load_files("info_importantes", output_dir)

    print(df_med["etat_commercialisation"].value_counts(dropna=False))
    
    # Filtering only currently marketed medecines
    df_med = df_med[df_med["etat_commercialisation"]== "Commercialisée"].copy()
    
    # Grouping active substances by CIS
    substances = (
        df_compo
        .groupby("CIS")["denomination_substance"]
        .apply(lambda x : ", ".join(x.dropna().unique()))
        .reset_index()
        .rename(columns={"denomination_substance" : "substances_actives"})
    )

    if not df_info.empty and "text_info" in df_info.columns:
        infos_importantes = (
            df_info
            .groupby("CIS")["text_info"]
            .apply(lambda x : ", ".join(x.dropna().unique()))
            .reset_index()
            .rename(columns={"text_info" : "alertes_securite"})
        )
    else :
        infos_importantes = pd.DataFrame(columns=["CIS","alertes_securite"]) 

    # Deduplicating generics 
    generiques = df_gener[["CIS", "id_groupe_generique", "libelle_groupe_generique", "type_generique"]].drop_duplicates()

    # Merging all datasets
    df = df_med.merge(substances, on="CIS", how="left")
    df = df.merge(generiques, on="CIS", how="left")
    df = df.merge(infos_importantes, on="CIS", how="left")

    print(f"Merged records : {len(df)} medecines, {len(df.columns)} columns")
    return df 

def save_notices(output_dir="data/raw") :
    """
    Saving the final merged DataFrame as a TSV file

    Input : 
        output_dir (str) : the directory where the TSV file will be saved
    
    Return : 
        path (str) : the local path to the saved TSV file

    """
    df = notice_builder(output_dir)
    path = os.path.join(output_dir, "notices_bdpm.tsv")
    df.to_csv(path, sep="\t", index= False, encoding="utf-8")
    print(f"Metadata successfully saved to '{path}'")
    return path

if __name__ == "__main__" :
    print("\nStarting BDPM data retrieval")

    for name in FILES:
        try :
            dowload_files(name)
        except Exception as e :
            print(f"Error on {name}: {e}")
    print()

    try:
        path = save_notices()
        print(f"Retrieval success, data pipeline finished. Output located in: 'data/raw'")
    except Exception as e :
        print(f"CRITICAL ERROR")
        traceback.print_exc()