// Jarvis V2 — Frontend
const orb = document.getElementById('orb');
const status = document.getElementById('status');
const transcript = document.getElementById('transcript');
const muteBtn = document.getElementById('mute-btn');

const TARGET_SAMPLE_RATE = 16000;
const VAD_RMS_THRESHOLD = 0.015;   // minimaler Pegel für "Sprache"
const VAD_SILENCE_MS = 900;         // so lange Stille = Ende der Äußerung
const MIN_SPEECH_MS = 300;          // unter dieser Dauer wird ignoriert
const PREROLL_MS = 200;             // Puffer vor dem Speech-Start mitschicken

let ws;
let audioQueue = [];
let isPlaying = false;
let audioUnlocked = false;
let isJarvisSpeaking = false;
let micReady = false;
let audioCtx = null;
let micStream = null;
let workletNode = null;
let preroll = [];
let speechBuffer = [];
let inSpeech = false;
let speechStartTs = 0;
let silenceStartTs = 0;
let listening = false;
let muted = false;

function unlockAudio() {
    if (!audioUnlocked) {
        const silent = new Audio('data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAABhgC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAAAYZNIGPkAAAAAAAAAAAAAAAAAAAA');
        silent.play().then(() => { audioUnlocked = true; }).catch(() => {});
    }
}

function connect() {
    ws = new WebSocket(`ws://${location.host}/ws`);
    ws.binaryType = 'arraybuffer';
    ws.onopen = () => {
        console.log('[jarvis] WebSocket connected');
        status.textContent = 'Klicke den Orb um Mikrofon zu starten.';
        setOrbState('idle');
        ws.send(JSON.stringify({ text: 'Jarvis activate' }));
    };
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'response') {
            if (data.text) addTranscript('jarvis', data.text);
            if (data.audio && data.audio.length > 0) {
                queueAudio(data.audio, data.mime || 'audio/mpeg');
            } else if (!data.text) {
                setOrbState('idle');
            }
        } else if (data.type === 'status') {
            status.textContent = data.text;
        } else if (data.type === 'transcription') {
            addTranscript('user', data.text);
            setOrbState('thinking');
            status.textContent = 'Jarvis denkt nach...';
        }
    };
    ws.onclose = () => {
        status.textContent = 'Verbindung verloren...';
        setTimeout(connect, 3000);
    };
}

function queueAudio(base64Audio, mime) {
    audioQueue.push({ b64: base64Audio, mime: mime || 'audio/mpeg' });
    if (!isPlaying) playNext();
}

function playNext() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        isJarvisSpeaking = false;
        if (micReady) {
            setOrbState('listening');
            listening = true;
        } else {
            setOrbState('idle');
        }
        status.textContent = '';
        return;
    }
    isPlaying = true;
    isJarvisSpeaking = true;
    listening = false;
    setOrbState('speaking');
    status.textContent = '';

    const { b64, mime } = audioQueue.shift();
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: mime });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => { URL.revokeObjectURL(url); playNext(); };
    audio.onerror = () => { URL.revokeObjectURL(url); playNext(); };
    audio.play().catch(err => {
        console.warn('[jarvis] Autoplay blocked, waiting for click...');
        status.textContent = 'Klicke irgendwo damit Jarvis sprechen kann.';
        setOrbState('idle');
        document.addEventListener('click', function retry() {
            document.removeEventListener('click', retry);
            audio.play().then(() => {
                setOrbState('speaking');
                status.textContent = '';
            }).catch(() => playNext());
        });
    });
}

