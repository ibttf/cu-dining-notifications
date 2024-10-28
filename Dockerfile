# Use the appropriate base image
FROM umihico/aws-lambda-selenium-python:latest

# Install boto3
RUN pip3 install boto3

# Add Chrome options for running in Lambda environment
ENV PYTHONPATH=/var/task
ENV PATH="/var/task:${PATH}"

# Create necessary directories
RUN mkdir -p /tmp/chrome/user-data
RUN mkdir -p /tmp/chrome/data-path

# Set Chrome flags for running in Lambda
# ENV CHROME_FLAGS="--headless --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-dev-tools --no-zygote --single-process --data-path=/tmp/chrome/data-path --disk-cache-dir=/tmp/chrome/data-path"

# Copy function code
COPY main.py ./

# Set the CMD to your handler
CMD [ "main.lambda_handler" ]