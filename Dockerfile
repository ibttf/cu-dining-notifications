# Use the latest version of the image
FROM umihico/aws-lambda-selenium-python:latest
# Copy function code
COPY main.py ./
# Set the CMD to your handler
CMD [ "main.lambda_handler" ]