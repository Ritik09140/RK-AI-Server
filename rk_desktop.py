"""
RK AI Desktop Assistant
Created by Ritik Boss
Voice Input + AI Brain (OpenRouter) + Voice Output + Memory
Run: python rk_desktop.py
Install: pip install SpeechRecognition pyttsx3 pyaudio requests
"""

import speech_recognition as sr
import pyttsx3
import requests
import json
import os
import subprocess
import webbrowser
from datetime import datetime
from collections import deque

def manual_load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        os.environ[key] = value

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
manual_load_env()

# ── Config ────────────────────────────────────────────────────────────────────
OPENROUTER_KEY = "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"
AI_MODEL = "google/gemini-2.0-flash-001"
WAKE_WORD = "hey rk"
ASSISTANT_NAME = "RK"
CREATOR = "Ritik Boss"

# ── Memory (last 10 messages) ─────────────────────────────────────────────────
memory = deque(maxlen=10)
user_name = None

# ── TTS Engine ────────────────────────────────────────────────────────────────
engine = pyttsx3.init()
engine.setProperty('rate', 175)
engine.setProperty('volume', 1.0)

# Try to set a female voice
voices = engine.getProperty('voices')
female_voice = None
for v in voices:
    if 'female' in v.name.lower() or 'zira' in v.name.lower() or 'kalpana' in v.name.lower():
        female_voice = v.id
        break

if female_voice:
    engine.setProperty('voice', female_voice)
else:
    # Fallback to any voice that isn't the default if possible
    if len(voices) > 1:
        engine.setProperty('voice', voices[1].id)

def speak(text: str):
    """Convert text to speech."""
    print(f"\n[RK] {text}")
    engine.say(text)
    engine.runAndWait()

# ── Speech Recognition ────────────────────────────────────────────────────────
recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

def listen(timeout: int = 5, phrase_limit: int = 10) -> str | None:
    """Listen from microphone and return text."""
    with sr.Microphone() as source:
        print("\n[MIC] Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            # Try Hindi first, then English
            try:
                text = recognizer.recognize_google(audio, language="hi-IN")
            except:
                text = recognizer.recognize_google(audio, language="en-IN")
            print(f"[YOU] {text}")
            return text.strip()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[MIC ERR] {e}")
            return None

# ── AI Brain (OpenRouter) ─────────────────────────────────────────────────────
def ask_ai(user_msg: str) -> str:
    """Send message to AI with memory context and robust multi-model fallback."""
    global user_name
    
    if not OPENROUTER_KEY:
        return "Boss, OpenRouter key missing in .env! 🔧"

    system_prompt = (
        f"You are {ASSISTANT_NAME}, a sweet and smart female AI assistant created by {CREATOR}. "
        f"{'User name is ' + user_name + '. ' if user_name else ''}"
        "Personality: You are a kind and professional girl. You treat Boss like a friend. "
        "Language: Speak in the same language the user speaks (Hindi/Gujarati/English/Marathi). "
        "Give concise and sweet answers. Use emojis to sound friendly. "
        "Always be respectful and address the user as 'Boss'."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in list(memory):
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_msg})

    # High reliability model list
    models = [
        "google/gemini-2.0-flash-001",
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "microsoft/phi-3-mini-128k-instruct:free",
        "google/gemma-2-9b-it:free",
        "openchat/openchat-7b:free"
    ]

    last_error = "Unknown"
    for model in models:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "RK AI Desktop"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 400,
                    "temperature": 0.8
                },
                timeout=15
            )
            if response.status_code == 200:
                reply = response.json()["choices"][0]["message"]["content"].strip()
                # Save to memory
                memory.append({"role": "user", "content": user_msg})
                memory.append({"role": "assistant", "content": reply})
                return reply
            
            last_error = f"Status {response.status_code}"
        except Exception as e:
            last_error = str(e)
            continue

    return f"Boss, system link down hai (Report: {last_error[:30]}). 🔧"

