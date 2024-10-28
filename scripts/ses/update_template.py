import boto3
import json
from botocore.exceptions import ClientError

# Initialize SES client
ses = boto3.client('ses', region_name='us-east-1')  # Replace 'us-east-1' with your region

# Define the template

template_data = {
    "Template": {
        "TemplateName": "ColumbiaDiningMenuUpdate",
        "SubjectPart": "{{subject}}",
        "TextPart": (
            "{{subject}} , {{date}}\n\n"
            "{{date}}\n\n"
            "{{#each locations}}\n"
            "* {{name}} - {{open_times}}\n\n"
            "{{#each meals}}\n"
            "== {{meal_type}} ==\n\n"
            "{{#each stations}}\n"
            "[{{station_name}}]\n"
            "{{#each items}}\n"
            "- {{name}}{{#if dietary}} ({{dietary}}){{/if}}{{#if allergens}} "
            "Contains: {{allergens}}{{/if}}\n\n"
            "{{/each}}\n{{/each}}\n{{/each}}\n{{/each}}\n\n"
            "Closed today:\n\n"
            "{{#each closed_locations}}* {{this}}\n{{/each}}\n\n"
            "This menu update is based on your dietary preferences and restrictions.\n"
            "To update your preferences, please visit your dining dashboard.\n"
        ),
        "HtmlPart": """
            <div style="font-family: Arial, sans-serif; color: #1e3a8a; max-width: 1200px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
                
                <h1 style="color: #1e3a8a; font-size: 24px; border-bottom: 2px solid #1e3a8a; padding-bottom: 10px; margin-bottom: 30px;">Columbia Dining Menus - {{date}}</h1>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px;">
                    <div style="background: #eff6ff; border-radius: 8px; padding: 20px;">
                        <h2 style="color: #1e3a8a; font-size: 20px; margin: 0 0 15px 0; padding-bottom: 8px; border-bottom: 2px solid #bfdbfe;">Open Today</h2>
                        {{#each locations}}
                        <div style="background: white; padding: 10px; margin: 8px 0; border-radius: 4px;">
                            <span style="font-weight: bold; color: #1e3a8a;">{{name}}</span>
                            <span style="color: #2563eb; margin-left: 10px;">{{open_times}}</span>
                        </div>
                        {{/each}}
                    </div>
                    
                    <div style="background: #eff6ff; border-radius: 8px; padding: 20px;">
                        <h2 style="color: #1e3a8a; font-size: 20px; margin: 0 0 15px 0; padding-bottom: 8px; border-bottom: 2px solid #bfdbfe;">Closed Today</h2>
                        {{#each closed_locations}}
                        <div style="background: white; padding: 10px; margin: 8px 0; border-radius: 4px;">
                            <span style="font-weight: bold; color: #1e3a8a;">{{this}}</span>
                        </div>
                        {{/each}}
                    </div>
                </div>
                
                {{#each locations}}
                <div style="background: white; border-radius: 8px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(30, 58, 138, 0.1);">
                    <h2 style="font-size: 20px; margin: 0 0 5px 0; color: #1e3a8a;">{{name}}</h2>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
                        {{#each meals}}
                        <div style="background: #f8fafc; padding: 15px; border-radius: 4px;">
                            <h3 style="font-size: 18px; color: #1e3a8a; margin: 0 0 15px 0; padding-bottom: 8px; border-bottom: 1px solid #bfdbfe;">{{meal_type}}</h3>
                            
                            {{#each stations}}
                            <div style="margin-bottom: 15px;">
                                <h4 style="font-size: 16px; color: #3b82f6; margin: 15px 0 8px 0;">{{station_name}}</h4>
                                
                                {{#each items}}
                                <div style="font-size: 14px; margin: 8px 0; padding-left: 15px; border-left: 2px solid #bfdbfe;">
                                    <strong>{{name}}</strong>
                                    {{#if dietary}}
                                    <span style="color: #2563eb; font-style: italic;"> ({{dietary}})</span>
                                    {{/if}}
                                    {{#if allergens}}
                                    <span style="color: #1e3a8a; font-size: 12px; display: block; margin-top: 3px;">Contains: {{allergens}}</span>
                                    {{/if}}
                                </div>
                                {{/each}}
                            </div>
                            {{/each}}
                        </div>
                        {{/each}}
                    </div>
                </div>
                {{/each}}
                
                <p style="margin-top: 30px; color: #64748b; text-align: center; border-top: 1px solid #bfdbfe; padding-top: 20px;">
                    This menu update is based on your dietary preferences and restrictions. To update it, just go back to <a href="https://www.cudiningnotifications.com" style="color: #1e3a8a; text-decoration: none;">cudiningnotifications.com</a> and resubmit the thingy.
                </p>
            </div>
        """
    }
}
# Create the new template
try:
    response = ses.create_template(Template=template_data['Template'])
    print("Template created successfully.")
    print(json.dumps(response, indent=2))
except ClientError as e:
    print(f"Error creating template: {e.response['Error']['Message']}")