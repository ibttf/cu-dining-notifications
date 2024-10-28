import json
import boto3
import os
from datetime import datetime
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dataclasses import dataclass, field
from tempfile import mkdtemp
import time
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
ses = boto3.client('ses', region_name='us-east-2')
users_table = dynamodb.Table('users')

@dataclass
class MenuItem:
    title: str
    allergens: List[str]
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_halal: bool = False

@dataclass
class DiningLocation:
    name: str
    url: str
    menus: Dict[str, Dict[str, Dict[str, MenuItem]]]
    open_today: bool = False
    open_times: str = ""

def initialize_driver():
    """Set up Chrome for Lambda environment"""
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument(f"--user-data-dir={mkdtemp()}")
    chrome_options.add_argument(f"--data-path={mkdtemp()}")
    chrome_options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    chrome_options.add_argument("--remote-debugging-pipe")
    chrome_options.add_argument("--verbose")
    chrome_options.add_argument("--log-path=/tmp/chromedriver.log")
    chrome_options.binary_location = "/opt/chrome/chrome-linux64/chrome"

    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log"
    )

    return webdriver.Chrome(
        service=service,
        options=chrome_options
    )

class ColumbiaDiningScraper:
    BASE_URL = 'https://dining.columbia.edu/'
    TIMEOUT = 10

    def __init__(self):
        self.driver = initialize_driver()
        self.locations: Dict[str, DiningLocation] = self._initialize_locations()

    def _initialize_locations(self) -> Dict[str, DiningLocation]:
        """Initialize the dining locations dictionary with known locations and their available menus."""
        return {
            'John Jay Dining Hall': DiningLocation(
                name='John Jay Dining Hall',
                url='https://dining.columbia.edu/content/john-jay-dining-hall',
                menus={
                    'Breakfast': {},
                    'Lunch': {},
                    'Dinner': {},
                    'Lunch & Dinner': {}
                }
            ),
            "JJ's Place": DiningLocation(
                name="JJ's Place",
                url='https://dining.columbia.edu/content/jjs-place-0',
                menus={
                    'All': {},
                    'Daily': {},
                    'Late Night': {},
                    'Breakfast': {}
                }
            ),
            'Ferris Booth Commons': DiningLocation(
                name='Ferris Booth Commons',
                url='https://dining.columbia.edu/content/ferris-booth-commons-0',
                menus={
                    'Breakfast': {},
                    'Lunch': {},
                    'Dinner': {},
                    'Lunch & Dinner': {}
                }
            ),
            'Faculty House': DiningLocation(
                name='Faculty House',
                url='https://dining.columbia.edu/content/faculty-house-0',
                menus={
                    'Lunch': {}
                }
            ),
            'The Fac Shack': DiningLocation(
                name="The Fac Shack",
                url='https://dining.columbia.edu/content/fac-shack',
                menus={
                    'Dinner': {}
                }
            )
            # Note: Removed locations without menus for efficiency
        }

    def _wait_and_find_element(self, by: By, value: str, timeout: int = TIMEOUT):
        """Wait for and return an element."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {value}")
            return None

    def _close_overlay(self):
        """Close privacy notice overlay if present."""
        try:
            close_button = self._wait_and_find_element(By.ID, "close-privacy-notice", timeout=5)
            if close_button:
                self.driver.execute_script("arguments[0].click();", close_button)
        except Exception as e:
            logger.debug(f"No overlay to close: {e}")

    def scrape_locations(self):
        """Scrape all dining locations and their menus."""
        try:
            logger.info("Starting to scrape locations")
            self.driver.get(self.BASE_URL)
            self._close_overlay()

            # Find all dining locations
            locations = self.driver.find_elements(
                By.CSS_SELECTOR, 
                '.location.dining-location, .location.retail-location'
            )
            logger.info(f"Found {len(locations)} locations")

            # Update location status
            for loc in locations:
                try:
                    title = loc.find_element(By.CSS_SELECTOR, '.name a').text.strip()
                    if title in self.locations:
                        open_times = loc.find_element(By.CSS_SELECTOR, '.open-time').text
                        self.locations[title].open_today = bool(open_times)
                        self.locations[title].open_times = open_times
                        logger.info(f"Location {title} is {'open' if open_times else 'closed'}")
                except NoSuchElementException:
                    continue

            # Scrape menus for open locations
            for location in self.locations.values():
                if location.open_today:
                    self._scrape_location_menu(location)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()

    def _scrape_location_menu(self, location: DiningLocation):
        """Scrape menu for a specific location."""
        logger.info(f"Scraping menu for {location.name}")
        self.driver.get(location.url)
        self._close_overlay()

        try:
            menu_tabs = self._wait_and_find_element(By.CSS_SELECTOR, '.cu-dining-menu-tabs')
            if not menu_tabs:
                return

            for meal_type in location.menus.keys():
                try:
                    button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f"//button[text()='{meal_type}' and contains(@class, 'ng-binding')]")
                        )
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(1)

                    stations = self.driver.find_elements(By.XPATH, ".//div[div[contains(@class, 'meal-items')]]")
                    for station in stations:
                        station_name = station.find_element(By.CSS_SELECTOR, '.station-title').text
                        if station_name not in location.menus[meal_type]:
                            location.menus[meal_type][station_name] = {}

                        meal_items = station.find_elements(By.CSS_SELECTOR, '.meal-item')
                        for meal_item in meal_items:
                            menu_item = self._parse_menu_item(meal_item)
                            location.menus[meal_type][station_name][menu_item.title] = menu_item

                except TimeoutException:
                    logger.debug(f"No {meal_type} menu found for {location.name}")
                    continue

        except Exception as e:
            logger.error(f"Error scraping menu for {location.name}: {e}")

    def _parse_menu_item(self, meal_item) -> MenuItem:
        """Parse a menu item element and return MenuItem object."""
        title = meal_item.find_element(By.CSS_SELECTOR, '.meal-title').text

        # Parse dietary information
        dietary_info = {'is_vegetarian': False, 'is_vegan': False, 'is_halal': False}
        try:
            dietary_text = meal_item.find_element(By.CSS_SELECTOR, 'div.meal-prefs strong').text
            dietary_info = {
                'is_vegetarian': "Vegetarian" in dietary_text or "Vegan" in dietary_text,
                'is_vegan': "Vegan" in dietary_text,
                'is_halal': "Halal" in dietary_text
            }
        except NoSuchElementException:
            pass

        # Parse allergens
        allergens = []
        try:
            allergens_text = meal_item.find_element(By.TAG_NAME, 'em').text
            if "Contains: " in allergens_text:
                allergens = allergens_text.split("Contains: ")[1].split(", ")
        except NoSuchElementException:
            pass

        return MenuItem(
            title=title,
            allergens=allergens,
            **dietary_info
        )

    def format_menu_for_user(self, user: Dict, locations: Dict[str, DiningLocation]) -> List[Dict]:
        """Format menu data according to user preferences."""
        formatted_locations = []
        
        for location_name, location in locations.items():
            if not location.open_today:
                continue

            location_data = {
                "name": location_name,
                "open_times": location.open_times,
                "meals": []
            }

            for meal_type, stations in location.menus.items():
                if not stations:
                    continue

                meal_data = {
                    "meal_type": meal_type,
                    "stations": []
                }

                for station_name, items in stations.items():
                    station_data = {
                        "station_name": station_name,
                        "items": []
                    }

                    for item_name, item in items.items():
                        # Check dietary preferences
                        if user.get('is_vegetarian') and not item.is_vegetarian:
                            continue
                        if user.get('is_vegan') and not item.is_vegan:
                            continue
                        if user.get('is_halal') and not item.is_halal:
                            continue

                        # Check allergens
                        skip_item = False
                        for unavailable in user.get('unavailable_foods', []):
                            if any(allergen.lower() == unavailable.lower() for allergen in item.allergens):
                                skip_item = True
                                break
                        if skip_item:
                            continue

                        # Format dietary information
                        dietary = []
                        if item.is_vegan:
                            dietary.append("Vegan")
                        elif item.is_vegetarian:
                            dietary.append("Vegetarian")
                        if item.is_halal:
                            dietary.append("Halal")

                        station_data["items"].append({
                            "name": item_name,
                            "dietary": ", ".join(dietary) if dietary else None,
                            "allergens": ", ".join(item.allergens) if item.allergens else None
                        })

                    if station_data["items"]:
                        meal_data["stations"].append(station_data)

                if meal_data["stations"]:
                    location_data["meals"].append(meal_data)

            if location_data["meals"]:
                formatted_locations.append(location_data)

        return formatted_locations

    def send_email(self, user_email: str, formatted_menu: List[Dict]):
        """Send formatted menu to user via SES."""
        try:
            template_data = {
                "date": datetime.now().strftime("%A, %B %d, %Y"),
                "locations": formatted_menu
            }

            response = ses.send_templated_email(
                Source='churlee12@gmail.com',  # Make sure this email is verified in SES
                Destination={
                    'ToAddresses': [user_email]
                },
                Template='ColumbiaDiningMenuUpdate',
                TemplateData=json.dumps(template_data)
            )
            logger.info(f"Email sent successfully to {user_email}")
            return response
        except Exception as e:
            logger.error(f"Error sending email to {user_email}: {e}")
            raise


def lambda_handler(event, context):
    logger.info("Starting Lambda execution")
    try:
        # Initialize scraper
        scraper = ColumbiaDiningScraper()
        
        # Scrape all locations
        scraper.scrape_locations()
        
        # Get all users from DynamoDB
        response = users_table.scan()
        users = response['Items']
        logger.info(f"Found {len(users)} users")
        
        # Process menu for each user and send email
        for user in users:
            formatted_menu = scraper.format_menu_for_user(user, scraper.locations)
            if formatted_menu:  # Only send email if there are matching menu items
                scraper.send_email(user['email'], formatted_menu)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Emails sent successfully')
        }
        
    except Exception as e:
        logger.error(f"Error in lambda execution: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
    

