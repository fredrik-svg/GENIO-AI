// Simple client-side interactions for the web UI.
// - Text chat -> /api/chat
// - Record audio via MediaRecorder -> /api/transcribe
// - Synthesize text -> /api/synthesize (server-side espeak-ng)

const chatEl = document.getElementById("chat");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const speakBtn = document.getElementById("speakBtn");
const recordBtn = document.getElementById("recordBtn");

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + (role === "user" ? "user" : "assistant");
  div.innerText = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendText() {
  const message = textInput.value.trim();
  if (!message) return;
  appendMessage("user", message);
  textInput.value = "";
  try {
    const form = new FormData();
    form.append("message", message);
    const res = await fetch("/api/chat", { method: "POST", body: form });
    const data = await res.json();
    if (data.reply) {
      appendMessage("assistant", data.reply);
    } else if (data.error) {
      appendMessage("assistant", "Fel: " + data.error);
    }
  } catch (e) {
    appendMessage("assistant", "Nätverksfel: " + e.toString());
  }
}

async function synthesizeAndPlay(text) {
  try {
    const form = new FormData();
    form.append("text", text);
    const res = await fetch("/api/synthesize", { method: "POST", body: form });
    if (!res.ok) {
      const err = await res.json();
      appendMessage("assistant", "TTS fel: " + (err.error || res.status));
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play();
  } catch (e) {
    appendMessage("assistant", "TTS nätverksfel: " + e.toString());
  }
}

sendBtn.addEventListener("click", sendText);
textInput.addEventListener("keydown", (e) => { if (e.key === "Enter") sendText(); });

speakBtn.addEventListener("click", async () => {
  const text = prompt("Text att tala (svenska):");
  if (!text) return;
  appendMessage("user", "[TTS] " + text);
  appendMessage("assistant", "[Spelar upp...]");
  await synthesizeAndPlay(text);
});

let mediaRecorder = null;
let audioChunks = [];

recordBtn.addEventListener("click", async () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    // stop
    mediaRecorder.stop();
    recordBtn.classList.remove("recording");
    recordBtn.innerText = "Spela in";
    return;
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert("Din webbläsare stödjer inte mikrofonåtkomst.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      const fd = new FormData();
      fd.append("file", blob, "recording.webm");
      appendMessage("user", "[Inspelning skickad för transkription]");
      try {
        const res = await fetch("/api/transcribe", { method: "POST", body: fd });
        const data = await res.json();
        if (data.transcript) {
          appendMessage("assistant", "Transkription: " + data.transcript);
          // Optionally send the transcribed text to chat
          const auto = confirm("Skicka transkriptionen till chat?");
          if (auto) {
            textInput.value = data.transcript;
            sendText();
          }
        } else {
          appendMessage("assistant", "Transkript-fel: " + (data.error || "okänt"));
        }
      } catch (err) {
        appendMessage("assistant", "Transkript nätverksfel: " + err.toString());
      }
    };
    mediaRecorder.start();
    recordBtn.classList.add("recording");
    recordBtn.innerText = "Stoppa";
  } catch (err) {
    alert("Kunde inte öppna mikrofon: " + err.toString());
  }
});
