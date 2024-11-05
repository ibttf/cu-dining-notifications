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

    def _fetch_page_html(self, url: str, browser_commands: List[Dict] = None) -> str:
        """Fetch page HTML using Zyte API with JavaScript rendering and optional browser commands."""
        try:
            payload = {
                "url": url,
                "javascript": True,     # Enable JavaScript rendering
                "browserHtml": True     # Get the full HTML after JS execution
            }

            if browser_commands:
                payload["browserCommands"] = browser_commands

            print(f"Sending request to Zyte API for {url} with payload: {json.dumps(payload)}")

            response = requests.post(
                "https://api.zyte.com/v1/extract",
                auth=(self.api_key, ""),
                json=payload
            )
            response.raise_for_status()
            json_response = response.json()
            # Return the browser HTML if available
            if "browserHtml" in json_response:
                print(f"Received browserHtml for {url}")
                return json_response["browserHtml"]
            else:
                print(f"Error: No 'browserHtml' in Zyte API response for {url}")
                print(f"Full response content: {json_response}")
                raise ValueError("No browserHtml in response")
        except Exception as e:
            print(f"Error fetching page {url}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Full error response: {e.response.text}")
            raise

    def scrape_locations(self):
        """Scrape all dining locations and their open status."""
        try:
            print("Starting to scrape locations")
            html_content = self._fetch_page_html(self.BASE_URL)
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find all dining and retail locations
            all_locations = soup.select('.location')
            print(f"Found {len(all_locations)} locations")

            # Reset closed locations list
            self.closed_locations = []

            # Process each location
            for loc in all_locations:
                try:
                    # Get the title
                    title_element = loc.select_one('.name a')
                    if not title_element:
                        continue

                    title = title_element.text.strip()
                    if not title:
                        continue

                    print(f"Processing location: {title}")

                    if title in self.locations:
                        # Get open times
                        open_time_element = loc.select_one('.open-time')
                        open_times = open_time_element.text.strip() if open_time_element else ""

                        # Get status
                        status_element = loc.select_one('.status')
                        status_text = status_element.text.strip() if status_element else ""
                        is_open = "Open" in status_text

                        self.locations[title].open_today = is_open
                        self.locations[title].open_times = open_times

                        if is_open:
                            print(f"Location {title} is open: {open_times}")
                        else:
                            self.closed_locations.append(title)
                            print(f"Location {title} is closed")

                except Exception as e:
                    print(f"Error processing location {title}: {e}")
                    continue

            # Scrape menus for open locations
            for location in self.locations.values():
                if location.open_today and location.menus:
                    self._scrape_location_menu(location)

        except Exception as e:
            print(f"Error during scraping: {e}")
            print(traceback.format_exc())
            raise

    def _scrape_location_menu(self, location: DiningLocation):
        """Scrape menu for a specific location."""
        print(f"Scraping menu for {location.name}")

        try:
            for meal_type in location.menus.keys():
                print(f"Processing meal type: {meal_type}")

                # JavaScript to click the button with innerText matching meal_type
                # The buttons have attribute data-ng-click="setMenu(menu)"
                js_click_button = f"""
                    var buttons = document.querySelectorAll('button[data-ng-click="setMenu(menu)"]');
                    for (var i = 0; i < buttons.length; i++) {{
                        if (buttons[i].innerText.trim() === '{meal_type}') {{
                            buttons[i].click();
                            break;
                        }}
                    }}
                """

                browser_commands = [
                    {"command": "waitForElement", "selector": "button[data-ng-click='setMenu(menu)']", "timeout": 5000},
                    {"command": "evaluate", "expression": js_click_button},
                    {"command": "wait", "timeout": 2000}
                ]

                html_content = self._fetch_page_html(location.url, browser_commands=browser_commands)
                soup = BeautifulSoup(html_content, 'html.parser')

                # Find all menu sections for this meal type
                menu_divs = soup.find_all('div', class_='menus')
                if not menu_divs:
                    print(f"Warning: No menu items found for {meal_type} at {location.name}")
                    continue

                print(f"Found {len(menu_divs)} menu sections for {meal_type} at {location.name}")

                for menu_div in menu_divs:
                    # For each station in this menu
                    station_divs = menu_div.find_all('div', class_='wrapper')
                    for station_div in station_divs:
                        # Get station name
                        station_name_element = station_div.find('h2', class_='station-title')
                        station_name = station_name_element.text.strip() if station_name_element else "Unknown Station"
                        print(f"Processing station: {station_name}")

                        # Get meal items
                        meal_items_div = station_div.find('div', class_='meal-items')
                        if not meal_items_div:
                            print(f"No meal items found for station {station_name}")
                            continue

                        meal_item_divs = meal_items_div.find_all('div', class_='meal-item')
                        print(f"Found {len(meal_item_divs)} meal items in station {station_name}")

                        for item_element in meal_item_divs:
                            menu_item = self._parse_menu_item(item_element)
                            if menu_item.title != "Unknown":
                                # Initialize the station dictionary if not present
                                if station_name not in location.menus[meal_type]:
                                    location.menus[meal_type][station_name] = {}
                                # Add the menu item to the station
                                location.menus[meal_type][station_name][menu_item.title] = menu_item

        except Exception as e:
            print(f"Error scraping menu for {location.name}: {e}")
            print(traceback.format_exc())

    def _parse_menu_item(self, meal_item_element) -> MenuItem:
        """Parse a menu item from BeautifulSoup element."""
        try:
            # Extract title
            title_element = meal_item_element.find('h5', class_='meal-title')
            title = title_element.text.strip() if title_element else "Unknown"
            print(f"Found title: {title}")

            # Extract dietary info
            dietary_info_element = meal_item_element.find('div', class_='meal-prefs')
            dietary_text = dietary_info_element.text.strip() if dietary_info_element else ""
            print(f"Found dietary text: {dietary_text}")

            is_vegetarian = 'Vegetarian' in dietary_text
            is_vegan = 'Vegan' in dietary_text
            is_halal = 'Halal' in dietary_text

            # Extract allergens
            allergens_info_element = meal_item_element.find('div', class_='meal-allergens')
            allergens_text = allergens_info_element.text.strip() if allergens_info_element else ""
            print(f"Found allergens text: {allergens_text}")

            # Extract allergens list
            allergens = []
            if 'Contains:' in allergens_text:
                allergens_text = allergens_text.replace('Contains:', '').strip()
                allergens = [a.strip() for a in allergens_text.split(',')]

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



