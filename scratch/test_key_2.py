import requests
google_api_key = "AIzaSyCav4UnAP1s2AJKIvOwx0W-Lx5O3MjEIvA"
payload = {
    "contents": [{"role": "user", "parts": [{"text": "Hello"}]}]
}
url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={google_api_key}"
resp = requests.post(url, json=payload)
print(f"Status: {resp.status_code}")
print(resp.json())
