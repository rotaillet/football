from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import pandas as pd
from tqdm import tqdm

# 1) Préparation du driver et de la liste des saisons

def links(driver):
    all_hrefs = []

    # De 2000-2001 jusqu'à 2023-2024
    for year in range(2024, 2025):
        season_str = f"{year}-{year+1}"
        print(f"Chargement de la saison : {season_str}")
        if year == 2024:
            url = f"https://www.flashscore.fr/football/france/ligue-1/resultats/"
        else:
            
            url = f"https://www.flashscore.fr/football/france/ligue-1-{season_str}/resultats/"
            

        # 2) Charger la page
        driver.get(url)
        time.sleep(3)  # Laisser le temps à la page de se charger

        # 3) Cliquer sur "Montrer plus de matchs" tant que possible
        actions = ActionChains(driver)
        wait = WebDriverWait(driver, 5)

        while True:
            try:
                button = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "a.event__more.event__more--static")
                ))
                actions.move_to_element(button).perform()
                time.sleep(1)
                button.click()
                time.sleep(1)  # Attendre un peu le chargement
            except:
                print("Plus de bouton 'Montrer plus de matchs' disponible pour cette saison.")
                break

        # 4) Récupérer les blocs de match et extraire les liens
        matches = driver.find_elements(By.CSS_SELECTOR, "div.event__match")
        for match in matches:
            anchors = match.find_elements(By.TAG_NAME, "a")
            for a in anchors:
                link = a.get_attribute("href")
                # On peut ignorer les liens vides ou None
                if link:
                    all_hrefs.append((season_str, link))

    # 5) Convertir en DataFrame
    df = pd.DataFrame(all_hrefs, columns=["saison", "href"])

    # 6) Sauvegarder en CSV (sans l’index)
    df.to_csv("flashscore_ligue1_links_2024.csv", index=False)

    # Fermer le navigateur

    print("Fin du script. Le fichier CSV a été enregistré.")



def extract(driver, csv_file):
    # 1) Lire le fichier CSV
    df = pd.read_csv(csv_file)
    # Inversion des lignes (la dernière devient la première, etc.)
    df = df.iloc[::-1].reset_index(drop=True)

    # Vérifier que les colonnes de score existent, sinon les créer
    if "score_equipe1" not in df.columns:
        df["score_equipe1"] = None
    if "score_equipe2" not in df.columns:
        df["score_equipe2"] = None

    # 2) Boucler sur les lignes du DataFrame avec une barre de progression
    for i in tqdm(range(len(df)), desc="Extraction des statistiques"):
        href = df.loc[i, "href"]
        # Charger la page des statistiques
        try:
            driver.get(href + "/statistiques-du-match/1")
        except:
            print(f"Impossible de charger la page : {href}/statistiques-du-match/1")
            continue

        time.sleep(1)  # Laisser le temps de charger la page

        # 3) Récupérer le score
        try:
            score_wrapper = driver.find_element(By.CSS_SELECTOR, "div.detailScore__wrapper")
            spans = score_wrapper.find_elements(By.TAG_NAME, "span")
            # spans[0] = score équipe 1, spans[2] = score équipe 2
            score_equipe1 = spans[0].text
            score_equipe2 = spans[2].text

            df.at[i, "score_equipe1"] = score_equipe1
            df.at[i, "score_equipe2"] = score_equipe2

        except NoSuchElementException:
            print(f"Score introuvable pour le match : {href}")

        # 4) Récupérer toutes les statistiques (le "tableau")
        time.sleep(1)
        try:
            stat_rows = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="wcl-statistics"]')
            
            match_stats = {}
            for row in stat_rows:
                try:
                    # Récupérer la catégorie de la statistique
                    tab = row.find_elements(By.CSS_SELECTOR, '[data-testid="wcl-scores-simpleText-01"]')
                    category_name = tab[1].text  # ex: "Possession"
                    home_value = tab[0].text     # ex: "52%"
                    away_value = tab[2].text     # ex: "48%"

                    match_stats[category_name] = (home_value, away_value)

                except NoSuchElementException:
                    # Si une des sous-valeurs n’est pas trouvée, on ignore cette ligne
                    pass

            # 5) Insérer les stats dans le DataFrame
            for category_name, (val_home, val_away) in match_stats.items():
                col_name_home = category_name.replace(" ", "_") + "_home"
                col_name_away = category_name.replace(" ", "_") + "_away"

                df.at[i, col_name_home] = val_home
                df.at[i, col_name_away] = val_away

        except NoSuchElementException:
            print(f"Tableau des statistiques introuvable pour le match : {href}")

    # 6) Sauvegarder le DataFrame
    df.to_csv("test2.csv", index=False)
    print(f"Mise à jour terminée, le CSV est sauvegardé : {csv_file}")


# Exemple d'utilisation
if __name__ == "__main__":
    driver = webdriver.Chrome()
    csv = "flashscore_ligue1_links_2024.csv"
    links(driver)
    extract(driver,csv)
    driver.quit()