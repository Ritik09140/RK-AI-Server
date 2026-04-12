import requests
google_api_key = "AIzaSyCbpgfyJAGZKUMVgklcNcrN9NwUy7GwyNE"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={google_api_key}"
resp = requests.get(url)
print(resp.json())
