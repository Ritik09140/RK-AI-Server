// ============================================================
// RK AI — Next Generation Assistant v4.0
// Created by Ritik Boss
// ============================================================

// --- DOM References ---
const robotUnit = document.getElementById('robot-unit');
const robotMouth = document.getElementById('robot-mouth');
const robotState = document.getElementById('robot-state');
const statusTxt = document.getElementById('status-txt');
const statusDot = document.getElementById('status-dot');
const micBtn = document.getElementById('mic-btn');
const micIcon = document.getElementById('mic-icon');
const micStatus = document.getElementById('mic-status');
const sendBtn = document.getElementById('send-btn');
const textInput = document.getElementById('text-input');
const chatMessages = document.getElementById('chat-messages');
const clearBtn = document.getElementById('clear-btn');
const typingIndicator = document.getElementById('typing-indicator');
const bootScreen = document.getElementById('boot-screen');
const appMain = document.getElementById('app');

// --- Initialization ---
let mouthSegments = [];
for (let i = 0; i < 7; i++) {
    const seg = document.createElement('div');
    seg.className = 'mouth-segment';
    seg.style.left = (i * 10 + 2) + 'px';
    seg.style.height = '4px';
    robotMouth.appendChild(seg);
    mouthSegments.push(seg);
}

// --- State Machine ---
const STATES = {
    IDLE: { cls: '', label: '● READY', status: 'SYSTEM READY', color: '#00f5ff' },
    LISTENING: { cls: 'listening', label: '● LISTENING...', status: 'MIC ACTIVE', color: '#ff0090' },
    THINKING: { cls: 'thinking', label: '● PROCESSING...', status: 'AI PROCESSING', color: '#8b00ff' },
    SPEAKING: { cls: 'speaking', label: '● SPEAKING...', status: 'VOICE OUTPUT', color: '#00ff88' }
};

function setSystemState(name) {
    const s = STATES[name];
    if (!s) return;
    
    // Reset emotional classes
    robotUnit.classList.remove('listening', 'thinking', 'speaking', 'joy', 'surprise');
    if (s.cls) robotUnit.classList.add(s.cls);

    robotState.textContent = s.label;
    robotState.style.color = s.color;
    statusTxt.textContent = s.status;
    statusDot.style.background = s.color;
    statusDot.style.boxShadow = `0 0 10px ${s.color}`;
}

// --- Language Management ---
let currentLang = 'hi';
const langMap = { hi: 'hi-IN', gu: 'gu-IN', mr: 'mr-IN', en: 'en-US' };

document.querySelectorAll('.lang-pill').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.lang-pill').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentLang = btn.dataset.lang;
        if (recognition) recognition.lang = langMap[currentLang];
        
        const msgs = { 
            hi: 'Hindi mode active! 🇮🇳', 
            en: 'English mode active! 🌍', 
            gu: 'Gujarati mode active! 🏠', 
            mr: 'Marathi mode active! 🙏' 
        };
        addMessage(msgs[currentLang], false);
        speakText(msgs[currentLang]);
    });
});

function triggerReaction(text) {
    const t = text.toLowerCase();
    robotUnit.classList.remove('joy', 'surprise', 'love');
    
    // Love/Affection keywords (AI responses or User input)
    if (t.includes('pyaar') || t.includes('love') || t.includes('heart') || t.includes('dil') || t.includes('❤️') || t.includes('boss')) {
        robotUnit.classList.add('love');
        setTimeout(() => robotUnit.classList.remove('love'), 5000);
    }
    // Joyful/Happy keywords
    else if (t.includes('haha') || t.includes('😊') || t.includes('😄') || t.includes('achha') || t.includes('swagat') || t.includes('shukriya') || t.includes('good')) {
        robotUnit.classList.add('joy');
        setTimeout(() => robotUnit.classList.remove('joy'), 4000);
    } 
    // Surprised/Questioning keywords
    else if (t.includes('oh!') || t.includes('arey') || t.includes('vau') || t.includes('shock') || t.includes('!') || t.includes('sachi') || t.includes('kya?')) {
        robotUnit.classList.add('surprise');
        setTimeout(() => robotUnit.classList.remove('surprise'), 2500);
    }
}

// --- Chat View ---
// Configure Marked
marked.setOptions({
    breaks: true,
    gfm: true
});

