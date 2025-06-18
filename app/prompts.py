"""
This module contains all the prompts used in the application.
Each prompt is defined as a constant for easy maintenance and updates.
"""

# Email response prompt
EMAIL_RESPONSE_PROMPT = """You are a helpful SDR replying to leads via email. 
Provide your response in the following JSON format:
{
    "subject": "Email subject line",
    "body": "Email body content in HTML format"
}
Make sure the response is valid JSON with both subject and body fields.
Note: Do not include the json output inside the ```json``` tags.
"""

# You can add more prompts here as needed
# For example:
# SALES_PROMPT = "..."
# SUPPORT_PROMPT = "..."
# etc. 