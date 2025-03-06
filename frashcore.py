from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import pandas as pd
from tqdm import tqdm
import re
import numpy as np
from multiprocessing import Pool


# --- Variables globales pour chaque processus ---
global global_driver
global_driver= webdriver.Chrome()

def init_driver():
    """Initialise le driver une fois par processus."""
    global global_driver
    global_driver = webdriver.Chrome()

def links():
    """
    Récupère les liens pour chaque saison et les enregistre dans un CSV.
    """
    all_hrefs = []
    driver = webdriver.Chrome()
    # Parcours des saisons de 2012-2013 à 2024-2025
    for year in range(2012, 2025):
        season_str = f"{year}-{year+1}"
        print(f"Chargement de la saison : {season_str}")
        if year == 2024:
            url = f"https://www.flashscore.fr/football/espagne/laliga2/resultats/"
        else:
            url = f"https://www.flashscore.fr/football/espagne/laliga2-{season_str}/resultats/"
        
        driver.get(url)
        time.sleep(1)  # Laisser le temps au chargement
        actions = ActionChains(driver)
        wait = WebDriverWait(driver, 5)
        
        # Cliquer sur "Montrer plus de matchs" tant que possible
        while True:
            try:
                button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.event__more.event__more--static")))
                actions.move_to_element(button).perform()
                time.sleep(1)
                button.click()
                time.sleep(1)
            except Exception:
                print("Plus de bouton 'Montrer plus de matchs' disponible pour cette saison.")
                break

        # Récupérer tous les liens de matchs
        matches = driver.find_elements(By.CSS_SELECTOR, "div.event__match")
        for match in matches:
            anchors = match.find_elements(By.TAG_NAME, "a")
            for a in anchors:
                link = a.get_attribute("href")
                if link:
                    all_hrefs.append((season_str, link))
                    
    driver.quit()
    df = pd.DataFrame(all_hrefs, columns=["saison", "href"])
    df.to_csv("flashscore_ligue2_links.csv", index=False)
    print("Fin de l'extraction des liens. Le fichier CSV a été enregistré.")
    return df

def process_match(match_tuple):
    """
    Pour un match donné (saison, href), cette fonction :
      - Ouvre une instance Selenium
      - Extrait le score complet et les statistiques via l'URL "/statistiques-du-match/1"
      - Extrait le score mi-temps via l'URL de base
      - Ferme le driver et renvoie un dictionnaire des résultats.
    """
    saison, href = match_tuple
    result = {"saison": saison, "href": href,
              "score_equipe_home": None, "score_equipe_away": None,
              "score_mi_temps_home": None, "score_mi_temps_away": None}
    global global_driver    
    try:
        # --- Extraction des statistiques et score complet ---
        try:
            global_driver.get(href + "/statistiques-du-match/1")
            time.sleep(1)
            try:
                score_wrapper = global_driver.find_element(By.CSS_SELECTOR, "div.detailScore__wrapper")
                spans = score_wrapper.find_elements(By.TAG_NAME, "span")
                if len(spans) >= 3:
                    result["score_equipe_home"] = spans[0].text
                    result["score_equipe_away"] = spans[2].text
            except NoSuchElementException:
                print(f"Score introuvable pour {href}")
            time.sleep(1)
            try:
                stat_rows = global_driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="wcl-statistics"]')
                for row in stat_rows:
                    try:
                        tab = row.find_elements(By.CSS_SELECTOR, '[data-testid="wcl-scores-simpleText-01"]')
                        if len(tab) >= 3:
                            category_name = tab[1].text  # ex: "Possession"
                            home_value = tab[0].text     # ex: "52%"
                            away_value = tab[2].text     # ex: "48%"
                            # Création dynamique des colonnes selon la catégorie
                            col_name_home = category_name.replace(" ", "_") + "_home"
                            col_name_away = category_name.replace(" ", "_") + "_away"
                            result[col_name_home] = home_value
                            result[col_name_away] = away_value
                    except NoSuchElementException:
                        pass
            except NoSuchElementException:
                print(f"Tableau des statistiques introuvable pour {href}")
        except Exception as e:
            print(f"Erreur lors du chargement des stats pour {href}: {e}")
        
        # --- Extraction du score mi-temps ---
        try:
            global_driver.get(href)
            time.sleep(0.5)
            ht_elements = global_driver.find_elements(By.CSS_SELECTOR, '[data-testid^="wcl-scores-overline-02"]')
            if len(ht_elements) > 1:
                ht_text = ht_elements[1].text
                if "MI" in ht_text and len(ht_elements) > 2:
                    ht_text = ht_elements[2].text
                ht_text_clean = ht_text.replace(".", "").strip()
                if "-" in ht_text_clean:
                    home, away = ht_text_clean.split("-")
                    result["score_mi_temps_home"] = home.strip()
                    result["score_mi_temps_away"] = away.strip()
        except Exception as e:
            print(f"Impossible de trouver le score mi-temps pour {href} : {e}")
    finally:
        print("fin")
        
    return result

