from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import logging
from typing import Optional
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from bs4 import BeautifulSoup  # HTML to text

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class WebhookData(BaseModel):
    email_body: str
    sender_email: str
    domain: Optional[str] = "general"

    class Config:
        json_schema_extra = {
            "example": {
                "email_body": "Hello, I'm interested in your AI solution",
                "sender_email": "user@example.com",
                "domain": "general"
            }
        }

@app.post("/webhook")
async def webhook_handler(
    request: Request,
    email_body: Optional[str] = Form(None),
    sender_email: Optional[str] = Form(None),
    domain: Optional[str] = Form("general")
):
    try:
        data = {}

        # Try form data first
        if email_body and sender_email:
            data = {
                "email_body": email_body,
                "sender_email": sender_email,
                "domain": domain
            }
        else:
            # Read raw body and try JSON
            raw_body = await request.body()
            raw_text = raw_body.decode("utf-8")
            logger.info(f"Raw request body: {raw_text}")
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                try:
                    email_body_start = raw_text.find('"email_body":') + len('"email_body":')
                    sender_email_start = raw_text.find('"sender_email":') + len('"sender_email":')

                    email_body = raw_text[email_body_start:raw_text.find('",', email_body_start)].strip(' ":')
                    sender_email = raw_text[sender_email_start:raw_text.find('",', sender_email_start)].strip(' ":')
                    domain = "general"

                    data = {
                        "email_body": email_body,
                        "sender_email": sender_email,
                        "domain": domain
                    }
                except Exception as parse_err:
                    logger.warning(f"Failed to parse fallback: {parse_err}")
                    raise HTTPException(status_code=400, detail="Invalid request format. Could not parse data.")

        if not data.get("email_body") or not data.get("sender_email"):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: email_body and sender_email"
            )

        # Sanitize HTML
        email_body_clean = BeautifulSoup(data["email_body"], "html.parser").get_text()
        sender_email = data["sender_email"]
        domain = data.get("domain", "general")

        logger.info(f"Received webhook from {sender_email} in domain: {domain}")

        # GPT response with structured prompt
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": """You are a helpful SDR replying to leads via email. 
                    Provide your response in the following JSON format:
                    {
                        "subject": "Email subject line",
                        "body": "Email body content in HTML format"
                    }
                    Make sure the response is valid JSON with both subject and body fields.
                    Note : Do not include the json output inside the ```json``` tags.
                    """
                },
                {"role": "user", "content": email_body_clean}
            ]
        )

        reply_text = response.choices[0].message.content

        try:
            # Parse the JSON response from GPT
            reply_json = json.loads(reply_text)
            
            # Return structured response
            return {
                "status": "success",
                "sender": sender_email,
                "reply": {
                    "subject": reply_json.get("subject", ""),
                    "body": reply_json.get("body", "")
                }
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT response as JSON: {str(e)}")
            # Fallback to returning the raw response if JSON parsing fails
            return {
                "status": "success",
                "sender": sender_email,
                "reply": {
                    "subject": "Re: Your inquiry",
                    "body": reply_text
                }
            }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
