
import boto3

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # replace with your region
table = dynamodb.Table('users') 
# Test user data

test_users = [
    {
        "email": "churlee12@gmail.com",
        "is_vegetarian": True,
        "is_vegan": False,
        "unavailable_foods": ["peanut", "shellfish"]
    }
]

# Insert data
for user in test_users:
    try:
        table.put_item(Item=user)
        print(f"Inserted user {user['email']} successfully.")
    except Exception as e:
        print(f"Error inserting user {user['email']}: {e}")
