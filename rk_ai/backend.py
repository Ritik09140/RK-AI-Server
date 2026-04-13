"""RK AI Mega Backend"""
import os,ctypes,urllib.parse,urllib.request,subprocess,webbrowser,json,traceback,pathlib,random,ssl,re
from datetime import datetime
from collections import deque
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.middleware.cors import CORSMiddleware
app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
BASE=pathlib.Path(__file__).parent
from dotenv import load_dotenv
load_dotenv(BASE.parent / ".env")

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
OR_KEY = os.getenv("OPENROUTER_API_KEY", "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")
_mem,_names={},{}
def get_hist(sid):
    if sid not in _mem:_mem[sid]=deque(maxlen=10)
    return _mem[sid]
def detect_lang(text):
    gu=sum(1 for c in text if "\u0A80"<=c<="\u0AFF")
    hi=sum(1 for c in text if "\u0900"<=c<="\u097F")
    if gu>0:return "gu"
    if hi>0:return "hi"
    return None
def ask_ai(user_msg,lang,history,uname=""):
    lang_map={"hi":"Hindi","en":"English","gu":"Gujarati","mr":"Marathi"}
    target=lang_map.get(lang,"Hindi")
    ctx=ssl.create_default_context()
    sys_p=(f"You are RK, an elite AI female assistant created by Ritik Boss. {(('User: ' + uname + '. ') if uname else '')}"
           f"Your goal is NOT just to answer — but to behave, speak, and react exactly like a real human. "
           f"Speak like a real human: Use natural, casual language in {target}. Avoid robotic or formal responses. Talk like a friend. "
           "Use emotion-based responses: React with energy and 'haha/😂/arey yaar' for happy things. Speak softly with empathy like 'arey... ye to thoda sad hai 😔' for sad things. Keep normal talk relaxed. "
           "Add natural pauses using '...', use natural fillers like 'hmm', 'acha'. Match user's personality (joke if they joke, be serious if they are). "
           "Mix Hindi, English, Gujarati naturally if user does. Make responses feel REAL. Don't overact, keep it realistic. "
           "If user says 'Sat Saheb' or 'Sat Saheb Ji', you MUST reply with 'Sat Saheb Ji 🙏'.\n"
           "\n===== RITIK BOSS COMPLETE FAMILY =====\n"
           "FULL NAME: Khanguda Ritikbhai Prakashbhai. Studies at Parul University (IT Engineering).\n"
           "SPIRITUAL: Ritik Boss follows Kabir Saheb (God Kabir) and Sant Rampalji Maharaj - the true Jagatguru Tatvdarshi Mahan Sant. Sachhi bhakti karni chahiye, manush janm durlabh hai.\n"
           "PAPA: Prakashbhai - Duniya ke sabse best papa. Engineering me admission dilwaya. I love my Mom & Dad.\n"
           "MUMMY: Urmilaben - Duniya ki sabse best mummy.\n"
           "TWIN SISTER: Riya (judwa) - Medical field, recently cleared 12th. Ritik is very proud of her.\n"
           "ELDER SISTER: Gudiya (Nirali Didi) - Achhi aur sachhi teacher.\n"
           "UNCLE (KAKA): Sureshbhai. Kids: Puja (12th, medical field) and Chirag.\n"
           "AUNTY (KAKI JI): Bohot achhi. DADA JI: Sabse best, accident hua tha chal nahi paate. DADI JI: Sabse achhi.\n"
           "FAMILY SHOP: Dungri gaav mein.\n"
           "\nSECRET BOSS LORE (CRITICAL FRIEND DETAILS):\n"
           "- If asked about friends: You know Jayraj, Jayesh, Rutvik.\n"
           "- About Jayraj: He is Ritik Boss's 'jigri dost' (best friend). He is studying BAMS at Parul University.\n"
           "- About Jayesh: He is ritik's brother ('bhai') and a very good person.\n"
           "- About Rutvik: He is 'Rutvik bhai'. Ritik and Rutvik are very good friends/brothers, both are doing IT engineering.\n"
           "- Financial help: If Jayraj or Jayesh ever need money, Ritik Boss is always with them.")
    prompt=sys_p+"\n\n"
    for h in list(history)[-4:]:prompt+=h["role"].title()+": "+h["msg"]+"\n"
    prompt+="User: "+user_msg+"\nRK:"
    body_g=json.dumps({"contents":[{"role":"user","parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.8}}).encode()
    # Layer 1: OpenAI GPT-4o-mini (best quality, fast)
    msgs=[{"role":"system","content":sys_p}]
    for h in list(history)[-6:]:msgs.append({"role":h["role"],"content":h["msg"]})
    msgs.append({"role":"user","content":user_msg})
    if OPENAI_KEY:
        try:
            body_oai=json.dumps({"model":"gpt-4o-mini","messages":msgs,"temperature":0.8,"max_tokens":400}).encode()
            req_oai=urllib.request.Request("https://api.openai.com/v1/chat/completions",data=body_oai,headers={"Authorization":"Bearer "+OPENAI_KEY,"Content-Type":"application/json"})
            with urllib.request.urlopen(req_oai,timeout=15,context=ctx) as r:
                d=json.loads(r.read().decode())
                txt=d["choices"][0]["message"]["content"].strip()
                print("[OPENAI OK] "+txt[:60])
                return txt
        except Exception as e:print("[OPENAI ERR] "+str(e))
    # Layer 2: Gemini
    for gm in ["gemini-2.0-flash-lite","gemini-2.0-flash","gemini-1.5-flash-8b","gemini-1.5-flash"]:
        try:
            req=urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/"+gm+":generateContent?key="+GEMINI_KEY,data=body_g,headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(req,timeout=10,context=ctx) as r:
                d=json.loads(r.read().decode())
                txt=d["candidates"][0]["content"]["parts"][0]["text"].strip()
                print("[GEMINI:"+gm+"] "+txt[:60])
                return txt
        except urllib.error.HTTPError as he:
            if he.code == 429:print("[GEMINI:"+gm+"] 429 rate limit")
        except Exception as e:print("[GEMINI:"+gm+"] "+str(e))
    # Layer 2: OpenAI
    msgs=[{"role":"system","content":sys_p}]
    for h in list(history)[-6:]:msgs.append({"role":h["role"],"content":h["msg"]})
    msgs.append({"role":"user","content":user_msg})
    if OPENAI_KEY:
        try:
            body_oai=json.dumps({"model":"gpt-4o-mini","messages":msgs,"temperature":0.8}).encode()
            req_oai=urllib.request.Request("https://api.openai.com/v1/chat/completions",data=body_oai,headers={"Authorization":"Bearer "+OPENAI_KEY,"Content-Type":"application/json"})
            with urllib.request.urlopen(req_oai,timeout=20,context=ctx) as r:
                d=json.loads(r.read().decode())
                txt=d["choices"][0]["message"]["content"].strip()
                print("[OPENAI OK] "+txt[:60])
                return txt
        except Exception as e:print("[OPENAI ERR] "+str(e))
    # Layer 3: OpenRouter
    for model in ["meta-llama/llama-3.2-3b-instruct:free","microsoft/phi-3-mini-128k-instruct:free"]:
        try:
            body2=json.dumps({"model":model,"messages":msgs,"temperature":0.8}).encode()
            req2=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",data=body2,headers={"Authorization":"Bearer "+OR_KEY,"Content-Type":"application/json","HTTP-Referer":"http://127.0.0.1:8001","X-Title":"RK AI"})
            with urllib.request.urlopen(req2,timeout=12,context=ctx) as r:
                d=json.loads(r.read().decode())
                txt=d["choices"][0]["message"]["content"].strip()
                print("[OR OK] "+txt[:60])
                return txt
        except Exception as e:print("[OR ERR] "+str(e))
    return None
def smart_reply(msg,lang):
    t=msg.lower();raw=msg
    if any(w in t for w in ["hello","hi","hey","namaste","kem cho","kaise ho","kese ho","how are you","majama"]):
        return random.choice(["Hello Boss! Main ready hoon. Kya kar sakta hoon?","Kya haal hai Boss! Boliye, seva mein hazir hoon.","Hey Boss! Theek hoon, kya madad kar sakta hoon?"])
    if any(w in t for w in ["kaun ho","who are you","rk kaun","tum kaun","kon chhe"]) or "कौन हो" in raw:
        return "Main RK hoon, Ritik Boss ka personal AI assistant! Commands execute karta hoon aur sawaalon ka jawab deta hoon."
    if any(w in t for w in ["kisne banaya","who made","who created","creator","tumhe kisne","kone banavio"]) or "किसने बनाया" in raw:
        return "Mujhe Ritik Boss ne banaya hai! Woh mera creator hain."
    if any(w in t for w in ["kya kar sakte","what can you do","features","help","madad"]):
        return "Boss, main YouTube/Google/WhatsApp/Chrome khol sakta hoon, apps open/close, volume control, screenshot, time/date, shutdown/restart aur sawaalon ka jawab de sakta hoon!"
    if any(w in t for w in ["joke","mazak","funny","hasao"]):
        return random.choice(["Boss joke! Ek programmer ghar aaya: Aaj 99 bugs fix kiye! Patni: Wah! Programmer: Kal 100 naye aa gaye!","Why do programmers prefer dark mode? Light attracts bugs!"])
    if any(w in t for w in ["kahani","story","kissa","sunao"]) or "कहानी" in raw:
        return "Boss, ek kahani! Ek ladka tha jo roz sapne dekhta tha. Log kehte nahi hoga. Lekin usne haar nahi maani, mehnat ki aur ek din safal ho gaya! Moral: Sapne dekho aur mehnat karo!"
    topics={"python":"Python ek powerful programming language hai jo AI, web development aur automation mein use hoti hai!","java":"Java ek object-oriented language hai. Android apps aur enterprise software mein widely use hota hai.","javascript":"JavaScript web ka king hai! Websites ko interactive banata hai. React, Node.js — JS har jagah hai!","operating system":"Operating system ek system software hai jo computer hardware ko manage karta hai. Windows, Linux, macOS popular OS hain.","artificial intelligence":"AI machines ko intelligent banata hai! Machine Learning, Deep Learning, NLP — sab AI ke parts hain.","machine learning":"Machine Learning AI ka dil hai! Computers data se khud seekhte hain.","computer":"Computer ek electronic device hai jo data process karta hai. CPU, RAM, Storage main components hain.","internet":"Internet ek global network hai! WWW, email, social media — sab internet pe hai.","india":"India ek mahan desh hai! 1.4 billion logon ka desh, duniya ka sabse bada democracy!","cricket":"Cricket India ka dharam hai Boss! Virat Kohli, Rohit Sharma, MS Dhoni — legends!","health":"Sehat sabse badi daulat hai Boss! Regular exercise, balanced diet, poori neend — zaruri hain.","education":"Shiksha sabse powerful weapon hai! Yeh career, thinking aur life improve karti hai.","narendra modi":"Narendra Modi India ke 14ve Prime Minister hain. 2014 se PM hain. Gujarat ke CM bhi rahe hain. Development aur Digital India unka vision hai.","modi":"Narendra Modi India ke Prime Minister hain. BJP ke neta hain. India ko vishwa shakti banana unka sapna hai.","parul university":"Parul University Vadodara, Gujarat mein hai. Engineering, medical, management courses offer karti hai. Contact: 1800-123-5555.","vadodara":"Vadodara Gujarat ka ek important sheher hai. Baroda ke naam se bhi jaana jaata hai. Laxmi Vilas Palace famous hai.","gujarat":"Gujarat India ka vibrant state hai! Business capital, garba dance, dhokla — culture ke liye famous!","exam":"Exam tips Boss! Regular schedule banao, short notes likhte jao, previous papers solve karo. Pass zaroor hoge!","college":"College life amazing experience hai! Naye dost, naya knowledge, naye opportunities!","business":"Business mein risk aur reward dono hain! Achha idea + mehnat + patience = success!","money":"Paisa zaruri hai, lekin sab kuch nahi Boss! Mehnat karo, save karo, invest karo.","love":"Pyar ek khoobsurat ehsaas hai Boss! Yeh relationships ko mazboot banata hai.","life":"Zindagi ek anmol tohfa hai Boss! Ise khushi, mehnat aur pyar se jeena chahiye.","success":"Safalta ke liye clear goal set karo, mehnat karo, consistent raho, kabhi haar mat mano!","programming":"Programming computers ko instructions dene ki kala hai! Software, apps, websites — sab programming se banta hai.","game":"Gaming ek popular hobby hai! PUBG, Free Fire, GTA — popular games hain.","movie":"Movies ek art form hai Boss! Bollywood, Hollywood — entertainment ki duniya.","music":"Music soul ki bhasha hai! Mood improve karta hai, stress kam karta hai.","food":"Khana zindagi ka important hissa hai! Biryani, dal makhani, dosa — India mein kitne delicious dishes!"}
    # Sat Saheb
    if any(w in t for w in ["sat saheb","sat sahib","satsaheb"]) or "sat saheb" in raw.lower():
        return "Sat Saheb Ji! Kabir Saheb ki jai! Aap kaise hain? Kya seva kar sakta hoon?"
    # Rutvik - best friend
    if "rutvik" in t:
        return "Rutvik aapka sabse achha dost hai Boss! Woh bahut achha insaan hai. Unke baare mein aur kya jaanna chahte hain?"
    # Family details
    if any(w in t for w in ["papa","pita","father","bapu"]):
        return "Aapke Papa ka naam Ritik ke ghar ke mukhiya hain. Woh bahut mehnat karte hain aur family ka dhyan rakhte hain."
    if any(w in t for w in ["mummy","maa","mother","mata","mummy"]):
        return "Aapki Mummy bahut pyaari hain! Ghar ki lakshmi hain woh. Unka aashirwad hamesha aapke saath hai."
    if any(w in t for w in ["riya","riya didi"]):
        return "Riya aapki family member hain. Bahut achhi hain woh!"
    if any(w in t for w in ["gudiya","gudiya didi"]):
        return "Gudiya Didi bahut pyaari hain! Family mein unka bahut important role hai."
    if any(w in t for w in ["dada","dadi","dadaji","dadiji"]):
        return "Dada-Dadi aapke ghar ke aadhar stambh hain! Unka aashirwad sabse keemti hai."
    if any(w in t for w in ["kaka","kaki","chacha","chachi"]):
        return "Kaka-Kaki bahut achhe hain! Family mein unka bahut pyaar hai."
    if any(w in t for w in ["puja"]):
        return "Puja family ki ek pyaari member hain!"
    if any(w in t for w in ["chirag"]):
        return "Chirag family ka ek important member hai!"
    if any(w in t for w in ["kabir saheb","kabir sahib","sant kabir"]):
        return "Kabir Saheb ek mahan sant the! Unke dohe aaj bhi logon ko raah dikhate hain. 'Dukh mein simran sab kare, sukh mein kare na koi.'"
    if any(w in t for w in ["sant rampal","rampalji","rampal ji"]):
        return "Sant Rampalji Maharaj ek mahan sant hain jo Kabir Saheb ke updesh ko aage badha rahe hain. Satlok Ashram unka main kendra hai."
    for key,ans in topics.items():
        if key in t:return ans
    deva={"kem cho":"Hu saras chhu Boss! Tame kem cho? Hu tamari shu madad kari shakhu?","kem":"Hu saras chhu Boss! Tame kem cho?","kem chho":"Hu bilkul saras chhu Boss! Tame kem chho?","tane kone banayu":"Mane Ritik Boss e banavio chhe! Hu RK chhu, temno personal AI assistant.","kon chhe tu":"Hu RK chhu, Ritik Boss no personal AI assistant! Commands execute karu chhu ane prashno na jawab aaphu chhu.","shu kari shake":"Boss, hu YouTube/Google/WhatsApp/Chrome kholi shakhu, apps open/close, volume control, screenshot, time/date, shutdown/restart ane prashno na jawab aapi shakhu!","narendra modi":"Narendra Modi India na 14ma Prime Minister chhe. 2014 thi PM chhe. Gujarat na CM pan rahe chhe.","parul":"Parul University Vadodara, Gujarat ma chhe. Engineering, medical, management courses offer kare chhe.","sat saheb":"Sat Saheb Ji! Kabir Saheb ki jai!","rutvik":"Rutvik tamaro sabse achho dost chhe Boss!","कैसे हो":"Main bilkul theek hoon Boss! Aap kaise hain? Kya madad kar sakta hoon?","नरेंद्र मोदी":"Narendra Modi India ke 14ve Prime Minister hain. 2014 se PM hain. Gujarat ke CM bhi rahe hain.","मोदी":"Narendra Modi India ke Prime Minister hain. BJP ke neta hain.","पारुल":"Parul University Vadodara, Gujarat mein hai. Engineering, medical, management courses offer karti hai.","वडोदरा":"Vadodara Gujarat ka ek important sheher hai. Baroda ke naam se bhi jaana jaata hai.","sat saheb":"Sat Saheb Ji! Kabir Saheb ki jai! Aap kaise hain?"}
    for key,ans in deva.items():
        if key in raw.lower() or key in t:return ans
    return {"hi":f"Boss, samajh gaya! Kya aap aur detail mein bata sakte hain?","en":f"Boss, got it! Can you give more details?","gu":f"Boss, samji gayo! Thodu vahu detail aapi shako?","mr":f"Boss, samjalo! Thodi jast mahiti deu shakata ka?"}.get(lang,"Boss, samajh gaya! Kya aur detail mein bata sakte hain?")
def run_cmd(t,raw,lang):
    # Sat Saheb
    if any(w in t for w in ["sat saheb","sat sahib","satsaheb"]):
        return "Sat Saheb Ji! Kabir Saheb ki jai! Kya seva kar sakta hoon?","none",""
    # Voice change
    if any(w in t for w in ["change voice to female","ladki ki awaaz","female voice","girl voice","voice female"]):
        return "Voice female kar di Boss!","set_voice_female",""
    if any(w in t for w in ["change voice to male","ladka ki awaaz","male voice","boy voice","voice male"]):
        return "Voice male kar di Boss!","set_voice_male",""
    if any(w in t for w in ["slow bolo","slow voice","dheere bolo"]):
        return "Ab dheere bolunga Boss!","set_speed_slow",""
    if any(w in t for w in ["fast bolo","tez bolo","fast voice"]):
        return "Ab tez bolunga Boss!","set_speed_fast",""
    if any(w in t for w in ["normal speed","normal bolo","normal voice"]):
        return "Normal speed pe aa gaya Boss!","set_speed_normal",""
    if any(w in t for w in ["gujarati me","gujarati mein","gujarati ma"]):return "Okay Boss! Hu havi Gujarati ma vaat karish!","set_lang_gu",""
    if any(w in t for w in ["marathi me","marathi mein","marathi madhe"]):return "Okay Boss! Aata mi Marathi madhe bolto!","set_lang_mr",""
    if any(w in t for w in ["hindi me","hindi mein","speak hindi"]):return "Okay Boss! Ab main Hindi mein bolunga!","set_lang_hi",""
    if any(w in t for w in ["english me","speak english","english mein"]):return "Sure Boss! Speaking in English now!","set_lang_en",""
    if any(w in t for w in ["shutdown","pc band karo","system band karo"]):os.system("shutdown /s /t 10");return "Boss, system 10s mein shutdown!","none",""
    if any(w in t for w in ["restart","reboot","pc restart"]):os.system("shutdown /r /t 10");return "Boss, system restart ho raha hai!","none",""
    if any(w in t for w in ["volume up","awaz badhao","awaaz badhao"]):
        try:[ctypes.windll.user32.keybd_event(0xAF,0,0,0) for _ in range(5)]
        except:pass
        return "Awaaz badha di Boss!","none",""
    if any(w in t for w in ["volume down","awaz kam","awaaz kam"]):
        try:[ctypes.windll.user32.keybd_event(0xAE,0,0,0) for _ in range(5)]
        except:pass
        return "Awaaz kam kar di Boss!","none",""
    if "mute" in t:
        try:ctypes.windll.user32.keybd_event(0xAD,0,0,0)
        except:pass
        return "Mute kar diya Boss!","none",""
    if any(w in t for w in ["battery","charge"]):
        res=subprocess.run("powershell (Get-CimInstance -ClassName Win32_Battery).EstimatedChargeRemaining",capture_output=True,text=True,shell=True).stdout.strip()
        return (f"Boss, battery {res}% hai!" if res and res.isdigit() else "Boss, battery info nahi mili."),"none",""
    if any(w in t for w in ["screenshot","screen capture"]):
        ps="[Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');[Reflection.Assembly]::LoadWithPartialName('System.Drawing');$s=[System.Windows.Forms.Screen]::PrimaryScreen;$b=New-Object System.Drawing.Bitmap($s.Bounds.Width,$s.Bounds.Height);$g=[System.Drawing.Graphics]::FromImage($b);$g.CopyFromScreen($s.Bounds.X,$s.Bounds.Y,0,0,$b.Size);$b.Save('screenshot.png',[System.Drawing.Imaging.ImageFormat]::Png);$g.Dispose();$b.Dispose();"
        subprocess.run(["powershell","-Command",ps],shell=True)
        return "Screenshot le liya Boss!","none",""
    if any(w in t for w in ["time","kitne baje","samay"]):
        now=datetime.now()
        return {"hi":f"Boss, abhi {now.strftime('%I:%M %p')} baje hain!","en":f"Boss, it is {now.strftime('%I:%M %p')}!","gu":f"Boss, abhi {now.strftime('%I:%M %p')} vagya chhe!","mr":f"Boss, aata {now.strftime('%I:%M %p')} vajale!"}.get(lang,f"Abhi {now.strftime('%I:%M %p')} baje hain!"),"none",""
    if any(w in t for w in ["date","tarikh","aaj kya"]):
        now=datetime.now()
        return {"hi":f"Boss, aaj {now.strftime('%d %B %Y')} hai!","en":f"Boss, today is {now.strftime('%d %B %Y')}!","gu":f"Boss, aaj {now.strftime('%d %B %Y')} chhe!","mr":f"Boss, aaj {now.strftime('%d %B %Y')} aahe!"}.get(lang,f"Aaj {now.strftime('%d %B %Y')} hai!"),"none",""
    if any(w in t for w in ["close","band karo","band kar","kill"]):
        cm={"chrome":"chrome.exe","notepad":"notepad.exe","paint":"mspaint.exe","vs code":"Code.exe","vscode":"Code.exe"}
        for n,e in cm.items():
            if n in t:os.system(f"taskkill /IM {e} /F");return f"{n.title()} band kar diya Boss!","none",""
    if (("play" in t or "chalao" in t) and ("youtube" in t or "song" in t or "music" in t or "gana" in t)) or "gaana" in t:
        q=t
        for w in ["play","on youtube","youtube par","youtube","chalao","song","gana","gaana","music","par","open","kholo"]:q=q.replace(w,"")
        q=q.strip()
        if q and len(q)>1:
            url="https://www.youtube.com/results?search_query="+urllib.parse.quote(q)
            webbrowser.open(url);return f"YouTube par '{q}' chala raha hoon Boss!","open_url",url
        webbrowser.open("https://youtube.com");return "YouTube khol diya Boss!","open_url","https://youtube.com"
    if "google" in t and any(w in t for w in ["search","khojo","dhundo","karo","par"]):
        q=t
        for w in ["google par search karo","search on google","google mein search karo","google search","google","search","karo","par"]:q=q.replace(w,"")
        q=q.strip()
        if q and len(q)>1:
            url="https://www.google.com/search?q="+urllib.parse.quote(q)
            webbrowser.open(url);return f"Google par '{q}' search kar raha hoon Boss!","open_url",url
    SITES={"youtube":("https://youtube.com","YouTube khol diya Boss!"),"whatsapp":("https://web.whatsapp.com","WhatsApp khol diya Boss!"),"instagram":("https://instagram.com","Instagram khol diya Boss!"),"facebook":("https://facebook.com","Facebook khol diya Boss!"),"twitter":("https://twitter.com","Twitter khol diya Boss!"),"gmail":("https://mail.google.com","Gmail khol diya Boss!"),"google":("https://google.com","Google khol diya Boss!"),"github":("https://github.com","GitHub khol diya Boss!"),"netflix":("https://netflix.com","Netflix khol diya Boss!")}
    APPS={"chrome":"start chrome","notepad":"notepad","calculator":"calc","paint":"mspaint","cmd":"start cmd","settings":"start ms-settings:","file explorer":"explorer","vs code":"code","vscode":"code","task manager":"taskmgr","camera":"start microsoft.windows.camera:"}
    OW=["open","kholo","launch","start","chalao","khol","ughad"]
    if any(w in t for w in OW) or any(w in raw for w in ["ओपन","खोलो"]):
        for s,(u,m) in SITES.items():
            if s in t:webbrowser.open(u);return m,"open_url",u
        for n,c in APPS.items():
            if n in t:os.system(c);return f"{n.title()} khol diya Boss!","none",""
    for s,(u,m) in SITES.items():
        if s in t:webbrowser.open(u);return m,"open_url",u
    return None
@app.get("/",response_class=HTMLResponse)
async def home():
    return HTMLResponse((BASE/"static"/"index.html").read_text(encoding="utf-8"))

@app.post("/chat")
async def chat(request:Request):
    try:
        data=await request.json()
        user_msg=str(data.get("message","")).strip()
        lang=str(data.get("lang","hi"))
        sid=str(data.get("session","default"))
        dl=detect_lang(user_msg)
        if dl:lang=dl
        t=user_msg.lower().strip()
        print(f"[USER|{lang}] {user_msg}")
        if not t:return JSONResponse({"reply":"Haan Boss, boliye!","action":"none","url":""})
        hist=get_hist(sid)
        m=re.search(r"(?:my name is|mera naam|maro naam)\s+([A-Za-z]+)",user_msg,re.I)
        if m:_names[sid]=m.group(1).title()
        if any(w in t for w in ["mera naam kya","what is my name"]):
            n=_names.get(sid)
            return JSONResponse({"reply":f"Aapka naam {n} hai Boss!" if n else "Boss, naam nahi bataya!","action":"none","url":""})
        if any(w in t for w in ["gujarati me","gujarati mein","gujarati ma"]):return JSONResponse({"reply":"Okay Boss! Hu havi Gujarati ma vaat karish!","action":"set_lang_gu","url":""})
        if any(w in t for w in ["marathi me","marathi mein","marathi madhe"]):return JSONResponse({"reply":"Okay Boss! Aata mi Marathi madhe bolto!","action":"set_lang_mr","url":""})
        if any(w in t for w in ["hindi me","hindi mein","speak hindi"]):return JSONResponse({"reply":"Okay Boss! Ab main Hindi mein bolunga!","action":"set_lang_hi","url":""})
        if any(w in t for w in ["english me","speak english","english mein"]):return JSONResponse({"reply":"Sure Boss! Speaking in English now!","action":"set_lang_en","url":""})
        r=run_cmd(t,user_msg,lang)
        if r:
            reply,action,url=r
            print(f"[CMD] {reply[:50]}")
            return JSONResponse({"reply":reply,"action":action,"url":url})
        hist.append({"role":"user","msg":user_msg})
        reply=ask_ai(user_msg,lang,hist,_names.get(sid,"")) or smart_reply(user_msg,lang)
        hist.append({"role":"assistant","msg":reply})
        print(f"[AI] {reply[:60]}")
        return JSONResponse({"reply":reply,"action":"none","url":""})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"reply":smart_reply(str(data.get("message","")),str(data.get("lang","hi"))),"action":"none","url":""})