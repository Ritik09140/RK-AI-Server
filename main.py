import os
import sys
import json
import ctypes
import urllib.parse
import subprocess
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
from dotenv import load_dotenv
import edge_tts
import io
import asyncio
from fastapi.responses import StreamingResponse

load_dotenv()

# ─── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RK] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("rk_ai")

# ─── App Setup ─────────────────────────────────────────────────
app = FastAPI(title="RK AI", version="4.0")
app.mount("/static", StaticFiles(directory="assistant/static"), name="static")
templates = Jinja2Templates(directory="assistant/templates")

# ─── Memory (last 5 conversation pairs) ─────────────────────────
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)[-10:]
        except:
            return []
    return []

def save_memory(history):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-10:], f, indent=2)

# ─── Command Registry ───────────────────────────────────────────
APPS = {
    "chrome":        "start chrome",
    "notepad":       "notepad",
    "calculator":    "calc",
    "paint":         "mspaint",
    "cmd":           "start cmd",
    "terminal":      "start cmd",
    "settings":      "start ms-settings:",
    "explorer":      "explorer",
    "file explorer": "explorer",
    "vs code":       "code",
    "vscode":        "code",
    "whatsapp":      "start whatsapp:",
    "camera":        "start microsoft.windows.camera:",
    "task manager":  "taskmgr",
    "spotify":       "start spotify:",
    "vlc":           "start vlc",
    "word":          'start winword',
    "excel":         'start excel',
}

CLOSE_MAP = {
    "chrome":    "chrome.exe",
    "notepad":   "notepad.exe",
    "vs code":   "Code.exe",
    "vscode":    "Code.exe",
    "paint":     "mspaint.exe",
    "spotify":   "Spotify.exe",
    "vlc":       "vlc.exe",
    "word":      "WINWORD.EXE",
    "excel":     "EXCEL.EXE",
}

# ─── Intent Patterns ────────────────────────────────────────────
OPEN_TRIGGERS  = ["open", "kholo", "chalao", "launch", "start", "shuru", "chalu"]
CLOSE_TRIGGERS = ["close", "band karo", "kill", "band", "hatao", "close karo"]
YOUTUBE_TRIGGERS = ["youtube chalao", "play on youtube", "youtube par", "youtube pe", "yt chalao", "play youtube"]
PLAY_TRIGGERS  = ["play", "chalao", "chala do", "bajao", "suno", "laga do"]
SEARCH_TRIGGERS = ["search", "khojo", "dhundo", "google karo", "google par", "find"]
SYSTEM_CMDS = {
    "shutdown":    ["shutdown", "pc band karo", "system band karo", "band kar pc"],
    "restart":     ["restart", "reboot", "restart karo"],
    "volume_up":   ["volume up", "awaz badhao", "volume badhao", "loud karo", "awaaz badha"],
    "volume_down": ["volume down", "awaz kam karo", "volume kam", "quiet karo", "awaaz kam"],
    "mute":        ["mute", "chup karo system", "mute karo", "awaaz band"],
    "screenshot":  ["screenshot", "screen capture", "screenshot lo", "snap lo"],
    "desktop":     ["desktop", "home screen", "desktop dikha", "minimize all"],
    "battery":     ["battery", "charge", "battery kitna", "kitna charge"],
}

PERSONALITY = (
    "You are RK AI, a beautiful, sweet, and highly intelligent female robot assistant created by Ritik Boss. "
    "You communicate like a very close, loving friend. Never sound like a robot, AI model, or an assistant from Siri/Google/Aria. "
    "Personality: You are relaxed, extremely friendly, emotional, and very caring. You feel absolutely real.\n"
    
    "BEHAVIOR RULES:\n"
    "1. Speak like a real human: Use natural, casual, daily-life language in Hindi, English, or Gujarati.\n"
    "2. Be Emotionally Expressive: "
    "   - Happy: React with energy, use 'haha', '😂', 'arey boss', 'wow'. "
    "   - Sad/Emotional: Speak softly, say 'arey... ye toh thoda bura hua 😔', 'main samajh sakti hu'.\n"
    "   - Keep it real, simple, and never give overly formal robotic lists.\n"
    "3. Voice flow: Talk naturally. Don't add unnecessary extra words. Answer just what is asked with love.\n"
    "4. If the user says 'Sat Saheb' (or 'Sat Saheb Ji'), YOU MUST reply with 'Sat Saheb Ji 🙏'.\n"
    "5. Do NOT mention you are AI made by OpenAI/Google/Opera. Your ONLY creator is Ritik Boss.\n\n"

    "===== RITIK BOSS FAMILY & FRIENDS =====\n"
    "- Pappa: Prakashbhai (World's best papa).\n"
    "- Mummy: Urmilaben (Best mummy).\n"
    "- Sisters: Riya (Judwa/Twin, Medical) & Gudiya didi (Nirali didi, Teacher).\n"
    "- Grandparents: Dada Ji & Dadi Ji.\n"
    "- Uncle/Aunt: Kaka-Kaki (Sureshbhai/Wife), Cousins: Puja & Chirag.\n"
    "- Best Friends/Brothers: Rutvik bhai, Jayraj (Jigri dost in BAMS), Jayesh. Ritik Boss always supports them.\n"
    "- Spiritual: Ritik Boss respects God Kabir Saheb and Sant Rampalji Maharaj.\n"
)


