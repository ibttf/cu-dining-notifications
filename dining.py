from selenium import webdriver
from selenium.webdriver.common.by import By
import time

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


# Getting John Jay Dining Hall Menu
# if locations_map['John Jay Dining Hall']:
new_url = 'https://dining.columbia.edu/content/john-jay-dining-hall'
driver.get(new_url)
menus = driver.find_element(By.ID, 'cu-dining-meals')

# ALL
button = driver.find_element(By.XPATH, "//button[text()='ALL']")
# Click the button
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
        print(title.text)
    print('\n')




# Step 6: Close the WebDriver
driver.quit()