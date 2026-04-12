import requests
import json

google_api_key = "AIzaSyCbpgfyJAGZKUMVgklcNcrN9NwUy7GwyNE"
PERSONALITY = "Tell me who made you."
messages = [{"role": "user", "parts": [{"text": "Hello"}]}]

payload = {
    "system_instruction": {"parts": [{"text": PERSONALITY}]},
    "contents": messages,
    "generationConfig": {"temperature": 0.8}
}

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={google_api_key}"
resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
print(f"Status: {resp.status_code}")
print(resp.json())