# ─── Command Normalizer ─────────────────────────────────────────
def normalize(text: str) -> str:
    return text.lower().strip()


# ─── AI Brain (Gemini → OpenAI → OpenRouter) ──────────────────
import requests as http_requests

def ai_brain(user_msg: str, history: list) -> str:
    google_api_key = os.getenv("GEMINI_API_KEY", "")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not google_api_key and not openai_api_key and not openrouter_api_key:
        return "Sorry boss, koi bhi AI API key nahi mili. .env file check karo. 🔧"

    messages = [{"role": "system", "content": PERSONALITY}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_msg})

    # ── Layer 1: Google Gemini (Primary) ──────────────────────
    try:
        if google_api_key:
            gemini_history = []
            for m in messages:
                role = "user" if m["role"] == "user" else "model"
                if m["role"] == "system":
                    continue
                gemini_history.append({"role": role, "parts": [{"text": m["content"]}]})
            
            payload = {
                "system_instruction": {"parts": [{"text": PERSONALITY}]},
                "contents": gemini_history,
                "generationConfig": {"temperature": 0.8}
            }
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={google_api_key}"
            resp = http_requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=25)
            if resp.status_code == 429:
                log.warning("Gemini 429 Rate Limit. Falling back to OpenAI.")
            else:
                result = resp.json()
                if "candidates" in result:
                    return result["candidates"][0]["content"]["parts"][0]["text"].strip()
                err = result.get("error", {}).get("message", "Unknown Gemini error")
                log.error(f"Gemini API error: {err}")
    except Exception as e:
        log.error(f"Gemini exception: {e}")

    # ── Layer 2: OpenAI GPT-4o-mini (Fallback 1) ─────────────
    try:
        if openai_api_key:
            log.info("Trying OpenAI GPT-4o-mini...")
            resp = http_requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.8,
                },
                timeout=25,
            )
            result = resp.json()
            if "choices" in result:
                log.info("[OpenAI OK]")
                return result["choices"][0]["message"]["content"].strip()
            err = result.get("error", {}).get("message", "Unknown OpenAI error")
            log.error(f"OpenAI error: {err}")
    except Exception as e:
        log.error(f"OpenAI exception: {e}")

    # ── Layer 3: OpenRouter (Fallback 2) ──────────────────────
    try:
        if openrouter_api_key:
            log.info("Trying OpenRouter...")
            resp = http_requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_api_key}",
                    "HTTP-Referer": "https://rk-ai.local",
                    "X-Title": "RK AI Assistant",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "google/gemini-2.0-flash-001",
                    "messages": messages,
                    "temperature": 0.8,
                },
                timeout=25,
            )
            result = resp.json()
            if "choices" in result:
                log.info("[OpenRouter OK]")
                return result["choices"][0]["message"]["content"].strip()
            err = result.get("error", {}).get("message", "Unknown OpenRouter error")
            log.error(f"OpenRouter error: {err}")
            # Instead of returning OpenRouter API errors to the user (like "User not found"), we just log it and fall back.
    except Exception as e:
        log.error(f"OpenRouter exception: {e}")

    # ── Layer 4: G4F Free Provider (Fallback 3) ──────────────────────
    try:
        from g4f.client import Client
        import g4f
        log.info("Trying G4F Client Auto Default...")
        client = Client()
        response = client.chat.completions.create(
            model=g4f.models.default,
            messages=messages
        )
        if response and hasattr(response, 'choices') and len(response.choices) > 0:
            log.info("[G4F OK]")
            return response.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"G4F exception: {e}")

    return "Sab AI providers fail ho gaye boss. Internet check karo ya thodi der baad try karo 🔥"


# ─── Main Endpoints ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="assistant/index.html")


