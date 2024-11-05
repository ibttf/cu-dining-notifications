
import json
import boto3
from datetime import datetime
from typing import Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dataclasses import dataclass
from tempfile import mkdtemp
import time
import logging
import random
import os 
import subprocess
import socket
import resource

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS stuff
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
ses = boto3.client('ses', region_name='us-east-1')
users_table = dynamodb.Table('users')

#classes
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
    print('Initializing driver')
    # Set Chrome binary location
    options = webdriver.ChromeOptions()

    #COMMENT THESE LINES TO RUN LOCALLY
    # service = Service("/opt/chromedriver")
    # options.add_argument("--single-process")
    # options.add_argument("--disable-dev-tools")
    # options.binary_location = '/opt/chrome/chrome'

    # UNCOMMENT TO RUN LOCALLY

    service = Service('/opt/homebrew/bin/chromedriver')
    options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    # Absolute minimum required options for Lambda
    # options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")

    options.add_argument("--disable-dev-shm-usage")

    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")


    # Add these options specifically for content loading
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-infobars')
    options.add_argument('--enable-javascript')  # Explicitly enable JavaScript
    options.add_argument('--window-size=1920,1080')  # Set a proper window size
    
    # Don't disable images as they might be needed for page load detection
    options.page_load_strategy = 'normal'  # Use 'normal' instead of 'eager'
    


    chrome = None
    try:
        # Initialize ChromeDriver with options and service
        chrome = webdriver.Chrome(options=options, service=service)
        print("Chrome browser started")
        
        # Set page load timeout
        chrome.set_page_load_timeout(20)
        print(f"Chrome version: {chrome.capabilities['browserVersion']}")
        print(f"ChromeDriver version: {chrome.capabilities['chrome']['chromedriverVersion']}")

        return chrome
    
    except Exception as e:
        print(f"Chrome initialization error: {str(e)}")
        print(f"Chrome binary location: {options.binary_location}")
        print(f"ChromeDriver path: {service.path}")
        raise Exception(f"Failed to start Chrome browser: {str(e)}")  
