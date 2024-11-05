import json
import boto3
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv
import traceback
import random
import os

load_dotenv()
# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS services
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
ses = boto3.client('ses', region_name='us-east-1')
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

class ColumbiaDiningScraper:
    BASE_URL = 'https://dining.columbia.edu/'
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.subjects = [
            'Wake up fucker!!!!', 'rise and shine bitchboy', 'Good morning big back', 
            "Hola papi <3333", "Ohaiyo onii-chan", "pls text back the kids miss you", 
            "Get out of bed; they're not texting you back", "Another morning spent single! Here's the menus",
            "You're never getting married. Here's the menus", "om nom nom nom", 
            "hello my sweet darling... wake up", "menus are out!",
            "joonha if you're reading this, please text me back"
        ]
        self.closed_locations = []
        # Dictionary of all possible locations
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


    def _fetch_page_html(self, url: str) -> str:
        """Fetch page HTML using Zyte API."""
        try:
            response = requests.post(
                "https://api.zyte.com/v1/extract",
                auth=(self.api_key, ""),
                json={
                    "url": url,
                    "browserHtml": True,
                }
            )
            response.raise_for_status()
            return response.json()["browserHtml"]
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            raise

    def scrape_locations(self):
        """Scrape all dining locations and their menus."""
        try:
            print("Starting to scrape locations")
            html_content = self._fetch_page_html(self.BASE_URL)
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find all dining and retail locations
            all_locations = soup.select('.dining-location, .retail-location')
            print(f"Found {len(all_locations)} locations")

            # Reset closed locations list
            self.closed_locations = []

            # Process each location
            for loc in all_locations:
                try:
                    title_element = loc.select_one('.name a')
                    if not title_element:
                        continue

                    title = title_element.text.strip()
                    if not title:
                        continue

                    print(f"Processing location: {title}")

                    if title in self.locations:
                        # Check if location is open
                        open_time_element = loc.select_one('.open-time')
                        open_times = open_time_element.text.strip() if open_time_element else ""
                        
                        is_open = bool(open_times)
                        self.locations[title].open_today = is_open
                        self.locations[title].open_times = open_times

                        if is_open:
                            print(f"Location {title} is open: {open_times}")
                        else:
                            self.closed_locations.append(title)
                            print(f"Location {title} is closed")

                except Exception as e:
                    print(f"Error processing location: {e}")
                    continue

            # Scrape menus for open locations
            for location in self.locations.values():
                if location.open_today and location.menus:
                    self._scrape_location_menu(location)

        except Exception as e:
            print(f"Error during scraping: {e}")
            raise
    def _scrape_location_menu(self, location: DiningLocation):
        """Scrape menu for a specific location."""
        print(f"\nScraping menu for {location.name}")
        
        try:
            html_content = self._fetch_page_html(location.url)
            soup = BeautifulSoup(html_content, 'html.parser')

            # Debug print the full HTML to understand the structure
            print("Full page HTML:")
            print(soup.prettify()[:2000])  # First 2000 chars to see the structure

            # Look for the menu container
            menu_container = soup.select_one('.menu-items-wrapper, .dining-menu-wrapper, .location-menu')
            if not menu_container:
                print("No menu container found, trying alternative selectors")
                menu_container = soup.select_one('[class*="menu"]')  # More permissive selector

            if not menu_container:
                print(f"No menu content found for {location.name}")
                return

            # Get all menu sections
            menu_sections = menu_container.select('.meal-period, .menu-section, [class*="meal"]')
            print(f"Found {len(menu_sections)} menu sections")

            for section in menu_sections:
                # Try to determine the meal type from various possible elements
                meal_type = None
                meal_header = section.select_one('.meal-period-header, .menu-header, h2, h3')
                if meal_header:
                    meal_type = meal_header.text.strip()
                    print(f"Found meal type: {meal_type}")

                # If we can't determine the meal type, try the section's class or data attributes
                if not meal_type:
                    for attr in section.attrs.get('class', []):
                        if 'breakfast' in attr.lower():
                            meal_type = 'Breakfast'
                        elif 'lunch' in attr.lower():
                            meal_type = 'Lunch'
                        elif 'dinner' in attr.lower():
                            meal_type = 'Dinner'
                        elif 'late' in attr.lower():
                            meal_type = 'Late Night'

                # Map the found meal type to our expected meal types
                mapped_meal_type = None
                for expected_type in location.menus.keys():
                    if meal_type and (expected_type.lower() in meal_type.lower() or 
                                    meal_type.lower() in expected_type.lower()):
                        mapped_meal_type = expected_type
                        break

                if not mapped_meal_type:
                    print(f"Could not map found meal type '{meal_type}' to expected types")
                    continue

                print(f"Processing mapped meal type: {mapped_meal_type}")

                # Find all stations in this section
                stations = section.select('.station-wrapper, .station, [class*="station"]')
                print(f"Found {len(stations)} stations")

                for station in stations:
                    station_title = station.select_one('.station-title, .station-name, h3, h4')
                    if not station_title:
                        continue
                        
                    station_name = station_title.text.strip()
                    print(f"Processing station: {station_name}")

                    if station_name not in location.menus[mapped_meal_type]:
                        location.menus[mapped_meal_type][station_name] = {}

                    # Look for menu items with more flexible selectors
                    meal_items = station.select('.meal-item, .menu-item, [class*="item"]')
                    print(f"Found {len(meal_items)} items in station {station_name}")

                    for meal_item in meal_items:
                        menu_item = self._parse_menu_item(meal_item)
                        if menu_item.title != "Unknown":  # Only add if we successfully parsed the item
                            location.menus[mapped_meal_type][station_name][menu_item.title] = menu_item

        except Exception as e:
            print(f"Error scraping menu for {location.name}: {e}")
            print(traceback.format_exc())

    def _parse_menu_item(self, meal_item_element) -> MenuItem:
        """Parse a menu item from BeautifulSoup element with more flexible selectors."""
        try:
            # Try multiple selectors for the title
            title_element = (meal_item_element.select_one('.meal-title, .item-title, .name, h4, strong') or 
                            meal_item_element.find(['h4', 'strong', 'span']))
            title = title_element.text.strip() if title_element else "Unknown"
            print(f"Found title: {title}")
            
            # Try multiple selectors for dietary information
            dietary_elements = meal_item_element.select('.dietary, .meal-prefs, [class*="dietary"], [class*="pref"]')
            dietary_text = ' '.join(elem.text.strip() for elem in dietary_elements)
            print(f"Found dietary text: {dietary_text}")
            
            # More flexible dietary checking
            is_vegetarian = any(marker in dietary_text.lower() 
                            for marker in ['vegetarian', 'vegan', 'plant-based'])
            is_vegan = 'vegan' in dietary_text.lower()
            is_halal = 'halal' in dietary_text.lower()

            # Try multiple selectors for allergens
            allergens = []
            allergen_elements = meal_item_element.select('.allergens, .contains, em, [class*="allerg"]')
            for elem in allergen_elements:
                text = elem.text.strip()
                if 'contains' in text.lower():
                    allergens = [a.strip() for a in text.split('Contains:')[1].split(',')]
                    break

            menu_item = MenuItem(
                title=title,
                allergens=allergens,
                is_vegetarian=is_vegetarian,
                is_vegan=is_vegan,
                is_halal=is_halal
            )
            print(f"Created MenuItem: {vars(menu_item)}")
            return menu_item
            
        except Exception as e:
            print(f"Error parsing menu item: {e}")
            print(traceback.format_exc())
            return MenuItem(title="Unknown", allergens=[])


    def format_menu_for_user(self, user: Dict, locations: Dict[str, DiningLocation]) -> List[Dict]:
        """Format menu data according to user preferences."""
        # [This method remains exactly the same as it doesn't involve scraping]
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
                "subject": random.choice(self.subjects),
                "locations": formatted_menu,
                "closed_locations": self.closed_locations
            }
            print("Template data", template_data)
            
            response = ses.send_templated_email(
                Source='roy@cudiningnotifications.com',
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
    successful_sends = []
    try:
        scraper = ColumbiaDiningScraper(api_key=os.getenv('ZYTE_API_KEY'))
        
        # Scrape all locations
        scraper.scrape_locations()
        
        # Get all users from DynamoDB
        response = users_table.scan()
        users = response['Items']
        print(f"Found {len(users)} users")
        
        # Debug print of locations data
        print("Locations data:")
        for loc_name, loc_data in scraper.locations.items():
            print(f"\nLocation: {loc_name}")
            print(f"Open today: {loc_data.open_today}")
            print(f"Open times: {loc_data.open_times}")
            print("Menus:")
            for meal_type, stations in loc_data.menus.items():
                print(f"  {meal_type}: {len(stations)} stations")
                for station_name, items in stations.items():
                    print(f"    {station_name}: {len(items)} items")

        # Process menu for each user and send email
        for user in users:
            print(f"\nProcessing user: {user.get('email')}")
            print(f"User preferences: {json.dumps(user, indent=2)}")
            
            formatted_menu = scraper.format_menu_for_user(user, scraper.locations)
            print(f"Formatted menu items: {len(formatted_menu)}")
            
            if formatted_menu:
                print("Menu content:")
                print(json.dumps(formatted_menu, indent=2))
                
                try:
                    scraper.send_email(user['email'], formatted_menu)
                    successful_sends.append(user['email'])
                    print(f"Successfully sent email to {user['email']}")
                except Exception as email_error:
                    print(f"Error sending email to {user['email']}: {str(email_error)}")
            else:
                print(f"No matching menu items found for user {user['email']}")
        
        print(f"\nSuccessful sends: {successful_sends}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Process completed',
                'successful_sends': successful_sends,
                'total_users': len(users)
            })
        }
        
    except Exception as e:
        print(f"Error in lambda execution: {e}")

        print("Full traceback:")
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        }
if __name__ == "__main__":
    lambda_handler(None, None)


#random bash script to move the chromedriver to the right place in the ec2 instance.

    # cd /tmp/
    # sudo wget https://chromedriver.storage.googleapis.com/80.0.3987.106/chromedriver_linux64.zip
    # sudo unzip chromedriver_linux64.zip
    # sudo mv chromedriver /usr/bin/chromedriver
    # chromedriver --version



