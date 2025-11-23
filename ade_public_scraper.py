from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime
import time
import re
import pytz

class ADEPublicScraper:
    def __init__(self):
        self.base_url = "https://ade-production.ut-capitole.fr/direct/index.jsp"

        # Configuration Selenium
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--headless')  # Mode headless pour CI/CD
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def navigate_and_select_calendar(self):
        """
        Navigue vers l'emploi du temps public et sélectionne le calendrier M1 MIAGE FA-ALT
        """
        try:
            print("Accès à l'interface publique...")
            url = f"{self.base_url}?showTree=true&showPianoDays=true&showPianoWeeks=true&showOptions=false&days=0,1,2,3,4,5&displayConfName=Web&projectId=26&login=anonymous"
            self.driver.get(url)

            # Attendre que la page se charge
            time.sleep(8)

            # Séquence de clics pour déplier l'arborescence (clic sur les icônes)
            navigation_path = [
                "Groupes d'étudiants",
                "UFR Informatique",
                "M1 MIAGE FA-ALT",
                "IMMGA1AN",
                "IMMGA1CM",
                "IMMGA1DO",
                "IMMGA1DV",
                "IMMGA1TD"
            ]

            # Éléments finaux à sélectionner avec Ctrl+clic (sélection multiple)
            final_selections = [
                "IMMGA1AN01",
                "IMMGA1CM01",
                "IMMGA1DO01",
                "IMMGA1DV01",
                "IMMGA1TD01"
            ]

            # Combiner pour la boucle de navigation
            selections = navigation_path

            # Fonction pour attendre qu'un élément apparaisse
            def wait_for_element(text_to_find, timeout=20):
                """Attendre qu'un élément contenant le texte apparaisse dans le DOM"""
                print(f"  Attente de l'apparition de '{text_to_find}' (max {timeout}s)...")
                start_time = time.time()
                attempt = 0

                while time.time() - start_time < timeout:
                    attempt += 1
                    elements = self.driver.find_elements(By.TAG_NAME, "span")
                    elements.extend(self.driver.find_elements(By.TAG_NAME, "div"))

                    for elem in elements:
                        try:
                            elem_text = elem.text.strip()
                            is_match = (elem_text == text_to_find or
                                       elem_text.startswith(text_to_find + '\n') or
                                       (text_to_find in elem_text and len(elem_text) < 100))
                            if is_match:
                                elapsed = int(time.time() - start_time)
                                print(f"  ✓ Élément trouvé après {elapsed}s (tentative #{attempt})")
                                return True
                        except:
                            continue

                    time.sleep(1)

                elapsed = int(time.time() - start_time)
                print(f"  ✗ Timeout après {elapsed}s ({attempt} tentatives)")
                return False

            for i, text_to_find in enumerate(selections):
                print(f"Recherche de: '{text_to_find}'...")

                try:
                    # Attendre que l'élément soit présent dans le DOM
                    if not wait_for_element(text_to_find, timeout=25):
                        print(f"✗ Impossible de trouver '{text_to_find}' (timeout)")
                        return False

                    # Chercher tous les spans et divs
                    all_elements = self.driver.find_elements(By.TAG_NAME, "span")
                    all_elements.extend(self.driver.find_elements(By.TAG_NAME, "div"))

                    found = False
                    for elem in all_elements:
                        try:
                            elem_text = elem.text.strip()
                            # Recherche plus stricte: texte exact, commence par, ou contient mais court
                            is_match = (elem_text == text_to_find or
                                       elem_text.startswith(text_to_find + '\n') or
                                       (text_to_find in elem_text and len(elem_text) < 100))

                            if is_match:
                                print(f"  Trouvé: '{elem_text[:80]}...' " if len(elem_text) > 80 else f"  Trouvé: '{elem_text}'")

                                # Scroller vers l'élément
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                                time.sleep(1)

                                # Pour tous les éléments de navigation, cliquer sur l'icône pour déployer
                                try:
                                    # Récupérer la div parente du span
                                    parent_div = elem.find_element(By.XPATH, "..")

                                    # Chercher l'image avec la classe x-tree3-node-joint dans cette div
                                    try:
                                        tree_icon = parent_div.find_element(By.CSS_SELECTOR, "img.x-tree3-node-joint")
                                        print(f"  Icône trouvée dans la div parente")
                                    except:
                                        # Si pas trouvée directement, chercher dans tous les enfants
                                        tree_icon = parent_div.find_element(By.TAG_NAME, "img")
                                        print(f"  Image trouvée dans la div parente")

                                    # Cliquer sur l'icône (sans scroll pour éviter les bugs)
                                    tree_icon.click()
                                    print(f"✓ Cliqué sur l'icône de: '{text_to_find}'")
                                    found = True
                                    break
                                except Exception as e1:
                                    # Si pas d'icône trouvée, essayer via JavaScript
                                    try:
                                        print(f"  Tentative JS... ({e1})")
                                        result = self.driver.execute_script("""
                                            var span = arguments[0];
                                            var parentDiv = span.parentElement;

                                            // Chercher l'image dans la même div
                                            var icon = parentDiv.querySelector('img.x-tree3-node-joint');
                                            if (!icon) {
                                                // Si pas trouvée, chercher n'importe quelle image
                                                icon = parentDiv.querySelector('img');
                                            }

                                            if (icon) {
                                                icon.click();
                                                return true;
                                            }
                                            return false;
                                        """, elem)

                                        if result:
                                            print(f"✓ Cliqué (JS) sur l'icône de: '{text_to_find}'")
                                            found = True
                                            break
                                        else:
                                            print(f"  Aucune icône trouvée via JS")
                                            continue
                                    except Exception as e2:
                                        print(f"  Erreur JS: {e2}")
                                        continue
                        except:
                            continue

                    if not found:
                        print(f"✗ Impossible de trouver '{text_to_find}'")
                        return False

                    # Debug: afficher l'index
                    print(f"  [Debug] i={i}, total={len(selections)}")

                    # Attendre que l'animation de dépliage se termine et scroller
                    print(f"  → Démarrage du scroll (élément {i+1}/{len(selections)})...")
                    time.sleep(2)

                    # Scroller le conteneur scrollable de l'arbre
                    try:
                        print(f"  → Recherche du conteneur scrollable (.x-grid3-scroller)...")

                        # Scroller le vrai conteneur scrollable
                        result = self.driver.execute_script("""
                            // Trouver le conteneur scrollable spécifique
                            var scroller = document.querySelector('.x-grid3-scroller');

                            if (scroller) {
                                var oldScroll = scroller.scrollTop;

                                // Scroll progressif vers le bas (pour forcer le lazy loading de GWT)
                                for (var i = 0; i < 10; i++) {
                                    scroller.scrollTop += 100;
                                }

                                return {
                                    found: true,
                                    scrolledFrom: oldScroll,
                                    scrolledTo: scroller.scrollTop,
                                    scrollHeight: scroller.scrollHeight,
                                    clientHeight: scroller.clientHeight
                                };
                            }

                            return {found: false, message: 'Scroller (.x-grid3-scroller) non trouvé'};
                        """)

                        print(f"  → Résultat: {result}")

                        if result.get('found'):
                            print(f"  → Attente du lazy loading (1s)...")
                            time.sleep(1)

                            # Forcer GWT à re-render comme quand on ouvre F12
                            print(f"  → Déclenchement d'un resize pour forcer le re-render...")
                            self.driver.execute_script("""
                                window.dispatchEvent(new Event('resize'));
                            """)
                            time.sleep(0.5)

                            # Redimensionner légèrement la fenêtre (comme F12)
                            current_size = self.driver.get_window_size()
                            print(f"  → Resize fenêtre {current_size['width']} -> {current_size['width'] - 10} -> {current_size['width']}")
                            self.driver.set_window_size(current_size['width'] - 10, current_size['height'])
                            time.sleep(0.3)
                            self.driver.set_window_size(current_size['width'], current_size['height'])
                            time.sleep(1)

                            print(f"  ✓ Re-render forcé !")
                        else:
                            print(f"  ⚠ Conteneur non trouvé, attente de 1s...")
                            time.sleep(1)

                        print(f"  ✓ Scroll effectué !")
                    except Exception as e:
                        print(f"  ⚠ Erreur de scroll: {e}")

                except Exception as e:
                    print(f"✗ Erreur lors de la sélection de '{text_to_find}': {e}")
                    return False

            print("✓ Navigation terminée, démarrage de la sélection multiple...")
            time.sleep(2)

            # Scroller au milieu de la liste pour voir tous les éléments à sélectionner
            print("Scroll vers le milieu de l'arbre pour voir tous les éléments...")
            self.driver.execute_script("""
                var scroller = document.querySelector('.x-grid3-scroller');
                if (scroller) {
                    scroller.scrollTop = scroller.scrollHeight / 2;
                }
            """)
            time.sleep(1)

            # Forcer le re-render après le scroll au milieu
            print("Forcer le re-render après scroll au milieu...")
            self.driver.execute_script("window.dispatchEvent(new Event('resize'));")
            time.sleep(0.5)
            current_size = self.driver.get_window_size()
            self.driver.set_window_size(current_size['width'] - 10, current_size['height'])
            time.sleep(0.3)
            self.driver.set_window_size(current_size['width'], current_size['height'])
            time.sleep(1)

            # Sélection multiple avec Ctrl+clic sur les éléments finaux
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains

            for idx, element_name in enumerate(final_selections):
                print(f"Sélection de '{element_name}' ({idx+1}/{len(final_selections)})...")

                try:
                    # Attendre que l'élément soit présent
                    if not wait_for_element(element_name, timeout=15):
                        print(f"  ⚠ Élément '{element_name}' non trouvé, skip...")
                        continue

                    # Chercher l'élément
                    all_elements = self.driver.find_elements(By.TAG_NAME, "span")
                    all_elements.extend(self.driver.find_elements(By.TAG_NAME, "div"))

                    found = False
                    for elem in all_elements:
                        try:
                            elem_text = elem.text.strip()
                            if elem_text == element_name or element_name in elem_text and len(elem_text) < 100:
                                print(f"  Trouvé: '{elem_text}' (tag={elem.tag_name}, visible={elem.is_displayed()})")

                                # Scroller vers l'élément pour qu'il soit visible
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                                time.sleep(0.5)

                                # Ctrl+clic pour sélection multiple
                                # Le premier élément doit être cliqué normalement, les autres avec Ctrl
                                try:
                                    if idx == 0:
                                        # Premier élément: clic simple
                                        elem.click()
                                        print(f"  ✓ Clic simple effectué sur '{element_name}' (premier élément)")
                                    else:
                                        # Éléments suivants: Ctrl+clic
                                        actions = ActionChains(self.driver)
                                        # Utiliser COMMAND sur Mac, CONTROL sinon
                                        ctrl_key = Keys.COMMAND if 'mac' in self.driver.capabilities.get('platformName', '').lower() else Keys.CONTROL
                                        actions.key_down(ctrl_key)
                                        actions.click(elem)
                                        actions.key_up(ctrl_key)
                                        actions.perform()
                                        print(f"  ✓ Ctrl+Clic effectué sur '{element_name}' (avec {ctrl_key})")
                                except Exception as click_error:
                                    # Si ActionChains échoue, essayer avec JavaScript
                                    print(f"  ⚠ Erreur ActionChains: {click_error}, tentative JS...")
                                    if idx == 0:
                                        self.driver.execute_script("arguments[0].click();", elem)
                                        print(f"  ✓ Clic simple JS effectué sur '{element_name}'")
                                    else:
                                        # Simuler Ctrl+clic avec JavaScript
                                        self.driver.execute_script("""
                                            var elem = arguments[0];
                                            var evt = new MouseEvent('click', {
                                                bubbles: true,
                                                cancelable: true,
                                                view: window,
                                                ctrlKey: true,
                                                metaKey: true  // Pour Mac
                                            });
                                            elem.dispatchEvent(evt);
                                        """, elem)
                                        print(f"  ✓ Ctrl+Clic JS effectué sur '{element_name}'")

                                found = True
                                break
                        except Exception as e:
                            print(f"  ⚠ Erreur sur élément: {e}")
                            continue

                    if not found:
                        print(f"  ⚠ Impossible de cliquer sur '{element_name}'")

                    time.sleep(0.5)

                except Exception as e:
                    print(f"  ✗ Erreur sur '{element_name}': {e}")

            print("✓ Sélection multiple terminée")

            # Attendre que le planning se charge complètement
            print("Attente du chargement complet du planning...")
            time.sleep(8)

            return True

        except Exception as e:
            print(f"✗ Erreur lors de la navigation: {e}")
            return False

    def get_schedule(self, weeks=2):
        """
        Récupère le HTML de l'emploi du temps pour plusieurs semaines
        """
        all_html = []

        try:
            # Le planning devrait déjà être chargé après la sélection
            print("Récupération du planning...")
            time.sleep(2)

            for week in range(weeks):
                print(f"Récupération semaine {week + 1}/{weeks}...")

                # Récupérer le HTML de la semaine actuelle
                all_html.append(self.driver.page_source)

                # Passer à la semaine suivante (même logique que le script précédent)
                if week < weeks - 1:
                    try:
                        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                        week_buttons = []
                        current_week_text = None

                        for btn in all_buttons:
                            try:
                                btn_text = btn.text.strip()
                                if btn_text and re.match(r'^\(\d+\)', btn_text):
                                    week_buttons.append(btn)
                                    aria_pressed = btn.get_attribute('aria-pressed')
                                    if aria_pressed == 'true':
                                        current_week_text = btn_text
                            except:
                                continue

                        if not current_week_text and week_buttons:
                            current_week_text = week_buttons[0].text

                        print(f"  Semaine actuelle: {current_week_text}")

                        week_match = re.search(r'\((\d+)\)', current_week_text)

                        if week_match:
                            current_week_num = int(week_match.group(1))
                            next_week_num = current_week_num + 1

                            for btn in week_buttons:
                                btn_text = btn.text.strip()
                                if f"({next_week_num})" in btn_text:
                                    try:
                                        self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                                        time.sleep(0.5)
                                        btn.click()

                                        wait = WebDriverWait(self.driver, 10)
                                        wait.until(lambda d: btn.get_attribute('aria-pressed') == 'true')
                                        print(f"  → Navigation vers: {btn_text}")
                                        break
                                    except:
                                        self.driver.execute_script("arguments[0].click();", btn)
                                        time.sleep(2)
                                        break

                        time.sleep(5)

                    except Exception as e:
                        print(f"⚠ Erreur navigation: {e}")
                        break

            print(f"✓ {len(all_html)} semaine(s) récupérée(s)")
            return all_html

        except Exception as e:
            print(f"✗ Erreur: {e}")
            return None

    def parse_and_export_ical(self, html_content_list):
        """
        Parse le HTML et crée un fichier iCal (même logique que le script précédent)
        """
        if not isinstance(html_content_list, list):
            html_content_list = [html_content_list]

        paris_tz = pytz.timezone('Europe/Paris')

        cal = Calendar()
        cal.add('prodid', '-//UT Capitole M1 MIAGE FA-ALT//FR')
        cal.add('version', '2.0')
        cal.add('X-WR-CALNAME', 'M1 MIAGE FA-ALT')
        cal.add('X-WR-TIMEZONE', 'Europe/Paris')
        cal.add('method', 'PUBLISH')

        print("Parsing des événements...")

        events_found = 0

        for week_idx, html_content in enumerate(html_content_list):
            soup = BeautifulSoup(html_content, 'html.parser')

            # Calibration automatique
            hour_labels = soup.find_all('div', class_='slot')
            pixels_per_hour = None

            for i, label in enumerate(hour_labels):
                text = label.get_text(strip=True)
                style = label.get('style', '')

                if '08h00' in text:
                    match_8h = re.search(r'top:\s*(\d+)px', style)
                    if match_8h:
                        top_8h = int(match_8h.group(1))
                elif '09h00' in text and 'top_8h' in locals():
                    match_9h = re.search(r'top:\s*(\d+)px', style)
                    if match_9h:
                        top_9h = int(match_9h.group(1))
                        pixels_per_hour = top_9h - top_8h
                        hour_offset = top_8h
                        print(f"  Calibration: {pixels_per_hour}px/heure, offset={hour_offset}px")
                        break

            if not pixels_per_hour:
                pixels_per_hour = 17.5
                hour_offset = 17
                print(f"  Calibration par défaut: {pixels_per_hour}px/heure")

            # Extraire les dates
            day_labels = soup.find_all('div', class_='labelLegend')
            days_mapping = {}
            day_positions = []

            for label in day_labels:
                style = label.get('style', '')
                text = label.get_text(strip=True)

                if '/' in text and any(day in text for day in ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']):
                    left_match = re.search(r'left:(\d+)px', style)
                    date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)

                    if left_match and date_match:
                        left_pos = int(left_match.group(1))
                        day = int(date_match.group(1))
                        month = int(date_match.group(2))
                        year = int(date_match.group(3))
                        days_mapping[left_pos] = datetime(year, month, day)
                        day_positions.append(left_pos)

            # Calculer largeur colonne
            if len(day_positions) >= 2:
                day_positions.sort()
                column_width = day_positions[1] - day_positions[0]
                print(f"  Largeur colonne: {column_width}px")
            else:
                column_width = 115

            # Parser les événements
            event_divs = soup.find_all('div', attrs={'aria-label': True, 'class': 'eventText'})

            for event_div in event_divs:
                try:
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

                    day_column = left // column_width

                    base_date = None
                    sorted_days = sorted(days_mapping.items())
                    for i, (day_left, date) in enumerate(sorted_days):
                        if i == day_column:
                            base_date = date
                            break

                    if not base_date:
                        continue

                    # Calcul heure
                    event_offset = 8
                    hours_from_8am = (top - hour_offset - event_offset) / pixels_per_hour
                    start_hour_float = 8 + hours_from_8am

                    if start_hour_float < 0 or start_hour_float > 23:
                        continue

                    # Durée
                    table = parent.find('table', class_='event')
                    if table and table.get('style'):
                        height_match = re.search(r'height:(\d+)px', table.get('style'))
                        if height_match:
                            height = int(height_match.group(1))
                            duration_hours = height / pixels_per_hour
                        else:
                            duration_hours = 1.5
                    else:
                        duration_hours = 1.5

                    # Arrondir
                    def round_to_15min(hour_float):
                        total_minutes = hour_float * 60
                        rounded_minutes = round(total_minutes / 15) * 15
                        return int(rounded_minutes // 60), int(rounded_minutes % 60)

                    start_hour, start_minute = round_to_15min(start_hour_float)
                    end_hour, end_minute = round_to_15min(start_hour_float + duration_hours)

                    if not (0 <= start_hour <= 23) or not (0 <= end_hour <= 23):
                        continue

                    start_time = paris_tz.localize(base_date.replace(hour=start_hour, minute=start_minute))
                    end_time = paris_tz.localize(base_date.replace(hour=end_hour, minute=end_minute))

                    # Extraire infos
                    aria_label = event_div.get('aria-label', '')
                    lines = [line.strip() for line in aria_label.split('null') if line.strip()]

                    summary = lines[0] if lines else "Cours"
                    description_parts = lines[1:] if len(lines) > 1 else []
                    description = '\n'.join(description_parts)

                    # Créer événement
                    event = Event()
                    event.add('summary', summary)
                    event.add('dtstart', start_time.astimezone(pytz.UTC))
                    event.add('dtend', end_time.astimezone(pytz.UTC))
                    if description:
                        event.add('description', description)
                    event.add('location', description_parts[0] if description_parts else '')

                    cal.add_component(event)
                    events_found += 1

                except Exception as e:
                    continue

        print(f"✓ {events_found} événements trouvés")

        output_file = 'edt_m1_miage.ics'
        with open(output_file, 'wb') as f:
            f.write(cal.to_ical())

        print(f"✓ Fichier iCal généré: {output_file}")
        return output_file, events_found

    def close(self):
        """
        Ferme le navigateur
        """
        if self.driver:
            self.driver.quit()


def main():
    import sys

    print("=" * 50)
    print("ADE Public Scraper - M1 MIAGE FA-ALT")
    print("=" * 50)

    scraper = ADEPublicScraper()
    success = False

    try:
        # Naviguer et sélectionner le calendrier
        if not scraper.navigate_and_select_calendar():
            print("\n❌ Impossible de sélectionner le calendrier")
            sys.exit(1)

        # Récupérer l'emploi du temps
        html_content = scraper.get_schedule(weeks=2)

        if html_content:
            # Générer le fichier iCal
            ical_file, events_count = scraper.parse_and_export_ical(html_content)

            if events_count == 0:
                print("\n❌ Aucun événement trouvé - le fichier ne sera pas utilisé")
                sys.exit(1)

            print("\n" + "=" * 50)
            print("✓ Processus terminé")
            print("=" * 50)
            print(f"\nFichier généré: {ical_file}")
            print(f"Événements: {events_count}")
            success = True
        else:
            print("\n❌ Impossible de récupérer l'emploi du temps")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1)
    finally:
        scraper.close()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