class ColumbiaDiningScraper:
    BASE_URL = 'https://dining.columbia.edu/'
    TIMEOUT = 10

    def __init__(self):
        self.driver = initialize_driver()
        self.subjects=['Wake up fucker!!!!', 'rise and shine bitchboy', 'Good morning big back', "Hola papi <3333", "Ohaiyo onii-chan", "pls text back the kids miss you", "Get out of bed; they're not texting you back", "Another morning spent single! Here's the menus", "You're never getting married. Here's the menus", "om nom nom nom", "hello my sweet darling... wake up", "menus are out!","joonha if you're reading this, please text me back"]
        self.closed_locations = []
        # Dictionary of all possible locations, including those without menus
        self.locations: Dict[str, DiningLocation] = {
            'John Jay Dining Hall': DiningLocation(
                name='John Jay Dining Hall',
                url='https://dining.columbia.edu/content/john-jay-dining-hall',
                menus={
                    'Brunch': {},
                    'Dinner': {},
                    'Lunch & Dinner': {}
                }
            ),
            "JJ's Place": DiningLocation(
                name="JJ's Place",
                url='https://dining.columbia.edu/content/jjs-place-0',
                menus={
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
                name='The Fac Shack',
                url='https://dining.columbia.edu/content/fac-shack',
                menus={
                    'Dinner': {}
                }
            ),
            'Blue Java Café - Butler Library': DiningLocation(
                name='Blue Java Café - Butler Library',
                url='https://dining.columbia.edu/content/blue-java-cafe-butler-library',
                menus={}
            ),
            "Chef Mike's Sub Shop": DiningLocation(
                name="Chef Mike's Sub Shop",
                url='https://dining.columbia.edu/content/chef-mikes-sub-shop',
                menus={}
            ),
            "Chef Don's Pizza Pi": DiningLocation(
                name="Chef Don's Pizza Pi",
                url='https://dining.columbia.edu/content/chef-dons-pizza-pi',
                menus={}
            ),
            'Grace Dodge Dining Hall': DiningLocation(
                name='Grace Dodge Dining Hall',
                url='https://dining.columbia.edu/content/grace-dodge-dining-hall',
                menus={}
            ),
            'Robert F. Smith Dining Hall': DiningLocation(
                name='Robert F. Smith Dining Hall',
                url='https://dining.columbia.edu/content/robert-f-smith-dining-hall',
                menus={}
            ),
            'Blue Java Café - Mudd Hall': DiningLocation(
                name='Blue Java Café - Mudd Hall',
                url='https://dining.columbia.edu/content/blue-java-cafe-mudd-hall',
                menus={}
            ),
            'Blue Java Café - Uris': DiningLocation(
                name='Blue Java Café - Uris',
                url='https://dining.columbia.edu/content/blue-java-cafe-uris',
                menus={}
            ),
            'Blue Java at Everett Library Café': DiningLocation(
                name='Blue Java at Everett Library Café',
                url='https://dining.columbia.edu/content/blue-java-everett-library-cafe',
                menus={}
            ),
            'Lenfest Café': DiningLocation(
                name='Lenfest Café',
                url='https://dining.columbia.edu/content/lenfest-cafe',
                menus={}
            )
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

    def _click_view_more(self):
        """Click the 'View More' button and wait for additional locations to load."""
        try:
            print("Looking for 'View More' button...")
            
            # Wait for page to be fully loaded
            time.sleep(2)
            
            # Try to find the button with different selectors
            selectors = [
                '.show-all-dinings',
                'button.show-all-dinings',
                '.show-all-locations',
                'button.show-all-locations',
                'button[onclick*="show-all"]'
            ]
            
            view_more_button = None
            for selector in selectors:
                try:
                    view_more_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if view_more_button:
                        print(f"Found button with selector: {selector}")
                        break
                except TimeoutException:
                    continue
            
            if not view_more_button:
                print("Could not find 'View More' button with any selector")
                # Take screenshot for debugging
                self.driver.save_screenshot('/tmp/before_click.png')
                print("Saved screenshot to /tmp/before_click.png")
                return False
            
            # Scroll the button into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", view_more_button)
            time.sleep(1)  # Wait after scroll
            
            # Try different click methods
            try:
                view_more_button.click()
            except Exception as e:
                print(f"Regular click failed: {e}, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", view_more_button)
            
            # Wait for new content to load
            time.sleep(3)
            
            print("Successfully clicked 'View More' button")
            return True
            
        except TimeoutException:
            print("'View More' button not found or not clickable (timeout)")
            return False
        except Exception as e:
            print(f"Error clicking 'View More' button: {e}")
            return False
    def scrape_locations(self):
        """Scrape all dining locations and their menus."""
        try:
            print("Starting to scrape locations")
            self.driver.get(self.BASE_URL)
            
            # Add initial wait for page load
            print("Waiting for page to load...")
            time.sleep(3)  # Initial wait for page load
            
            # Wait for any dynamic content to load
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.dining-location, .retail-location'))
                )
                print("Initial content loaded")
            except TimeoutException:
                print("Timeout waiting for initial content")
                raise
            
            # Click the "View More" button to show all locations
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                if self._click_view_more():
                    print("Successfully expanded locations")
                    break
                print(f"Retry {retry_count + 1} of {max_retries} for expanding locations")
                time.sleep(2)
                retry_count += 1
            
            # Additional wait after expanding
            time.sleep(3)
            
            # Find all dining and retail locations
            dining_locations = self.driver.find_elements(
                By.CSS_SELECTOR, 
                '.dining-location'
            )
            retail_locations = self.driver.find_elements(
                By.CSS_SELECTOR,
                '.retail-location'
            )
            all_locations = dining_locations + retail_locations
            print(f"Found {len(all_locations)} locations")

            # Reset closed locations list
            self.closed_locations = []

            # Process each location
            for loc in all_locations:
                try:
                    # Find the location title using the link element
                    title_element = loc.find_element(By.CSS_SELECTOR, '.name a')
                    if not title_element:
                        continue
                    
                    title = title_element.text.strip()
                    
                    if not title:  # Skip if title is empty
                        continue
                        
                    print(f"Processing location: {title}")
                
                    
                    # Check if location is in our tracking list
                    if title in self.locations:
                        # Check if the location is open by looking for open-time with content
                        try:
                            open_time_element = loc.find_element(By.CSS_SELECTOR, '.open-time')
                            open_times = open_time_element.text.strip() if open_time_element else ""
                            
                            # A location is considered open if it has open times
                            is_open = bool(open_times)
                            
                            # Update location status
                            self.locations[title].open_today = is_open
                            self.locations[title].open_times = open_times
                            
                            if is_open:
                                print(f"Location {title} is open: {open_times}")
                            else:
                                self.closed_locations.append(title)
                                print(f"Location {title} is closed")
                            
                        except NoSuchElementException:
                            # No open time element found - location is closed
                            self.locations[title].open_today = False
                            self.locations[title].open_times = ""
                            self.closed_locations.append(title)
                            print(f"Location {title} is closed (no open times found)")
                    else:
                        print(f"Warning: Found location '{title}' on website that isn't in our tracking list")

                except NoSuchElementException as e:
                    print(f"Error processing location: {e}")
                    continue
                except Exception as e:
                    print(f"Unexpected error processing location: {e}")
                    continue

            # Scrape menus for open locations that have menu configurations
            for location in self.locations.values():
                if location.open_today and location.menus:
                    self._scrape_location_menu(location)
            print("Current URL:", self.driver.current_url)
            print("Page source:", self.driver.page_source[:1000])  # First 1000 chars
        except Exception as e:
            print(f"Error during scraping: {e}")
            # Add more detailed error information
            print("Current URL:", self.driver.current_url)
            print("Page source:", self.driver.page_source[:1000])  # First 1000 chars
            raise
        finally:
            if self.driver:
                self.driver.quit()

    def _scrape_location_menu(self, location: DiningLocation):
        """Scrape menu for a specific location."""
        print(f"Scraping menu for {location.name}")
        self.driver.get(location.url)

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
            print(f"Error scraping menu for {location.name}: {e}")

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
                "subject": random.choice(self.subjects),  # Pick a random subject
                "locations": formatted_menu,
                "closed_locations": self.closed_locations
            }
            print("Template data", template_data)
            response = ses.send_templated_email(
                Source='roy@cudiningnotifications.com',  # Make sure this email is verified in SES
                Destination={
                    'ToAddresses': [user_email]
                },
                Template='ColumbiaDiningMenuUpdate',
                TemplateData=json.dumps(template_data)
            )
            print(f"Email sent successfully to {user_email}")
            return response
        except Exception as e:
            print(f"Error sending email to {user_email}: {e}")
            raise

