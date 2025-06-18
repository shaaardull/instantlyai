from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
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

# Initialize OpenAI client
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

@app.post("/webhook", response_model=dict)
async def webhook_handler(
    request: Request,
    email_body: Optional[str] = Form(None),
    sender_email: Optional[str] = Form(None),
    domain: Optional[str] = Form("general")
):
    """
    Handle incoming webhook requests from Instantly.ai.
    Accepts both JSON and form data.
    
    Example JSON payload:
    ```json
    {
        "email_body": "Hello, I'm interested in your AI solution",
        "sender_email": "user@example.com",
        "domain": "general"
    }
    ```
    """
    try:
        # Try to get data from form first
        if email_body and sender_email:
            data = {
                "email_body": email_body,
                "sender_email": sender_email,
                "domain": domain
            }
        else:
            # Try to get data from JSON body
            try:
                data = await request.json()
            except Exception:
                # Try raw body as fallback
                try:
                    raw_body = await request.body()
                    data = json.loads(raw_body.decode("utf-8"))
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid request format. Please provide either form data or JSON with email_body and sender_email"
                    )

        # Validate required fields
        if not data.get("email_body") or not data.get("sender_email"):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: email_body and sender_email"
            )

        email_body = data.get("email_body", "")
        sender_email = data.get("sender_email", "")
        domain = data.get("domain", "general")

        logger.info(f"Received webhook from {sender_email} in domain: {domain}")

        # Generate GPT response using new OpenAI API format
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful SDR replying to leads via email."},
                {"role": "user", "content": email_body}
            ]
        )

        reply_text = response.choices[0].message.content

        return {
            "status": "success",
            "reply": reply_text,
            "sender": sender_email
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
