from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional
import os
from dotenv import load_dotenv
import openai
from pydantic import BaseModel
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import json

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

# Initialize OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# SendGrid config
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
REPLY_FROM_EMAIL = os.getenv("REPLY_FROM_EMAIL")


def send_email(to_email: str, subject: str, body: str):
    try:
        message = Mail(
            from_email=REPLY_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=body.replace('\n', '<br>')
        )
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
async def webhook_handler(request: Request):
    """
    Handle incoming webhook requests from Instantly.ai with fallback JSON handling.
    """
    try:
        raw_body = await request.body()
        try:
            data = await request.json()
        except Exception:
            logger.warning("Standard JSON parse failed, attempting fallback...")
            try:
                data = json.loads(raw_body.decode("utf-8"))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Malformed JSON: {str(e)}")

        email_body = data.get("email_body", "")
        sender_email = data.get("sender_email", "")
        domain = data.get("domain", "general")

        logger.info(f"Received webhook from {sender_email} in domain: {domain}")

        # Generate GPT response
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful SDR replying to leads via email."},
                {"role": "user", "content": email_body}
            ]
        )

        reply_text = response['choices'][0]['message']['content']

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
        raise HTTPException(status_code=500, detail=f"Webhook error: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