# ── Command Engine ────────────────────────────────────────────────────────────
def execute_command(text: str) -> str | None:
    """Check if text is a command. Return reply or None."""
    t = text.lower().strip()

    # Identity
    if any(w in t for w in ["kisne banaya", "who made you", "who created", "creator"]):
        return f"Mujhe {CREATOR} ne banaya hai! Main {ASSISTANT_NAME} hoon, aapka personal AI assistant."

    if any(w in t for w in ["tum kaun ho", "who are you", "kaun ho", "aap kaun"]):
        return f"Main {ASSISTANT_NAME} hoon — {CREATOR} ka personal AI assistant! Kya madad kar sakta hoon Boss?"

    # Time & Date
    if any(w in t for w in ["time", "kitne baje", "samay"]):
        return f"Boss, abhi {datetime.now().strftime('%I:%M %p')} baje hain."

    if any(w in t for w in ["date", "tarikh", "aaj kya"]):
        return f"Boss, aaj {datetime.now().strftime('%d %B %Y')} hai."

    # System commands
    if any(w in t for w in ["shutdown", "pc band karo", "system band"]):
        speak("Boss, system 10 seconds mein shutdown ho raha hai!")
        os.system("shutdown /s /t 10")
        return None

    if any(w in t for w in ["restart", "reboot"]):
        speak("Boss, system restart ho raha hai!")
        os.system("shutdown /r /t 10")
        return None

    # Volume
    if any(w in t for w in ["volume up", "awaz badhao"]):
        import ctypes
        for _ in range(5): ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
        return "Awaaz badha di Boss!"

    if any(w in t for w in ["volume down", "awaz kam"]):
        import ctypes
        for _ in range(5): ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
        return "Awaaz kam kar di Boss!"

    if "mute" in t:
        import ctypes
        ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        return "Mute kar diya Boss!"

    # Open apps
    open_words = ["open", "kholo", "launch", "start", "chalao"]
    if any(w in t for w in open_words):
        if "youtube" in t:
            webbrowser.open("https://youtube.com")
            return "YouTube khol diya Boss!"
        if "google" in t:
            webbrowser.open("https://google.com")
            return "Google khol diya Boss!"
        if "whatsapp" in t:
            webbrowser.open("https://web.whatsapp.com")
            return "WhatsApp khol diya Boss!"
        if "chrome" in t:
            os.system("start chrome")
            return "Chrome khol diya Boss!"
        if "notepad" in t:
            os.system("notepad")
            return "Notepad khol diya Boss!"
        if "calculator" in t or "calc" in t:
            os.system("calc")
            return "Calculator khol diya Boss!"
        if "camera" in t:
            os.system("start microsoft.windows.camera:")
            return "Camera khol diya Boss!"
        if "instagram" in t:
            webbrowser.open("https://instagram.com")
            return "Instagram khol diya Boss!"

    # YouTube play
    if ("play" in t or "chalao" in t) and ("song" in t or "music" in t or "gana" in t or "youtube" in t):
        q = t
        for w in ["play", "chalao", "song", "music", "gana", "youtube", "on", "par"]:
            q = q.replace(w, "")
        q = q.strip()
        if q:
            webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
            return f"YouTube par '{q}' chala raha hoon Boss!"
        webbrowser.open("https://youtube.com")
        return "YouTube khol diya Boss!"

    # Google search
    if "google" in t and any(w in t for w in ["search", "khojo", "dhundo", "karo"]):
        q = t.replace("google par search karo", "").replace("search on google", "").replace("google", "").replace("search", "").replace("karo", "").strip()
        if q:
            webbrowser.open(f"https://www.google.com/search?q={q}")
            return f"Google par '{q}' search kar raha hoon Boss!"

    # Remember name
    import re
    m = re.search(r"(?:my name is|mera naam|maro naam)\s+([A-Za-z]+)", text, re.I)
    if m:
        global user_name
        user_name = m.group(1).title()
        return f"Theek hai Boss, main yaad rakh lunga — aapka naam {user_name} hai!"

    if any(w in t for w in ["mera naam kya", "what is my name", "maro naam kya"]):
        if user_name:
            return f"Aapka naam {user_name} hai Boss!"
        return "Boss, aapne abhi tak apna naam nahi bataya!"

    return None  # Not a command → send to AI

# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print(f"  {ASSISTANT_NAME} AI — Created by {CREATOR}")
    print("=" * 50)
    print(f"  Say '{WAKE_WORD}' to activate")
    print("  Or type your message and press Enter")
    print("  Type 'quit' to exit")
    print("=" * 50)

    speak(f"Hello Boss! Main {ASSISTANT_NAME} hoon. Boliye, kya karu?")

    while True:
        try:
            # Option 1: Voice input
            print(f"\n[Listening for '{WAKE_WORD}' or press Enter to type...]")
            user_input = listen(timeout=3, phrase_limit=8)

            # Option 2: Text input fallback
            if not user_input:
                try:
                    user_input = input("[TYPE] > ").strip()
                except EOFError:
                    break

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "band karo", "bye"]:
                speak("Alvida Boss! Phir milenge!")
                break

            # Check command first
            reply = execute_command(user_input)

            # If not a command, ask AI
            if reply is None:
                print("[AI] Thinking...")
                reply = ask_ai(user_input)

            # Speak and print reply
            speak(reply)

        except KeyboardInterrupt:
            print("\n[Exiting...]")
            speak("Alvida Boss!")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            continue

if __name__ == "__main__":
    main()