async function startMic() {
    if (micReady) return;
    try {
        micStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
        });
        audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: TARGET_SAMPLE_RATE });

        const workletCode = `
            class PcmCapture extends AudioWorkletProcessor {
                process(inputs) {
                    const input = inputs[0];
                    if (input && input[0]) {
                        this.port.postMessage(input[0].slice(0));
                    }
                    return true;
                }
            }
            registerProcessor('pcm-capture', PcmCapture);
        `;
        const blob = new Blob([workletCode], { type: 'application/javascript' });
        const workletUrl = URL.createObjectURL(blob);
        await audioCtx.audioWorklet.addModule(workletUrl);
        URL.revokeObjectURL(workletUrl);

        const source = audioCtx.createMediaStreamSource(micStream);
        workletNode = new AudioWorkletNode(audioCtx, 'pcm-capture');
        workletNode.port.onmessage = (e) => handleAudioChunk(e.data);
        source.connect(workletNode);

        micReady = true;
        listening = true;
        setOrbState('listening');
        status.textContent = 'Höre zu...';
        console.log('[jarvis] Mikrofon bereit, SR=', audioCtx.sampleRate);
    } catch (err) {
        console.error('[jarvis] getUserMedia failed:', err);
        status.textContent = 'Mikrofon-Zugriff verweigert.';
    }
}

function rms(samples) {
    let sum = 0;
    for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
    return Math.sqrt(sum / samples.length);
}

function handleAudioChunk(chunk) {
    if (isJarvisSpeaking || !listening || muted) return;

    const level = rms(chunk);
    const now = performance.now();
    const chunkMs = (chunk.length / TARGET_SAMPLE_RATE) * 1000;

    // Pre-roll buffer (kurzer Zeitraum vor Beginn der Sprache)
    preroll.push(chunk);
    const prerollChunks = Math.ceil(PREROLL_MS / chunkMs) + 1;
    if (preroll.length > prerollChunks) preroll.shift();

    if (level > VAD_RMS_THRESHOLD) {
        if (!inSpeech) {
            inSpeech = true;
            speechStartTs = now;
            speechBuffer = [...preroll];
            setOrbState('hearing');
        } else {
            speechBuffer.push(chunk);
        }
        silenceStartTs = 0;
    } else if (inSpeech) {
        speechBuffer.push(chunk);
        if (silenceStartTs === 0) silenceStartTs = now;
        if (now - silenceStartTs >= VAD_SILENCE_MS) {
            const durationMs = now - speechStartTs;
            inSpeech = false;
            silenceStartTs = 0;
            if (durationMs >= MIN_SPEECH_MS) {
                flushToServer(speechBuffer);
            }
            speechBuffer = [];
            setOrbState('listening');
        }
    }
}

function flushToServer(chunks) {
    const total = chunks.reduce((s, c) => s + c.length, 0);
    const merged = new Float32Array(total);
    let off = 0;
    for (const c of chunks) { merged.set(c, off); off += c.length; }
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(merged.buffer);
        status.textContent = 'Transkribiere...';
        setOrbState('thinking');
    }
}

function setMuted(value) {
    muted = value;
    if (micStream) {
        for (const track of micStream.getAudioTracks()) track.enabled = !muted;
    }
    if (muted) {
        inSpeech = false;
        speechBuffer = [];
        silenceStartTs = 0;
        muteBtn.classList.add('muted');
        muteBtn.textContent = '🔇 Mic aus';
        muteBtn.setAttribute('aria-pressed', 'true');
        status.textContent = 'Stumm. Jarvis hört nicht mit.';
        if (!isJarvisSpeaking) setOrbState('idle');
    } else {
        muteBtn.classList.remove('muted');
        muteBtn.textContent = '🎤 Mic an';
        muteBtn.setAttribute('aria-pressed', 'false');
        if (micReady && !isJarvisSpeaking) {
            listening = true;
            setOrbState('listening');
            status.textContent = 'Höre zu...';
        }
    }
}

muteBtn.addEventListener('click', () => setMuted(!muted));

orb.addEventListener('click', async () => {
    unlockAudio();
    if (!micReady) {
        await startMic();
        return;
    }
    listening = !listening;
    setOrbState(listening ? 'listening' : 'idle');
    status.textContent = listening ? 'Höre zu...' : 'Pausiert. Klicke zum Fortsetzen.';
});

function setOrbState(state) { orb.className = state; }

function addTranscript(role, text) {
    const div = document.createElement('div');
    div.className = role;
    div.textContent = role === 'user' ? `Du: ${text}` : `Jarvis: ${text}`;
    transcript.appendChild(div);
    transcript.scrollTop = transcript.scrollHeight;
}

connect();