function addMessage(text, isUser = false) {
    const div = document.createElement('div');
    div.className = `msg ${isUser ? 'user' : 'ai'}`;
    const icon = isUser ? 'fa-user' : 'fa-robot';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    // Trigger visual reaction for both user and AI text
    triggerReaction(text);

    const htmlContent = isUser ? text : marked.parse(text);
    
    div.innerHTML = `
        <div class="msg-avatar"><i class="fa-solid ${icon}"></i></div>
        <div class="msg-bubble">
            <div class="msg-content">${htmlContent}</div>
            <span class="msg-time">${time}</span>
        </div>`;
    
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

clearBtn.addEventListener('click', () => {
    chatMessages.innerHTML = '';
    addMessage('Memory cleared boss. Main hamesha yahan hoon.', false);
});

// --- Request State Control ---
const REQ_CACHE = new Map(); // Last 10 Questions Cache
let isProcessing = false;
let lastRequestTime = 0;
let quotaLimitReached = false;
const COOLDOWN_MS = 3500; // 3.5s delay

// --- Speech Recognition ---
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let micEnabled = true;
let isSpeaking = false;
let isRecording = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = langMap[currentLang];

    recognition.onstart = () => {
        isRecording = true;
        setSystemState('LISTENING');
        micBtn.classList.add('active');
        micStatus.textContent = '🎤 LISTENING';
    };

    recognition.onresult = async (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
        if (!transcript) return;

        // Force stop logic
        if (transcript.includes('chup') || transcript.includes('stop') || transcript.includes('ruk') || transcript.includes('shant')) {
            window.speechSynthesis.cancel();
            if (window.currentAudio) { window.currentAudio.pause(); window.currentAudio.currentTime = 0; }
            isSpeaking = false;
            isProcessing = false;
            stopMouthAnimation();
            setSystemState('IDLE');
            addMessage("Thik hai boss, chup ho gayi. 🤐", false);
            return;
        }

        // ECHO PREVENTER: If we are speaking, absolutely ignore all recognition text!
        if (isSpeaking) return;

        // CLIENT-SIDE OS COMMANDS
        if (transcript.includes("open youtube") || transcript.includes("youtube kholo") || transcript.includes("youtube chalu")) { window.open("https://youtube.com", "_blank"); addMessage(transcript, true); addMessage("YouTube open kar rahi hu boss! 📺", false); return; }
        if (transcript.includes("open google") || transcript.includes("google kholo") || transcript.includes("google chalu")) { window.open("https://google.com", "_blank"); addMessage(transcript, true); addMessage("Google open kiya boss! 🌐", false); return; }
        if (transcript.includes("call") && transcript.includes("karo")) { window.open("tel:"); addMessage(transcript, true); addMessage("Call dialer open kiya boss! 📞", false); return; }
        if (transcript.includes("camera") && (transcript.includes("open") || transcript.includes("kholo") || transcript.includes("chalu"))) { 
             const cb = document.getElementById('cam-btn');
             if(cb) cb.click();
             addMessage(transcript, true); addMessage("Camera open ho raha hai boss! 📷", false);
             return;
        }

        addMessage(transcript, true);
        await handleCommand(transcript);
    };

    recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove('active');
        // Restart if mic is enabled, even if speaking (to allow stop command)
        if (micEnabled && !isProcessing) {
            setTimeout(() => { try { recognition.start(); } catch(e){} }, 400);
        } else {
            setSystemState('IDLE');
            micStatus.textContent = micEnabled ? '🎤 MIC ON' : '🔇 MIC OFF';
        }
    };
}

micBtn.addEventListener('click', () => {
    micEnabled = !micEnabled;
    if (micEnabled) {
        micBtn.classList.remove('muted');
        micIcon.className = 'fa-solid fa-microphone';
        try { recognition.start(); } catch(e){}
    } else {
        micBtn.classList.add('muted');
        micIcon.className = 'fa-solid fa-microphone-slash';
        try { recognition.stop(); } catch(e){}
        setSystemState('IDLE');
    }
});

// --- UI Actions & Controls ---
sendBtn.addEventListener('click', () => {
    if (isProcessing) return;
    
    const val = textInput.value.trim();
    if (!val) return;

    if (quotaLimitReached) {
        const limitMsg = "Aaj ka free limit khatam ho gaya hai Boss Ritik, kal fir try kare 😊";
        addMessage(limitMsg, false);
        speakText(limitMsg);
        return;
    }

    const now = Date.now();
    if (now - lastRequestTime < COOLDOWN_MS) {
        addMessage("Thodi der ruk jaiye Boss Ritik, system process kar raha hai 😊", false);
        return;
    }

    textInput.value = '';
    addMessage(val, true);
    handleCommand(val);
});
textInput.addEventListener('keypress', e => { if (e.key === 'Enter') sendBtn.click(); });

// --- AI Handler (v4.5 — Smart Quota & Cache) ---
async function handleCommand(text) {
    if (isProcessing) return;
    
    // Explicitly kill mic while thinking/fetching to avoid recording ambient noise
    if (recognition && isRecording) { try { recognition.abort(); } catch(e){} }
    
    const query = text.toLowerCase().trim();

    // 1. Check Cache
    if (REQ_CACHE.has(query)) {
        setSystemState('THINKING');
        setTimeout(() => {
            const cachedReply = REQ_CACHE.get(query);
            addMessage(cachedReply, false);
            speakText(cachedReply);
        }, 500);
        return;
    }

    // 2. State update
    isProcessing = true;
    lastRequestTime = Date.now();
    sendBtn.disabled = true;
    textInput.disabled = true;
    setSystemState('THINKING');
    typingIndicator.classList.add('visible');

    try {
        const res = await fetch('/api/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: query, client_lang: currentLang })
        });
        const data = await res.json();
        
        typingIndicator.classList.remove('visible');

        // 3. Quota Handle (New message as per request)
        if (data.status === 'quota_limit') {
            quotaLimitReached = true;
            addMessage(data.reply, false);
            speakText(data.reply);
            return;
        }

        const reply = data.reply || "Kuch problem hui boss, firse try kare.";
        addMessage(reply, false);
        speakText(reply);

        // 4. Update Cache (Max 10)
        if (data.status === 'success') {
            REQ_CACHE.set(query, reply);
            if (REQ_CACHE.size > 10) {
                const lastKey = REQ_CACHE.keys().next().value;
                REQ_CACHE.delete(lastKey);
            }
        }

    } catch (e) {
        typingIndicator.classList.remove('visible');
        setSystemState('IDLE');
        addMessage("Net connection check karo Boss, kuch gadbad lag rahi hai.", false);
    } finally {
        isProcessing = false;
        sendBtn.disabled = false;
        textInput.disabled = false;
    }
}

