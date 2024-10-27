from selenium import webdriver
from tempfile import mkdtemp
from selenium.webdriver.common.by import By
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event=None, context=None):
    options = webdriver.ChromeOptions()
    service = webdriver.chrome.service.Service("/opt/chromedriver")

    # Set Chrome binary location
    options.binary_location = '/opt/chrome/chrome'
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")

    chrome = None
    try:
        # Initialize ChromeDriver with options and service
        chrome = webdriver.Chrome(options=options, service=service)
        logger.info("Chrome browser started")
    except Exception as e:
        logger.error(e)
        return "Error starting Chrome browser"
    
    # Access example.com as a test
    chrome.get("https://example.com/")
    page_text = chrome.find_element(by=By.XPATH, value="//html").text
    
    chrome.quit()  # Close the browser
    return page_text

# Bash script to dockerize, build the image, push it to ECR, and deploy to Lambda
# ```bash
#!/bin/bash
"""

# Get AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Clean up any existing images
docker system prune -f

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names docker-selenium || \
aws ecr create-repository \
    --repository-name docker-selenium \
    --image-scanning-configuration scanOnPush=true

# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build --platform linux/amd64 -t docker-selenium .
docker tag docker-selenium:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/docker-selenium:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/docker-selenium:latest   

# Create Lambda function (if it doesn't exist)
aws lambda create-function \
    --function-name docker-selenium-lambda \
    --package-type Image \
    --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/docker-selenium:latest \
    --role arn:aws:iam::252562067238:role/service-role/cu_dining_emailer-role-q8dy1wv0 \
    --timeout 300 \
    --memory-size 2048

# If the function already exists, update its code
aws lambda update-function-code \
    --function-name docker-selenium-lambda \
    --image-uri $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/docker-selenium:latest

# Update function configuration
aws lambda update-function-configuration \
    --function-name docker-selenium-lambda \
    --timeout 300 \
    --memory-size 2048
"""