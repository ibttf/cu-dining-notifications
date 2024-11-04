from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tempfile import mkdtemp
import time
import random

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)

def test_dining_website():
    driver = None
    try:
        # Setup Chrome options
        options = webdriver.ChromeOptions()
        service = Service("/usr/local/bin/chromedriver")
        options.binary_location = '/usr/bin/google-chrome-stable'
        
        # Enhanced browser configuration
        user_agent = get_random_user_agent()
        options.add_argument(f'user-agent={user_agent}')
        
        # Add required arguments
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-browser-side-navigation')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-data-dir={mkdtemp()}')
        options.add_argument('--headless=new')
        
        # Add experimental options
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Initialize driver
        print("Starting Chrome...")
        driver = webdriver.Chrome(options=options, service=service)
        
        # Execute CDP commands to modify browser characteristics
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": user_agent,
            "platform": "Linux x86_64"
        })
        
        # Modify navigator properties
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
        
        print("Chrome started successfully")
        print(f"Using User-Agent: {user_agent}")
        
        # Access the website with retry mechanism
        url = 'https://dining.columbia.edu/'
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"\nAttempt {retry_count + 1} of {max_retries}")
                driver.get(url)
                
                # Initial wait
                time.sleep(random.uniform(5, 8))
                
                print(f"Current title: {driver.title}")
                print(f"Current URL: {driver.current_url}")
                
                # Check if we're on the Cloudflare page
                if "Just a moment" in driver.title:
                    print("Detected Cloudflare challenge page")
                    # Wait longer for Cloudflare challenge to complete
                    time.sleep(random.uniform(10, 15))
                
                # Try to find content
                try:
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.dining-location, .retail-location'))
                    )
                    print("Successfully found dining location element!")
                    break
                    
                except TimeoutException:
                    print("Timeout waiting for content")
                    print("Current page source preview:", driver.page_source[:200])
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(random.uniform(3, 5))
                        continue
            
            except Exception as e:
                print(f"Error during attempt {retry_count + 1}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(random.uniform(3, 5))
                    continue
                raise
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        if driver:
            print(f"Final page source: {driver.page_source[:500]}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    test_dining_website()
