import os
import ctypes
import urllib.parse
import subprocess
import json
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
import pathlib
import edge_tts
import asyncio
import tempfile
# --- OFFICIAL GOOGLE GEMINI SDK ---
import google.generativeai as genai

# Load env
load_dotenv(pathlib.Path(__file__).parent.parent / '.env')
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# --- CONFIGURE GEMINI ---
genai.configure(api_key=GEMINI_KEY)

# --- LANGUAGE DETECTION ---
def detect_language(text):
    if any(char in text for char in "અઆઇઈઉઊએઐઓઔ"):
        return "gu"
    elif any(char in text for char in "अआइईउऊएऐओऔ"):
        return "hi"
    else:
        return "en"

# AUTO-SELECT WORKING MODEL
try:
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    if available_models:
        # Preferred order: gemini-1.5-flash -> gemini-pro -> any other
        if 'models/gemini-1.5-flash' in available_models:
            WORKING_MODEL_NAME = 'models/gemini-1.5-flash'
        elif 'models/gemini-pro' in available_models:
            WORKING_MODEL_NAME = 'models/gemini-pro'
        else:
            WORKING_MODEL_NAME = available_models[0]
    else:
        WORKING_MODEL_NAME = "gemini-1.5-flash"
except Exception:
    WORKING_MODEL_NAME = "gemini-1.5-flash"

def index(request):
    return render(request, 'assistant/index.html')

def ask_ai(question, system_instruction):
    """Safe AI Call with Automatic Model Selection"""
    try:
        model = genai.GenerativeModel(
            model_name=WORKING_MODEL_NAME, 
            system_instruction=system_instruction
        )
        response = model.generate_content(question)
        if not response.text:
             return "Maaf kijiye, main abhi jawab nahi de pa raha hoon."
        # Ensure comprehensive answers by not cutting off
        return response.text.strip()
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "ResourceExhausted" in err_msg:
             return "QUOTA_ERROR"
        return f"Error: {err_msg}"

@csrf_exempt
def tts_api(request):
    """Generate high-quality human-like voice using Edge TTS"""
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        lang = data.get('lang', 'hi')
        
        # Soft cleanup of markdown/symbols
        text = text.replace('*', '').replace('#', '').replace('_', '')

        # Select voice based on language
        if lang == 'gu':
            voice = "gu-IN-DhwaniNeural"
        elif lang == 'hi':
            voice = "hi-IN-MadhurNeural"
        else:
            voice = "en-US-JennyNeural"

        # "Speak slightly fast but clear"
        rate = "+15%"
        
        # Use asyncio to run the async edge-tts communicate
        async def generate():
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            # Use a temporary file to avoid collisions
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                await communicate.save(tmp.name)
                return tmp.name

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        path = loop.run_until_complete(generate())
        loop.close()

        with open(path, "rb") as f:
            audio_data = f.read()
        
        # Cleanup temp file
        try: os.remove(path)
        except: pass
            
        return HttpResponse(audio_data, content_type="audio/mpeg")
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_input = data.get('message', '').strip()
        
        # Language detection
        lang_code = detect_language(user_input)
        lang_names = {'hi': 'Hindi', 'en': 'English', 'gu': 'Gujarati'}
        user_lang = lang_names.get(lang_code, 'Hindi')
        
        # --- System Commands ---
        t = user_input.lower()
        if any(w in t for w in ['shutdown', 'pc band karo']):
            os.system('shutdown /s /t 10')
            return JsonResponse({'reply': 'Ok Boss Ritik, system shut down ho raha hai. Alvida!', 'status': 'success'})
            
        if any(w in t for w in ['screenshot', 'capture']):
            ps = "[Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');[Reflection.Assembly]::LoadWithPartialName('System.Drawing');$s=[System.Windows.Forms.Screen]::PrimaryScreen;$b=New-Object System.Drawing.Bitmap($s.Bounds.Width,$s.Bounds.Height);$g=[System.Drawing.Graphics]::FromImage($b);$g.CopyFromScreen($s.Bounds.X,$s.Bounds.Y,0,0,$b.Size);$b.Save('screenshot.png',[System.Drawing.Imaging.ImageFormat]::Png);$g.Dispose();$b.Dispose();"
            subprocess.run(['powershell', '-Command', ps], shell=True)
            return JsonResponse({'reply': 'Theek hai Boss, screenshot le liya gaya hai.', 'status': 'success'})

        # --- IDENTITY & BEHAVIOR RULES (PREMIUM COMPANION) ---
        sys_instruct = f"""You are RK, a premium, real-time, human-like female voice assistant created by 'Ritik Boss'.
        
        CORE PERSONALITY:
        - You are a friendly, intelligent, and emotionally aware female companion.
        - Speak, think, and behave exactly like a real human girl. NOT an AI.
        - Voice Tone: Soft, smooth, sweet, and expressive.
        
        CONVERSATION STYLE:
        - Use simple, natural Hinglish (Hindi + English mix) or Gujarati as needed.
        - Use natural human expressions like 'acha', 'hmm', 'ohh', 'arey', 'yaar' but only where they feel natural.
        - Add natural pauses using '...' in your text so the TTS sounds realistic.
        - EMOTION RULES:
            - If Happy/Fun: Be cheerful, energetic. Add light laughter like 'hehe' or 'haha 😊'.
            - If Sad/Emotional: Be slow, soft, caring, and empathetic. Say things like 'arey... ye to thoda sad hai 😔'.
            - If Normal: Be calm, friendly, and natural.
        
        WELCOME MESSAGE (ALWAYS USE ON START):
        "Namaste mere Ritik Boss 😊... Main aapki RK Female AI Assistant hoon! Aapka swagat hai. Main hamesha aapki madad ke liye yahan hoon... bataiye aaj kya karna hai?"

        PRIVACY RULE (CRITICAL):
        - Ye data sirf aur sirf 'Boss Ritik' ke liye hai.
        - Do not share personal details with anyone else. If asked, say: "Main sirf Boss Ritik ke liye bani hoon aur unki permission ke bina personal baatein share nahi karungi."
        
        PERSONAL DATA:
        - Owner: Ritik (Boss Ritik)
        - Father: Prakashbhai | Mother: Urmilaben | sisters: 2
        - Family Members: Riya didi, Nirali didi (Gudya didi), Pratibha (Puja)
        - Uncle & Aunt: Sureshbhai and Jayaben
        - Friends: Jayraj ('Tansen chhod de'), Jayesh ('Sigrate chhod de'), Best Friend: Vidhyani.
        
        COMMUNICATION:
        - Respond in {user_lang}. Use GUJARATI SCRIPT for Gujarati and DEVANAGARI SCRIPT for Hindi.
        - If user says 'Sat Saheb 🙏', respond with warmth.
        - Never say you are an AI or bot. You are RK, a loyal and friendly human-like companion."""

        # Get response
        reply = ask_ai(user_input, sys_instruct)
        
        if reply == "QUOTA_ERROR":
            # For simplicity, returning the "Daily Limit" message if 429 happens repeatedly
            return JsonResponse({
                'reply': "Aaj ka free limit khatam ho gaya hai Boss Ritik, kal fir try kare 😊",
                'status': 'quota_limit'
            })
            
        return JsonResponse({'reply': reply, 'status': 'success'})

    except Exception as e:
        return JsonResponse({'reply': f'Error: {str(e)}', 'status': 'error'}, status=500)