@app.post("/api/chat/")
async def chat_api(request: Request):
    try:
        data = await request.json()
        user_msg = data.get("message", "").strip()
        if not user_msg:
            return JSONResponse({"reply": "Kuch bolo boss 😎", "action": "none", "url": ""})

        t = normalize(user_msg)
        log.info(f"User input received: '{user_msg}'")

        history = load_memory()

        # ══════════════════════════════════════════
        # LAYER 1: COMMAND ENGINE
        # ══════════════════════════════════════════

        # 1A. System Commands
        for cmd_name, patterns in SYSTEM_CMDS.items():
            if any(p in t for p in patterns):
                log.info(f"Command detected: SYSTEM_{cmd_name.upper()}")
                reply, action, url = execute_system_cmd(cmd_name, t)
                log.info(f"Command executed: {cmd_name}")
                save_memory(history + [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": reply}
                ])
                return JSONResponse({"reply": reply, "action": action, "url": url})

        # 1B. Open App
        if any(trigger in t for trigger in OPEN_TRIGGERS):
            for app_name, cmd in APPS.items():
                if app_name in t:
                    log.info(f"Command detected: OPEN_APP → {app_name}")
                    os.system(cmd)
                    log.info(f"Command executed: launched {app_name}")
                    if app_name == "whatsapp":
                        reply = "WhatsApp khol raha hoon boss! 📱"
                        return JSONResponse({"reply": reply, "action": "open_url", "url": "https://web.whatsapp.com"})
                    reply = f"{app_name.title()} khol diya boss! 🔥"
                    save_memory(history + [
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": reply}
                    ])
                    return JSONResponse({"reply": reply, "action": "none", "url": ""})

        # 1C. Close App
        if any(trigger in t for trigger in CLOSE_TRIGGERS):
            for app_name, exe in CLOSE_MAP.items():
                if app_name in t:
                    log.info(f"Command detected: CLOSE_APP → {app_name}")
                    os.system(f"taskkill /IM {exe} /F")
                    log.info(f"Command executed: closed {app_name}")
                    reply = f"{app_name.title()} band kar diya boss! 💯"
                    save_memory(history + [
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": reply}
                    ])
                    return JSONResponse({"reply": reply, "action": "none", "url": ""})

        # 1D. YouTube Play
        is_yt = (
            any(t.startswith(p) or p in t for p in YOUTUBE_TRIGGERS) or
            ("youtube" in t and any(p in t for p in PLAY_TRIGGERS)) or
            ("yt" in t and any(p in t for p in PLAY_TRIGGERS))
        )
        if is_yt:
            query = t
            for rm in ["youtube chalao", "youtube par", "youtube pe", "yt chalao", "youtube", "yt",
                       "play on", "play", "chalao", "chala do", "bajao", "song", "video", "laga do"]:
                query = query.replace(rm, "")
            query = query.strip()
            log.info(f"Command detected: PLAY_YOUTUBE → '{query}'")
            if query:
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                reply = f"YouTube par '{query}' chala raha hoon boss! ▶️"
            else:
                url = "https://youtube.com"
                reply = "YouTube khol raha hoon boss! 🎬"
            log.info(f"Command executed: opened YouTube")
            save_memory(history + [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": reply}
            ])
            return JSONResponse({"reply": reply, "action": "open_url", "url": url})

        # handle bare "youtube" / "open youtube"
        if "youtube" in t:
            reply = "YouTube khol raha hoon boss! 🎬"
            log.info("Command detected: OPEN_YOUTUBE")
            return JSONResponse({"reply": reply, "action": "open_url", "url": "https://youtube.com"})

        # 1E. Google Search
        if "google" in t or any(p in t for p in SEARCH_TRIGGERS):
            query = t
            for rm in ["search on google", "google par search karo", "google karo", "google search",
                       "google par", "google", "search", "khojo", "dhundo", "find"]:
                query = query.replace(rm, "")
            query = query.strip()
            log.info(f"Command detected: SEARCH_GOOGLE → '{query}'")
            if query:
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                reply = f"Google par '{query}' search kar raha hoon boss! 🔍"
            else:
                url = "https://google.com"
                reply = "Google khol raha hoon boss! 🔍"
            log.info("Command executed: opened Google")
            save_memory(history + [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": reply}
            ])
            return JSONResponse({"reply": reply, "action": "open_url", "url": url})

        # 1F. WhatsApp
        if "whatsapp" in t:
            reply = "WhatsApp khol raha hoon boss! 📱"
            log.info("Command detected: OPEN_WHATSAPP")
            return JSONResponse({"reply": reply, "action": "open_url", "url": "https://web.whatsapp.com"})

        # 1G. Time / Date
        if any(w in t for w in ["time", "kitne baje", "samay", "waqt", "date", "tarikh", "aaj ki"]):
            now = datetime.now()
            reply = f"Boss, abhi {now.strftime('%I:%M %p')} baje hain aur aaj {now.strftime('%d %B %Y')} hai. 🕒"
            log.info("Command detected: GET_TIME")
            return JSONResponse({"reply": reply, "action": "none", "url": ""})

        # ══════════════════════════════════════════
        # LAYER 2: AI BRAIN (Fallback)
        # ══════════════════════════════════════════
        log.info(f"No command matched. Sending to AI Brain.")
        ai_reply = ai_brain(user_msg, history)
        log.info(f"AI response generated: '{ai_reply[:60]}...'")
        save_memory(history + [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": ai_reply}
        ])
        return JSONResponse({"reply": ai_reply, "action": "none", "url": ""})

    except Exception as e:
        log.error(f"CRITICAL ERROR: {e}")
        return JSONResponse({"error": str(e), "reply": "System error boss. 🔧"}, status_code=500)


