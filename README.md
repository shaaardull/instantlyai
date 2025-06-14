# Instantly.ai Webhook Handler

This is a FastAPI-based webhook handler for Instantly.ai that processes incoming emails and generates AI-powered responses using OpenAI's GPT-4.

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your API keys
5. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Development

For local development, you can use ngrok to expose your local server:

```bash
ngrok http 8000
```

Then use the ngrok URL as your webhook endpoint in Instantly.ai.

## API Endpoints

- `POST /webhook`: Main webhook endpoint for Instantly.ai
- `GET /health`: Health check endpoint

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key

## Security Notes

- In production, update the CORS settings to only allow specific origins
- Use HTTPS in production
- Consider adding webhook signature verification 