// --- TTS Engine (v4.5 — Soft, Slow, Calm) ---
function speakText(text) {
    if (!text) return;
    
    // Trigger emotional visual reaction
    triggerReaction(text);
    
    // Stop any previous browser tts just in case
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    
    const cleanText = text.replace(/[*_#`~]/g, '').trim();
    if (!cleanText) return;

    let lang = currentLang || 'hi';
    if (/[\u0A80-\u0AFF]/.test(text)) lang = 'gu';
    else if (/[\u0900-\u097F]/.test(text)) lang = 'hi';

    isSpeaking = true;
    setSystemState('SPEAKING');
    startMouthAnimation();

    fetch('/api/tts/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: cleanText, lang: lang })
    })
    .then(res => {
        if (!res.ok) throw new Error('API TTS failed');
        return res.blob();
    })
    .then(blob => {
        const audioUrl = URL.createObjectURL(blob);
        window.currentAudio = new Audio(audioUrl);
        window.currentAudio.onended = () => {
            setTimeout(() => {
                isSpeaking = false;
                stopMouthAnimation();
                setSystemState('IDLE');
                if (micEnabled) restartRecognition();
            }, 1200); // Wait for room echo to die down
        };
        window.currentAudio.onerror = () => {
            isSpeaking = false;
            stopMouthAnimation();
            setSystemState('IDLE');
        };
        window.currentAudio.play().catch(e => {
            console.error('Audio play error:', e);
            isSpeaking = false;
            stopMouthAnimation();
            setSystemState('IDLE');
            if (micEnabled) restartRecognition();
        });
    })
    .catch(e => {
        console.error(e);
        isSpeaking = false;
        stopMouthAnimation();
        setSystemState('IDLE');
        if (micEnabled) restartRecognition();
    });
}

function splitIntoChunks(str, l) {
    let chunks = [];
    let words = str.split(' ');
    let current = "";
    words.forEach(w => {
        if ((current + w).length < l) {
            current += (current ? " " : "") + w;
        } else {
            chunks.push(current);
            current = w;
        }
    });
    if (current) chunks.push(current);
    return chunks;
}

function restartRecognition() {
    setTimeout(() => {
        if (micEnabled && !isSpeaking && !isRecording && !isProcessing) {
            try { recognition.start(); } catch(e){}
        }
    }, 600);
}

// --- Mouth Animation ---
let mouthInterval;
function startMouthAnimation() {
    mouthInterval = setInterval(() => {
        mouthSegments.forEach(seg => {
            seg.style.height = (Math.random() * 16 + 2) + 'px';
        });
    }, 80);
}

function stopMouthAnimation() {
    clearInterval(mouthInterval);
    mouthSegments.forEach(seg => seg.style.height = '4px');
}

// --- Launch Boot sequence ---
bootScreen.addEventListener('click', () => {
    bootScreen.style.opacity = '0';
    setTimeout(() => {
        bootScreen.remove();
        appMain.style.display = 'flex';
        if (micEnabled && recognition && !isProcessing) try { recognition.start(); } catch(e){}
        const greeting = "Namaste mere Ritik Boss 😊... Main aapki RK Female AI Assistant hoon! Aapka swagat hai. Main hamesha aapki madad ke liye yahan hoon... bataiye aaj kya karna hai?";
        addMessage(greeting, false);
        speakText(greeting);
    }, 800);
});

// --- File & Camera Handlers ---
const fileBtn = document.getElementById('file-btn');
const camBtn = document.getElementById('cam-btn');
const fileInput = document.getElementById('file-input');

if (fileBtn) fileBtn.addEventListener('click', () => { fileInput.removeAttribute('capture'); fileInput.accept='image/*,.pdf,.txt,.doc'; fileInput.click(); });
if (camBtn) camBtn.addEventListener('click', () => { fileInput.accept='image/*'; fileInput.setAttribute('capture', 'environment'); fileInput.click(); });

if (fileInput) {
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const fileName = e.target.files[0].name;
            addMessage(`File attached: ${fileName}`, true);
            handleCommand(`Maine ek file bheji hai: ${fileName}. Iske bare me summary do.`);
        }
    });
}

// Warm up voices
window.speechSynthesis.getVoices();
console.log("🚀 RK AI v4.5 STABLE.");