def lambda_handler(event, context):
    try:
        socket.gethostbyname('dining.columbia.edu')
        print("DNS resolution successful")
    except Exception as e:
        print(f"DNS resolution failed: {e}")
    
    try:
        chrome_path = subprocess.check_output("find /opt /usr -name chrome", shell=True).decode()
        chromedriver_path = subprocess.check_output("find /opt /usr -name chromedriver", shell=True).decode()
        logger.info(f"Chrome path:\n{chrome_path}")
        logger.info(f"Chromedriver path:\n{chromedriver_path}")
    except Exception as e:
        print(f"Error finding Chrome or Chromedriver: {e}")
    successful_sends=[]
    try:
        
        # Initialize scraper
        scraper = ColumbiaDiningScraper()
        
        # Scrape all locations
        scraper.scrape_locations()
        
        # Get all users from DynamoDB
        response = users_table.scan()
        users = response['Items']
        print(f"Found {len(users)} users")
        
        # Process menu for each user and send email
        for user in users:
            formatted_menu = scraper.format_menu_for_user(user, scraper.locations)
            if formatted_menu:  # Only send email if there are matching menu items
                scraper.send_email(user['email'], formatted_menu)
                successful_sends.append(user['email'])
        
        return {
            'statusCode': 200,
            'body': json.dumps('Emails sent successfully')
        }
        
    except Exception as e:
        print(f"Error in lambda execution: {e}")
        # Print full traceback for debugging
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        }

lambda_handler(None, None)




