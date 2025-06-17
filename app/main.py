from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Dict, Any
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Instantly.ai Webhook Handler",
    description="Webhook handler for Instantly.ai email automation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.post("/webhook")
async def webhook_handler(request: Request) -> Dict[str, Any]:
    """
    Handle incoming webhook requests from Instantly.ai
    """
    try:
        # Parse the incoming webhook data
        data = await request.json()
        logger.info(f"Received webhook data: {data}")

        # Extract email data
        email_body = data.get("email_body")
        sender = data.get("sender_email")

        if not email_body or not sender:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Generate GPT response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful SDR replying to leads via email."},
                {"role": "user", "content": email_body}
            ]
        )

        reply_text = response.choices[0].message.content

        # Log the response
        logger.info(f"Generated reply for {sender}")

        return {
            "status": "success",
            "reply": reply_text,
            "sender": sender
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