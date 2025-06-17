from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize SendGrid
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
REPLY_FROM_EMAIL = os.getenv("REPLY_FROM_EMAIL")

def send_email(to_email: str, subject: str, body: str):
    """
    Send an email using SendGrid
    """
    message = Mail(
        from_email=REPLY_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=body.replace('\n', '<br>')
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}. Status code: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False

class WebhookData(BaseModel):
    email_body: str
    sender_email: str
    domain: Optional[str] = "general"

@app.post("/webhook")
async def webhook_handler(request: Request) -> Dict[str, Any]:
    """
    Handle incoming webhook requests from Instantly.ai
    """
    try:
        raw_data = await request.body()
        try:
            json_data = await request.json()
        except Exception:
            import json
            json_data = json.loads(raw_data.decode("utf-8").replace('\n', '\\n').replace('\r', '').replace('"', '\\"'))

        email_body = json_data.get("email_body", "").replace('\r', '')
        sender_email = json_data.get("sender_email", "")
        domain = json_data.get("domain", "general")

        logger.info(f"Sanitized webhook data from {sender_email}")

        # Generate GPT response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful SDR replying to leads via email."},
                {"role": "user", "content": email_body}
            ]
        )

        reply_text = response.choices[0].message.content

        # Send reply email
        email_sent = send_email(
            to_email=sender_email,
            subject="RE: Your recent inquiry",
            body=reply_text
        )

        return {
            "status": "success",
            "reply": reply_text,
            "sender": sender_email,
            "email_sent": email_sent
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 