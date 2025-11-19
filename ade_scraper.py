from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime
import time
import re
import pytz
import os

class ADEScraper:
    def __init__(self, username=None, password=None):
        # Lire depuis les variables d'environnement si non fournis
        self.username = username or os.environ.get('SSO_USERNAME')
        self.password = password or os.environ.get('SSO_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("Username et password requis (paramètres ou variables d'environnement SSO_USERNAME/SSO_PASSWORD)")

        self.base_url = "https://ade-production.ut-capitole.fr"

        # Configuration Selenium
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Mode sans interface graphique
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def login(self):
        """
        Authentifie l'utilisateur via le SSO CAS avec Selenium
        """
        try:
            print("Connexion au SSO...")
            # Accéder à la page de planning (redirige vers le SSO)
            self.driver.get(f"{self.base_url}/direct/myplanning.jsp?logout=true")

            # Attendre le formulaire de connexion
            wait = WebDriverWait(self.driver, 10)
            username_field = wait.until(EC.presence_of_element_located((By.ID, "userfield")))

            print("Envoi des identifiants...")
            # Remplir le formulaire
            username_field.send_keys(self.username)
            password_field = self.driver.find_element(By.ID, "passwordfield")
            password_field.send_keys(self.password)

            # Soumettre le formulaire
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()

            # Attendre la redirection vers myplanning.jsp
            wait.until(lambda driver: "myplanning.jsp" in driver.current_url)

            print("✓ Connexion réussie")
            return True
        except Exception as e:
            print(f"✗ Échec de la connexion: {e}")
            return False

    def get_schedule(self, weeks=2):
        """
        Récupère le HTML de l'emploi du temps pour plusieurs semaines
        """
        all_html = []

        try:
            # Attendre que l'application GWT se charge
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.ID, "MyPlanning")))
            time.sleep(5)

            for week in range(weeks):
                print(f"Récupération semaine {week + 1}/{weeks}...")

                # Récupérer le HTML de la semaine actuelle
                all_html.append(self.driver.page_source)

                # Passer à la semaine suivante (sauf pour la dernière itération)
                if week < weeks - 1:
                    try:
                        # ADE utilise des boutons avec format "(XX)JJ mois AA"
                        # Stratégie: extraire le numéro de semaine actuel, chercher semaine+1

                        # 1. Chercher TOUS les boutons, même sans aria-pressed
                        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                        week_buttons = []
                        current_week_text = None

                        for btn in all_buttons:
                            try:
                                btn_text = btn.text.strip()
                                # Filtrer uniquement les boutons qui commencent par (XX)
                                if btn_text and re.match(r'^\(\d+\)', btn_text):
                                    week_buttons.append(btn)
                                    aria_pressed = btn.get_attribute('aria-pressed')
                                    if aria_pressed == 'true':
                                        current_week_text = btn_text
                            except:
                                continue

                        if not current_week_text and week_buttons:
                            # Si aucun bouton actif, prendre le premier
                            current_week_text = week_buttons[0].text

                        print(f"  Semaine actuelle: {current_week_text}")
                        print(f"  Boutons de semaine trouvés: {len(week_buttons)}")

                        # Extraire le numéro de semaine (XX)
                        if not current_week_text:
                            print("⚠ Aucun bouton de semaine trouvé")
                            break

                        week_match = re.search(r'\((\d+)\)', current_week_text)

                        clicked = False
                        if week_match:
                            current_week_num = int(week_match.group(1))
                            next_week_num = current_week_num + 1
                            print(f"  Recherche semaine {next_week_num}...")

                            for btn in week_buttons:
                                btn_text = btn.text.strip()
                                print(f"    - {btn_text} (visible: {btn.is_displayed()}, enabled: {btn.is_enabled()})")
                                if f"({next_week_num})" in btn_text:
                                    print(f"  ✓ Bouton trouvé, tentative de clic...")
                                    try:
                                        # Scroll vers l'élément si nécessaire
                                        self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                                        time.sleep(0.5)
                                        btn.click()
                                        clicked = True
                                        print(f"  → Navigation vers: {btn_text}")

                                        # Attendre que le bouton devienne actif (aria-pressed="true")
                                        wait = WebDriverWait(self.driver, 10)
                                        wait.until(lambda d: btn.get_attribute('aria-pressed') == 'true')
                                        print(f"  ✓ Page changée")
                                        break
                                    except Exception as click_error:
                                        print(f"  Erreur clic: {click_error}")
                                        # Essayer avec JavaScript
                                        try:
                                            self.driver.execute_script("arguments[0].click();", btn)
                                            clicked = True
                                            print(f"  → Navigation JS vers: {btn_text}")

                                            # Attendre que le bouton devienne actif
                                            wait = WebDriverWait(self.driver, 10)
                                            wait.until(lambda d: btn.get_attribute('aria-pressed') == 'true')
                                            print(f"  ✓ Page changée")
                                            break
                                        except:
                                            pass

                        if not clicked:
                            print("⚠ Impossible de naviguer vers la semaine suivante")
                            print("  Tentative avec JavaScript...")

                            # Dernier recours: utiliser JavaScript pour cliquer
                            try:
                                result = self.driver.execute_script(f"""
                                    var buttons = document.querySelectorAll('button[role="button"][aria-pressed="false"]');
                                    for (var i = 0; i < buttons.length; i++) {{
                                        if (buttons[i].textContent.includes('({next_week_num})')) {{
                                            buttons[i].click();
                                            return buttons[i].textContent;
                                        }}
                                    }}
                                    return null;
                                """)
                                if result:
                                    print(f"  → Navigation JS vers: {result}")
                                    clicked = True
                            except Exception as js_error:
                                print(f"  Erreur JS: {js_error}")

                        if not clicked:
                            break

                        # Attendre le rechargement complet des événements
                        time.sleep(5)

                    except Exception as e:
                        print(f"⚠ Erreur navigation semaine suivante: {e}")
                        import traceback
                        traceback.print_exc()
                        break

            print(f"✓ {len(all_html)} semaine(s) récupérée(s)")
            return all_html

        except Exception as e:
            print(f"✗ Erreur lors de la récupération: {e}")
            return None

    def save_html(self, html_content_list, filename="schedule.html"):
        """
        Sauvegarde le HTML pour analyse
        """
        if isinstance(html_content_list, list):
            # Sauvegarder la première semaine (pour debug)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content_list[0])
            print(f"✓ HTML sauvegardé dans {filename}")
        else:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content_list)
            print(f"✓ HTML sauvegardé dans {filename}")

    def parse_and_export_ical(self, html_content_list):
        """
        Parse le HTML de l'emploi du temps ADE et crée un fichier iCal
        """
        # Gérer liste ou string unique
        if not isinstance(html_content_list, list):
            html_content_list = [html_content_list]

        # Créer le calendrier avec timezone
        paris_tz = pytz.timezone('Europe/Paris')

        cal = Calendar()
        cal.add('prodid', '-//UT Capitole Schedule//FR')
        cal.add('version', '2.0')
        cal.add('X-WR-CALNAME', 'Emploi du Temps UT Capitole')
        cal.add('X-WR-TIMEZONE', 'Europe/Paris')
        cal.add('method', 'PUBLISH')

        print("Parsing des événements...")

        events_found = 0

        # Traiter chaque semaine
        for week_idx, html_content in enumerate(html_content_list):
            soup = BeautifulSoup(html_content, 'html.parser')

            # DÉTECTER L'ÉCHELLE AUTOMATIQUEMENT
            # Chercher les labels d'heure pour calibrer
            hour_labels = soup.find_all('div', class_='slot')
            pixels_per_hour = None

            for i, label in enumerate(hour_labels):
                text = label.get_text(strip=True)
                style = label.get('style', '')

                # Chercher "08h00" et "09h00" pour calibrer
                if '08h00' in text:
                    match_8h = re.search(r'top:\s*(\d+)px', style)
                    if match_8h:
                        top_8h = int(match_8h.group(1))
                elif '09h00' in text and 'top_8h' in locals():
                    match_9h = re.search(r'top:\s*(\d+)px', style)
                    if match_9h:
                        top_9h = int(match_9h.group(1))
                        pixels_per_hour = top_9h - top_8h
                        hour_offset = top_8h  # Position de 8h
                        print(f"  Calibration détectée: {pixels_per_hour}px/heure, offset={hour_offset}px pour 8h")
                        break

            if not pixels_per_hour:
                # Valeurs par défaut (ancienne échelle)
                pixels_per_hour = 17.5
                hour_offset = 17
                print(f"  Calibration par défaut: {pixels_per_hour}px/heure")

            # Extraire les dates des jours de la semaine
            day_labels = soup.find_all('div', class_='labelLegend')
            days_mapping = {}  # left position -> date
            day_positions = []  # Pour calculer la largeur des colonnes

            for label in day_labels:
                style = label.get('style', '')
                text = label.get_text(strip=True)

                # Chercher les dates au format "Lundi 17/11/2025"
                if '/' in text and any(day in text for day in ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']):
                    # Extraire la position left
                    left_match = re.search(r'left:(\d+)px', style)
                    date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)

                    if left_match and date_match:
                        left_pos = int(left_match.group(1))
                        day = int(date_match.group(1))
                        month = int(date_match.group(2))
                        year = int(date_match.group(3))
                        days_mapping[left_pos] = datetime(year, month, day)
                        day_positions.append(left_pos)

            # Calculer la largeur des colonnes automatiquement
            if len(day_positions) >= 2:
                day_positions.sort()
                column_width = day_positions[1] - day_positions[0]
                print(f"  Largeur colonne détectée: {column_width}px")
            else:
                column_width = 115  # Défaut
                print(f"  Largeur colonne par défaut: {column_width}px")

            # Chercher tous les événements
            event_divs = soup.find_all('div', attrs={'aria-label': True, 'class': 'eventText'})

            for event_div in event_divs:
                try:
                    # Récupérer le parent avec position absolute
                    parent = event_div.find_parent('div', style=lambda s: s and 'position: absolute' in s)
                    if not parent or not parent.get('style'):
                        continue

                    style = parent.get('style')
                    left_match = re.search(r'left:\s*(\d+)px', style)
                    top_match = re.search(r'top:\s*(\d+)px', style)

                    if not left_match or not top_match:
                        continue

                    left = int(left_match.group(1))
                    top = int(top_match.group(1))

                    # Trouver la date du jour en utilisant la largeur détectée
                    day_column = left // column_width

                    # Trouver la date correspondante
                    base_date = None
                    sorted_days = sorted(days_mapping.items())
                    for i, (day_left, date) in enumerate(sorted_days):
                        if i == day_column:
                            base_date = date
                            break

                    if not base_date:
                        continue

                    # Calculer l'heure à partir de top en utilisant la calibration détectée
                    # Les événements ont un offset de ~8px par rapport à la grille
                    event_offset = 8
                    hours_from_8am = (top - hour_offset - event_offset) / pixels_per_hour
                    start_hour_float = 8 + hours_from_8am

                    # Ignorer les événements hors limites (probablement chevauchement ou erreur)
                    if start_hour_float < 0 or start_hour_float > 23:
                        continue

                    # Récupérer la durée depuis la table event
                    table = parent.find('table', class_='event')
                    if table and table.get('style'):
                        height_match = re.search(r'height:(\d+)px', table.get('style'))
                        if height_match:
                            height = int(height_match.group(1))
                            duration_hours = height / pixels_per_hour
                        else:
                            duration_hours = 1.5  # Défaut
                    else:
                        duration_hours = 1.5

                    # Arrondir à 15 minutes (créneaux standards universitaires)
                    def round_to_15min(hour_float):
                        total_minutes = hour_float * 60
                        rounded_minutes = round(total_minutes / 15) * 15
                        return int(rounded_minutes // 60), int(rounded_minutes % 60)

                    start_hour, start_minute = round_to_15min(start_hour_float)
                    end_hour, end_minute = round_to_15min(start_hour_float + duration_hours)

                    # Valider les heures (doivent être entre 0 et 23)
                    if not (0 <= start_hour <= 23) or not (0 <= end_hour <= 23):
                        print(f"⚠ Heure invalide: {start_hour}h{start_minute} - {end_hour}h{end_minute}")
                        continue

                    # Créer les datetime avec timezone Paris (réutiliser paris_tz défini au début)
                    start_time = paris_tz.localize(base_date.replace(
                        hour=start_hour,
                        minute=start_minute
                    ))
                    end_time = paris_tz.localize(base_date.replace(
                        hour=end_hour,
                        minute=end_minute
                    ))

                    # Extraire le titre et les détails
                    aria_label = event_div.get('aria-label', '')
                    lines = [line.strip() for line in aria_label.split('null') if line.strip()]

                    summary = lines[0] if lines else "Cours"
                    description_parts = lines[1:] if len(lines) > 1 else []
                    description = '\n'.join(description_parts)

                    # Créer l'événement iCal
                    event = Event()
                    event.add('summary', summary)
                    # Convertir en UTC pour compatibilité maximale avec Apple Calendar
                    event.add('dtstart', start_time.astimezone(pytz.UTC))
                    event.add('dtend', end_time.astimezone(pytz.UTC))
                    if description:
                        event.add('description', description)
                    event.add('location', description_parts[0] if description_parts else '')

                    cal.add_component(event)
                    events_found += 1

                except Exception as e:
                    print(f"Erreur lors du parsing d'un événement: {e}")
                    continue

        if events_found > 0:
            print(f"✓ {events_found} événements trouvés")
        else:
            print("⚠ Aucun événement trouvé - La structure HTML doit être analysée")
            print("→ Consultez le fichier schedule.html pour adapter le parsing")

        # Sauvegarder le fichier .ics
        output_file = 'emploi_du_temps.ics'
        with open(output_file, 'wb') as f:
            f.write(cal.to_ical())

        print(f"✓ Fichier iCal généré: {output_file}")
        return output_file

    def close(self):
        """
        Ferme le navigateur Selenium
        """
        if self.driver:
            self.driver.quit()


def main():
    """
    Fonction principale
    """
    print("=" * 50)
    print("ADE Schedule Scraper - UT Capitole")
    print("=" * 50)

    # Utiliser les variables d'environnement ou demander
    username = os.environ.get('SSO_USERNAME')
    password = os.environ.get('SSO_PASSWORD')

    if not username or not password:
        print("\n⚠ Variables d'environnement non trouvées")
        username = input("Identifiant: ")
        password = input("Mot de passe: ")

    # Créer le scraper
    scraper = ADEScraper(username, password)

    try:
        # Se connecter
        if not scraper.login():
            print("\n❌ Impossible de se connecter. Vérifiez vos identifiants.")
            return

        # Récupérer l'emploi du temps
        html_content = scraper.get_schedule()

        if html_content:
            # Sauvegarder le HTML pour analyse
            scraper.save_html(html_content)

            # Générer le fichier iCal
            ical_file = scraper.parse_and_export_ical(html_content)

            print("\n" + "=" * 50)
            print("✓ Processus terminé")
            print("=" * 50)
            print(f"\nFichiers générés:")
            print(f"  - schedule.html (pour analyse)")
            print(f"  - {ical_file} (à importer dans Apple Calendar)")
            print("\nPour importer dans Apple Calendar:")
            print(f"  1. Ouvrir le fichier {ical_file}")
            print("  2. Ou: Fichier > Importer dans Calendar")
        else:
            print("\n❌ Impossible de récupérer l'emploi du temps")
    finally:
        # Toujours fermer le navigateur
        scraper.close()


if __name__ == "__main__":
    main()
