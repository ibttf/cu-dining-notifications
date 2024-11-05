import boto3

# Initialize the SES client
ses_client = boto3.client('ses', region_name='us-east-1')  # Replace with your region if different

# Define the template data
template_data = {
    "date": "Monday, November 04, 2024",
    "subject": "om nom nom nom",
    "locations": [
        {
            "name": "John Jay Dining Hall",
            "open_times": "10:00 AM - 6:00 PM",
            "meals": [
                {
                    "meal_type": "Dinner",
                    "stations": [
                        {
                            "station_name": "Main Line",
                            "items": [
                                {"name": "Pepper Steak", "dietary": None, "allergens": "Soy"},
                                {"name": "Jasmine Rice", "dietary": "Vegan, Halal", "allergens": None}
                            ]
                        }
                    ]
                }
            ]
        }
    ],
    "closed_locations": ["Ferris Booth Commons", "Faculty House"]
}

# Convert template data to JSON
import json
template_data_json = json.dumps(template_data)

# Send the templated email
try:
    response = ses_client.send_templated_email(
        Source='roy@cudiningnotificatinos.com',  # Replace with your SES-verified sender email
        Destination={
            'ToAddresses': ['churlee12@gmail.com']  # Replace with the recipient email
        },
        Template='ColumbiaDiningMenuUpdate',  # Template name
        TemplateData=template_data_json
    )
    print("Email sent! Message ID:", response['MessageId'])
except Exception as e:
    print("Error sending email:", e)
