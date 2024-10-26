from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

url = 'https://dining.columbia.edu/'
driver = webdriver.Chrome()  # Make sure you have ChromeDriver installed and in your PATH

# # Step 2: Use Selenium to fetch the HTML content from the URL
# driver.get(url)

# # Optional: Wait for the page to load completely
# time.sleep(5)  # Adjust the sleep time as needed

# # Step 3: Find the relevant div containing the dining data
# dining_section = driver.find_element(By.ID, "cu_dining_open_now-19925")


# locations = dining_section.find_elements(By.CSS_SELECTOR, '.col-md-6.p-0')
# open_times = dining_section.find_elements(By.CSS_SELECTOR, '.open-time')
# is_opens=dining_section.find_elements(By.CSS_SELECTOR, '.status')

# locations_map={}
# for location, open_time, is_open in zip(locations, open_times, is_opens):
#     print(location.text) #name of the location
#     locations_map[location.text]=True if is_open.text=='OPEN' else False
#     print(open_time.text) #times that hte location is open: 12:00 PM - 10:00AM, 7:30 AM - 8:00 PM
#     print(is_open.text) #either OPEN or CLOSED


menus_db= {} #LOCATION : {station: {meal_item: [allergens]}}


# JOHN JAY
locations_map={'John Jay Dining Hall':False, "JJ's Place":True}

if locations_map['John Jay Dining Hall']:
    try:
        new_url = 'https://dining.columbia.edu/content/john-jay-dining-hall'
        driver.get(new_url)
        menus = driver.find_element(By.ID, 'cu-dining-meals')
        button = driver.find_element(By.XPATH, "//button[text()='All']")
        button.click()
        #find all divs that contain meal items
        parent_divs = driver.find_elements(By.XPATH, ".//div[div[contains(@class, 'meal-items')]]")
        with open('dining.txt', 'w') as f:
            for parent_div in parent_divs:
                f.write(parent_div.get_attribute('outerHTML'))
                f.write('\n')
        for parent_div in parent_divs:

            #each of these divs 
            station_title = parent_div.find_element(By.CSS_SELECTOR, '.station-title')
            print('STATION', station_title.text)
            meal_items=parent_div.find_elements(By.CSS_SELECTOR, '.meal-item')
            for meal_item in meal_items:
                title = meal_item.find_element(By.CSS_SELECTOR, '.meal-title')
                # print(title.text)
            print('\n')
            menus_db[station_title.text]=[meal_item.text for meal_item in meal_items]
        
        #ADDING TO OUR FAKE DATABASE
        

    except Exception as e:
        #case: ALL button can't be found
        print('Could not find the button')
        print(e)


#JJ'S PLACE

# Dismiss any overlays (e.g., Privacy Notice)
try:
    privacy_notice = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, "cu-privacy-notice"))
    )
    if privacy_notice.is_displayed():
        driver.find_element(By.ID, "close-privacy-notice").click()
except Exception:
    print("No privacy notice found, or unable to close it.")


# Check for and close any overlay if it exists
def close_overlay():
    try:
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "cu-privacy-notice"))
        )
        close_button = driver.find_element(By.ID, "close-privacy-notice")
        driver.execute_script("arguments[0].click();", close_button)  # Click using JavaScript
        print("Overlay closed.")
    except Exception:
        print("No overlay found.")

# Main function to select menu tabs and retrieve data
if locations_map["JJ's Place"]:
    menus_db["JJ's Place"] = {'Breakfast': {}, 'Daily': {}, 'Late Night': {}}
    try:
        new_url = 'https://dining.columbia.edu/content/jjs-place-0'
        driver.get(new_url)
        
        # Attempt to close any overlay that may block the view
        close_overlay()
        
        # Find the menu tabs container
        menu_tabs = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.cu-dining-menu-tabs'))
        )
        
        # Loop through each meal type
        for meal_type in ['Breakfast', 'Daily', 'Late Night']:
            button = None
            for attempt in range(3):  # Retry mechanism for each button
                try:
                    # Locate button by text and class
                    button = WebDriverWait(menu_tabs, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f"//button[text()='{meal_type}' and contains(@class, 'ng-binding')]"))
                    )
                    
                    # Scroll into view and click using JavaScript to avoid click interception
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    driver.execute_script("arguments[0].click();", button)  # Click via JavaScript
                    print(f"Clicked '{meal_type}' tab.")
                    time.sleep(1)  # Allow time for content to load after clicking
                    break  # Exit retry loop on successful click
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed for meal type '{meal_type}': {e}")
                    time.sleep(2)  # Wait before retrying
            else:
                print(f"Could not click button for meal type '{meal_type}'. Moving to next meal type.")
                continue
            
            # Retrieve and process data for each station under the meal type
            parent_divs = driver.find_elements(By.XPATH, ".//div[div[contains(@class, 'meal-items')]]")
            for parent_div in parent_divs:
                station_title = parent_div.find_element(By.CSS_SELECTOR, '.station-title')
                menus_db["JJ's Place"][meal_type][station_title.text] = menus_db["JJ's Place"][meal_type].get(station_title.text, {})
                
                meal_items = parent_div.find_elements(By.CSS_SELECTOR, '.meal-item')
                for meal_item in meal_items:
                    title = meal_item.find_element(By.CSS_SELECTOR, '.meal-title').text
                    
                    # Check dietary information
                    is_vegetarian = is_vegan = is_halal = False
                    try:
                        dietary_text = meal_item.find_element(By.CSS_SELECTOR, 'div.meal-prefs strong').text
                        is_vegetarian = "Vegetarian" in dietary_text
                        is_halal = "Halal" in dietary_text
                        is_vegan = "Vegan" in dietary_text
                    except Exception:
                        pass

                    # Get allergens
                    try:
                        allergens = meal_item.find_element(By.TAG_NAME, 'em').text
                        allergens = allergens.split("Contains: ")[1].split(", ")
                    except Exception:
                        allergens = []

                    # Store data in the menu database
                    menus_db["JJ's Place"][meal_type][station_title.text][title] = {
                        "allergens": allergens,
                        "vegetarian": is_vegetarian or is_vegan,
                        "vegan": is_vegan,
                        'halal': is_halal
                    }
                    print(f"{title}: Vegetarian - {is_vegetarian}, Vegan - {is_vegan}, Halal - {is_halal}, Allergens - {allergens}")
                print('\n')
    except Exception as e:
        print("Menu not available")
        print(e)
    

# Step 6: Close the WebDriver
driver.quit()