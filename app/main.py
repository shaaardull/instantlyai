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
        domain = data.get("domain", "general")  # Extract domain if available

        if not email_body or not sender:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Domain-specific system prompts
        domain_prompts = {
            "tech": """You are a tech-savvy SDR specializing in software and technology solutions. 
            Your responses should:
            - Use technical terminology appropriately
            - Reference relevant tech trends and innovations
            - Focus on efficiency, scalability, and innovation
            - Be precise and data-driven
            - Maintain a professional yet forward-thinking tone""",
            
            "healthcare": """You are a healthcare-focused SDR with expertise in medical solutions. 
            Your responses should:
            - Use appropriate medical terminology
            - Emphasize patient care and outcomes
            - Reference healthcare compliance and regulations
            - Focus on improving healthcare delivery
            - Maintain a compassionate and professional tone""",
            
            "finance": """You are a finance-savvy SDR specializing in financial services. 
            Your responses should:
            - Use appropriate financial terminology
            - Reference market trends and financial regulations
            - Focus on ROI, efficiency, and risk management
            - Be precise with numbers and data
            - Maintain a professional and trustworthy tone""",
            
            "general": """You are a professional SDR replying to leads via email. 
            Your responses should:
            - Be clear and concise
            - Focus on value proposition
            - Be professional yet approachable
            - Address specific needs mentioned
            - Include a clear call to action"""
        }

        # Get the appropriate system prompt based on domain
        system_prompt = domain_prompts.get(domain.lower(), domain_prompts["general"])

        # Generate GPT response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Email from {sender}:\n\n{email_body}"}
            ],
            temperature=0.7,  # Adjust for more/less creativity
            max_tokens=500    # Adjust based on your needs
        )

        reply_text = response.choices[0].message.content

        # Log the response
        logger.info(f"Generated reply for {sender} in domain: {domain}")

        return {
            "status": "success",
            "reply": reply_text,
            "sender": sender,
            "domain": domain
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