import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not found in .env")
        return

    print(f"Testing OpenRouter with key: {api_key[:10]}...")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8001", # Required for OpenRouter
        "X-Title": "RK AI Test", # Recommended
    }

    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": [
            {"role": "user", "content": "Hello, respond with 'Success' if you can hear me."}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Success! Response: {content}")
        else:
            print(f"❌ Failed: Status {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error during request: {e}")

if __name__ == "__main__":
    test_openrouter()