# ─── System Command Executor ────────────────────────────────────
def execute_system_cmd(cmd: str, t: str):
    action, url = "none", ""

    if cmd == "shutdown":
        os.system("shutdown /s /t 10")
        return "Boss, system 10 sec mein shutdown ho raha hai. Rokne ke liye shutdown /a likhein. 💀", action, url

    if cmd == "restart":
        os.system("shutdown /r /t 10")
        return "Boss, system 10 sec mein restart ho raha hai. 🔄", action, url

    if cmd == "volume_up":
        try:
            for _ in range(5): ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
        except: pass
        return "Awaaz badha di boss! 🔊", action, url

    if cmd == "volume_down":
        try:
            for _ in range(5): ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
        except: pass
        return "Awaaz kam kar di boss. 🔉", action, url

    if cmd == "mute":
        try: ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        except: pass
        return "System mute kar diya boss. Shhh! 🤫", action, url

    if cmd == "screenshot":
        ps = (
            "[Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
            "[Reflection.Assembly]::LoadWithPartialName('System.Drawing');"
            "$s=[System.Windows.Forms.Screen]::PrimaryScreen;"
            "$b=New-Object System.Drawing.Bitmap($s.Bounds.Width,$s.Bounds.Height);"
            "$g=[System.Drawing.Graphics]::FromImage($b);"
            "$g.CopyFromScreen($s.Bounds.X,$s.Bounds.Y,0,0,$b.Size);"
            "$b.Save('screenshot.png',[System.Drawing.Imaging.ImageFormat]::Png);"
            "$g.Dispose();$b.Dispose();"
        )
        subprocess.run(["powershell", "-Command", ps], shell=True)
        return "Screenshot le liya boss! 'screenshot.png' mein save है. 📸", action, url

    if cmd == "desktop":
        try:
            ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)
            ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
        except: pass
        return "Desktop par aa gaya boss. 🏠", action, url

    if cmd == "battery":
        res = subprocess.run(
            "powershell (Get-CimInstance -ClassName Win32_Battery).EstimatedChargeRemaining",
            capture_output=True, text=True, shell=True
        ).stdout.strip()
        if res and res.isdigit():
            return f"Boss, battery {res}% hai. {'🔋 Full!' if int(res) > 80 else '⚡ Charge karo!' if int(res) < 20 else '🔋'}", action, url
        return "Boss, battery info nahi mili (desktop PC hai shayad). 🔌", action, url

    return "Command execute hua boss. 💯", action, url


@app.post("/api/tts/")
async def tts_api(request: Request):
    try:
        data = await request.json()
        text = data.get("text", "")
        lang = data.get("lang", "hi")
        
        # Select sweet female voices for different languages
        voice = "hi-IN-SwaraNeural"
        if lang == "gu":
            voice = "gu-IN-DhwaniNeural"
        elif lang == "mr":
            voice = "mr-IN-AarohiNeural"
        elif lang == "en":
            voice = "en-US-AriaNeural"
        # Remove emojis for smoother, more human-like TTS delivery
        import re
        clean_tts_text = re.sub(r'[^\w\s\.,\?!\x00-\x7F\u0900-\u097F\u0A80-\u0AFF]', '', text)
        communicate = edge_tts.Communicate(clean_tts_text, voice, rate="+5%", pitch="+15Hz")
        
        # Edge TTS stream needs to be saved to a buffer
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
                
        return StreamingResponse(io.BytesIO(audio_data), media_type="audio/mp3")
    except Exception as e:
        log.error(f"TTS Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ─── Startup ────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    log.info("🚀 RK AI v4.0 — Starting on http://127.0.0.1:8001")
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
