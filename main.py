
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
    options = webdriver.ChromeOptions()

    # EC2 Configuration
    service = Service("/usr/local/bin/chromedriver")
    options.binary_location = '/usr/bin/google-chrome-stable'
    
    # Enhanced browser configuration
    user_agent = random.choice([
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ])
    options.add_argument(f'user-agent={user_agent}')
    
    # Memory and performance optimizations
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-browser-side-navigation')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    options.add_argument('--window-size=1280,720')  # Reduced window size
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Memory management
    options.add_argument('--single-process')  # Use single process
    options.add_argument('--disable-application-cache')
    options.add_argument('--disable-dev-tools')
    options.add_argument('--aggressive-cache-discard')
    options.add_argument('--disable-cache')
    options.add_argument('--disable-offline-load-stale-cache')
    options.add_argument('--disk-cache-size=0')
    options.add_argument('--media-cache-size=0')
    
    # Set specific timeout values
    options.add_argument('--dns-prefetch-disable')
    options.page_load_strategy = 'eager'  # Changed from 'normal' to 'eager'
    
    # Temporary directories with cleanup
    temp_dir = mkdtemp()
    options.add_argument(f'--user-data-dir={temp_dir}')
    options.add_argument(f'--crash-dumps-dir={temp_dir}')
    options.add_argument(f'--disk-cache-dir={temp_dir}')
    
    # Add experimental options
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Additional performance settings
    prefs = {
        'profile.default_content_setting_values': {
            'images': 2,  # Disable images
            'plugins': 2,  # Disable plugins
            'popups': 2,  # Disable popups
            'geolocation': 2,  # Disable geolocation
            'notifications': 2  # Disable notifications
        },
        'disk-cache-size': 4096,
        'profile.managed_default_content_settings': {
            'javascript': 1  # Enable JavaScript
        }
    }
    options.add_experimental_option('prefs', prefs)

    print("Chrome binary path:", options.binary_location)
    print("ChromeDriver path:", service.path)

    def create_driver():
        driver = webdriver.Chrome(options=options, service=service)
        
        # Set shorter timeouts
        driver.set_script_timeout(20)
        driver.set_page_load_timeout(30)
        
        # Execute CDP commands
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": user_agent,
            "platform": "Linux x86_64"
        })
        
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """
        })
        
        return driver

    # Try to create driver with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            driver = create_driver()
            print(f"Chrome started successfully on attempt {attempt + 1}")
            print(f"Chrome version: {driver.capabilities['browserVersion']}")
            print(f"ChromeDriver version: {driver.capabilities['chrome']['chromedriverVersion']}")
            return driver
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise Exception(f"Failed to start Chrome after {max_retries} attempts: {str(e)}")


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
    def _safe_get_page(self, url, max_attempts=3):
        """Safely load a page with retries and proper error handling."""
        for attempt in range(max_attempts):
            try:
                # Clear memory before loading new page
                self.driver.execute_script('window.localStorage.clear();')
                self.driver.execute_script('window.sessionStorage.clear();')
                
                # Delete all cookies
                self.driver.delete_all_cookies()
                
                # Load the page
                print(f"\nAttempt {attempt + 1} of {max_attempts} to load {url}")
                self.driver.get(url)
                
                # Initial wait
                time.sleep(random.uniform(3, 5))
                
                # Check for Cloudflare
                if "Just a moment" in self.driver.title:
                    print("Detected Cloudflare challenge, waiting...")
                    time.sleep(random.uniform(8, 12))
                    
                    # Verify if we got past Cloudflare
                    if "Just a moment" in self.driver.title:  # Fixed syntax
                        print("Still on Cloudflare page after waiting")
                        if attempt < max_attempts - 1:
                            continue
                        else:
                            return False
                
                # Quick check if page loaded successfully
                try:
                    body = self.driver.find_element(By.TAG_NAME, 'body')
                    if body:
                        print("Page loaded successfully")
                        return True
                except:
                    print("Could not verify page load")
                    if attempt < max_attempts - 1:
                        continue
                    return False
                    
            except Exception as e:
                print(f"Error loading page (attempt {attempt + 1}): {str(e)}")
                if attempt < max_attempts - 1:
                    # Clear memory and reset state
                    try:
                        self.driver.execute_script("window.stop();")
                    except:
                        pass
                    time.sleep(random.uniform(2, 4))
                else:
                    print("Failed to load page after all attempts")
                    return False
        
        return False      

    def scrape_locations(self):
        """Scrape all dining locations and their menus."""
        try:
            print("Starting to scrape locations")
            if not self._safe_get_page(self.BASE_URL):
                raise Exception("Failed to load main dining page after all attempts")

            # Wait for any dynamic content to load with retry logic
            max_content_retries = 3
            for attempt in range(max_content_retries):
                try:
                    print(f"\nAttempting to find dining locations (attempt {attempt + 1})")
                    
                    # Wait for locations to be present
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.dining-location, .retail-location'))
                    )
                    print("Found initial locations")
                    break
                except TimeoutException:
                    if attempt < max_content_retries - 1:
                        print("Timeout waiting for locations, retrying...")
                        self.driver.refresh()
                        time.sleep(random.uniform(3, 5))
                    else:
                        raise Exception("Could not find any dining locations after all attempts")

            # Click the "View More" button with retry logic
            view_more_attempts = 0
            while view_more_attempts < 3:
                try:
                    print("\nLooking for 'View More' button...")
                    
                    # Try different selectors
                    selectors = [
                        '.show-all-dinings',
                        'button.show-all-dinings',
                        '.show-all-locations',
                        'button.show-all-locations',
                        'button[onclick*="show-all"]'
                    ]
                    
                    button_found = False
                    for selector in selectors:
                        try:
                            button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            if button:
                                print(f"Found button with selector: {selector}")
                                # Scroll into view and click
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                time.sleep(random.uniform(1, 2))
                                self.driver.execute_script("arguments[0].click();", button)
                                button_found = True
                                break
                        except TimeoutException:
                            continue

                    if button_found:
                        print("Successfully clicked 'View More'")
                        time.sleep(random.uniform(3, 5))
                        break
                    else:
                        print("No 'View More' button found, might be already expanded")
                        break

                except Exception as e:
                    print(f"Error clicking 'View More' (attempt {view_more_attempts + 1}): {str(e)}")
                    view_more_attempts += 1
                    if view_more_attempts < 3:
                        time.sleep(random.uniform(2, 4))
                    continue

            # Find all locations after expansion
            print("\nLocating all dining locations...")
            dining_locations = self.driver.find_elements(By.CSS_SELECTOR, '.dining-location')
            retail_locations = self.driver.find_elements(By.CSS_SELECTOR, '.retail-location')
            all_locations = dining_locations + retail_locations
            
            if not all_locations:
                raise Exception("No locations found after expansion")
                
            print(f"Found {len(all_locations)} total locations")

            # Reset closed locations list
            self.closed_locations = []

            # Process each location
            for loc in all_locations:
                try:
                    # Find the location title
                    title_element = loc.find_element(By.CSS_SELECTOR, '.name a')
                    if not title_element:
                        continue
                    
                    title = title_element.text.strip()
                    if not title:
                        continue
                        
                    print(f"\nProcessing location: {title}")
                    
                    # Check if location is in our tracking list
                    if title in self.locations:
                        try:
                            # Check if location is open
                            open_time_element = loc.find_element(By.CSS_SELECTOR, '.open-time')
                            open_times = open_time_element.text.strip() if open_time_element else ""
                            
                            is_open = bool(open_times)
                            
                            # Update location status
                            self.locations[title].open_today = is_open
                            self.locations[title].open_times = open_times
                            
                            if is_open:
                                print(f"{title} is open: {open_times}")
                            else:
                                self.closed_locations.append(title)
                                print(f"{title} is closed")
                            
                        except NoSuchElementException:
                            print(f"{title} appears to be closed (no hours found)")
                            self.locations[title].open_today = False
                            self.locations[title].open_times = ""
                            self.closed_locations.append(title)
                            
                except Exception as e:
                    print(f"Error processing location {title if 'title' in locals() else 'unknown'}: {str(e)}")
                    continue

            # Scrape menus for open locations
            print("\nBeginning menu scraping for open locations...")
            for location in self.locations.values():
                if location.open_today and location.menus:
                    print(f"\nScraping menu for: {location.name}")
                    self._scrape_location_menu(location)

        except Exception as e:
            print(f"\nError during location scraping: {str(e)}")
            if self.driver:
                print("Final URL:", self.driver.current_url)
                print("Page source preview:", self.driver.page_source[:500])
            raise

    def _scrape_location_menu(self, location: DiningLocation):
        """Scrape menu for a specific location."""
        try:
            if not self._safe_get_page(location.url):
                print(f"Skipping menu scrape for {location.name} - could not load page")
                return

            # Wait for menu tabs
            try:
                menu_tabs = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.cu-dining-menu-tabs'))
                )
                print("Found menu tabs")
            except TimeoutException:
                print(f"No menu tabs found for {location.name}")
                return

            # Process each meal type
            for meal_type in location.menus.keys():
                print(f"\nProcessing {meal_type} menu...")
                try:
                    # Find and click meal type button
                    button = None
                    button_attempts = 0
                    while button_attempts < 3:
                        try:
                            button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, f"//button[text()='{meal_type}' and contains(@class, 'ng-binding')]")
                                )
                            )
                            break
                        except TimeoutException:
                            button_attempts += 1
                            if button_attempts < 3:
                                print(f"Retrying to find {meal_type} button...")
                                time.sleep(random.uniform(2, 3))
                            else:
                                print(f"Could not find button for {meal_type}")
                                continue

                    if not button:
                        continue

                    # Click the button and wait for content
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(random.uniform(1, 2))
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(random.uniform(2, 3))

                    # Find all stations
                    stations = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located(
                            (By.XPATH, ".//div[div[contains(@class, 'meal-items')]]")
                        )
                    )
                    
                    # Process each station
                    for station in stations:
                        try:
                            station_name = station.find_element(By.CSS_SELECTOR, '.station-title').text
                            if not station_name:
                                continue

                            if station_name not in location.menus[meal_type]:
                                location.menus[meal_type][station_name] = {}

                            # Process meal items at this station
                            meal_items = station.find_elements(By.CSS_SELECTOR, '.meal-item')
                            if meal_items:
                                print(f"Found {len(meal_items)} items at {station_name}")
                                for meal_item in meal_items:
                                    menu_item = self._parse_menu_item(meal_item)
                                    location.menus[meal_type][station_name][menu_item.title] = menu_item
                            else:
                                print(f"No items found at {station_name}")

                        except Exception as e:
                            print(f"Error processing station in {meal_type}: {str(e)}")
                            continue

                except Exception as e:
                    print(f"Error processing {meal_type} menu: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error scraping menu for {location.name}: {str(e)}")
            if self.driver:
                print("Current URL:", self.driver.current_url)
                print("Page source preview:", self.driver.page_source[:200])




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