def merge(df1, df2):
    """
    Concatène verticalement deux DataFrames et enregistre le résultat dans un CSV.
    """
    df_merged = pd.concat([df1, df2], axis=0, ignore_index=True)
    df_merged.to_csv("merged_data.csv", index=False)
    return df_merged

def nettoyage(df):
    """
    Nettoyage du DataFrame : suppression de colonnes inutiles, remplissage et suppression des valeurs manquantes.
    """
    cols_to_drop = ["Touches_dans_la_surface_adverse_home","Tacles_away","Tacles_home",
                    "Touches_dans_la_surface_adverse_away","Expected_Goals_(xG)_home",
                    "Expected_Goals_(xG)_away","Centres_home","Centres_away","Sauvetages_home","Sauvetages_away",
                    "Buts_de_la_tête_home","Buts_de_la_tête_away","Passes_dans_le_dernier_tiers_away","Passes_dans_le_dernier_tiers_home",
                    "Montant_touché_away","Montant_touché_home","Tirs_en_dehors_de_la_surface_away","Tirs_en_dehors_de_la_surface_home",
                    "Tirs_à_l'intérieur_de_la_surface_away","Tirs_à_l'intérieur_de_la_surface_home","Grosses_occasions_away",
                    "Grosses_occasions_home","Interceptions_home","Interceptions_away","Touche_away","Touche_home"]
    df.drop(columns=cols_to_drop, axis=1, inplace=True, errors='ignore')
    
    # Remplissage des cartons si ces colonnes existent
    for col in ["Cartons_Rouges_home", "Cartons_Rouges_away", "Cartons_Jaunes_away", "Cartons_Jaunes_home"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    
    df.dropna(inplace=True)
    df.reset_index(inplace=True, drop=True)
    df.to_csv("matchs_utilisable_l1.csv", index=False)
    return df

def pretraitement(df,name):
    """
    Prétraitement : suppression de colonnes inutiles, conversion de pourcentages et calcul de résultats.
    """
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # Conversion des pourcentages pour la possession de balle si les colonnes existent
    for col in ['Possession_de_balle_home', 'Possession_de_balle_away']:
        if col in df.columns:
            df[col] = df[col].str.rstrip('%').astype(float) / 100
    
    def extract_percentage(value):
        match = re.search(r'(\d+)%', str(value))
        if match:
            return float(match.group(1)) / 100
        return None

    for col in ['Passes_home', 'Passes_away']:
        if col in df.columns:
            df[col] = df[col].apply(extract_percentage)
    
    colonnes_numeriques = [
        'score_equipe_home', 'score_equipe_away', 'Tirs_au_but_home', 'Tirs_au_but_away',
        'Tirs_cadrés_home', 'Tirs_cadrés_away', 'Tirs_non_cadrés_home', 'Tirs_non_cadrés_away',
        'Tirs_bloqués_home', 'Tirs_bloqués_away', 'Corners_home', 'Corners_away',
        'Sauvetages_du_gardien_home', 'Sauvetages_du_gardien_away', 'Coup_francs_home', 'Coup_francs_away',
        'Hors-jeu_home', 'Hors-jeu_away', 'Fautes_home', 'Fautes_away', 'Cartons_Jaunes_home',
        'Cartons_Jaunes_away', 'Passes_home', 'Passes_away', 'Cartons_Rouges_home', 'Cartons_Rouges_away'
    ]
    for col in colonnes_numeriques:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    if 'score_equipe_home' in df.columns and 'score_equipe_away' in df.columns:
        df['resultat'] = np.where(df['score_equipe_home'] > df['score_equipe_away'], -1,
                           np.where(df['score_equipe_home'] == df['score_equipe_away'], 0, 1))
    df.to_csv(f"data_{name}.csv", index=False)
    return df

if __name__ == "__main__":
    
    df1 = pd.read_csv("merged_data.csv")
    df2 = pd.read_csv("data_laliga2.csv")
    
    df = merge(df1,df2)
