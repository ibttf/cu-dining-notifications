
import boto3
import json
from botocore.exceptions import ClientError
# Initialize SES client
ses = boto3.client('ses', region_name='us-east-1')  # Replace 'us-east-1' with your region

# Delete existing template (if it exists) and create the new one
try:
    # Delete the template if it already exists
    ses.delete_template(TemplateName='ColumbiaDiningMenuUpdate')
    print("Existing template deleted.")
except ClientError as e:
    if e.response['Error']['Code'] == 'TemplateDoesNotExist':
        print("Template does not exist, so no need to delete.")
    else:
        print(f"Error checking/deleting template: {e.response['Error']['Message']}")
