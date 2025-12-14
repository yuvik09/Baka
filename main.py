import os
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

app = FastAPI()

# TEMP history (later Redis / DB)
chat_history = {}

def send_message(chat_id: int, text: str):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

def mistral_chat(messages: list):
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-small-latest",
        "messages": messages
    }

    res = requests.post(MISTRAL_API_URL, headers=headers, json=payload)
    return res.json()["choices"][0]["message"]["content"]

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")

    if not user_text:
        return {"ok": True}

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    # Add user message
    chat_history[chat_id].append({
        "role": "user",
        "content": user_text
    })

    # Keep only last 6 messages
    chat_history[chat_id] = chat_history[chat_id][-6:]

    # Get reply from Mistral
    reply = mistral_chat(chat_history[chat_id])

    # Save assistant reply
    chat_history[chat_id].append({
        "role": "assistant",
        "content": reply
    })

    chat_history[chat_id] = chat_history[chat_id][-6:]

    send_message(chat_id, reply)
    return {"ok": True}

@app.on_event("startup")
def set_webhook():
    url = f"{TELEGRAM_API}/setWebhook?url={WEBHOOK_URL}"
    requests.get(url)
