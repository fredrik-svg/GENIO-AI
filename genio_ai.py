\
import os
import ssl
import sys
import time
import json
import uuid
import queue
import signal
import logging
import threading
import numpy as np
import yaml

import sounddevice as sd
import webrtcvad
import pvporcupine
from paho.mqtt import client as mqtt
from faster_whisper import WhisperModel
from datetime import datetime, timezone
from pathlib import Path
from subprocess import Popen, PIPE, CalledProcessError, run

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class MqttClient:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = mqtt.Client(
            client_id=cfg["client_id"],
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        )
        self.client.enable_logger(logging.getLogger("paho-mqtt"))

        username = os.environ.get(cfg["username_env"], "")
        password = os.environ.get(cfg["password_env"], "")
        if username:
            self.client.username_pw_set(username, password)

        if cfg.get("ca_certs"):
            self.client.tls_set(
                ca_certs=cfg["ca_certs"],
                certfile=None,
                keyfile=None,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
                ciphers=None,
            )
        else:
            self.client.tls_set(
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
            )
        self.client.tls_insecure_set(bool(cfg.get("tls_insecure", False)))

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self.pending = {}
        self._connected_evt = threading.Event()

    def connect(self):
        host = self.cfg["host"]
        port = int(self.cfg.get("port", 8883))
        keepalive = int(self.cfg.get("keepalive", 60))
        logging.info(f"Ansluter till MQTT {host}:{port} (TLS)")
        self.client.connect(host, port, keepalive=keepalive)
        self.client.loop_start()
        if not self._connected_evt.wait(timeout=10):
            raise RuntimeError("MQTT: anslutning misslyckades (timeout)")

        base = self.cfg["base_response_topic"].rstrip("/")
        topic = f"{base}/#"
        self.client.subscribe(topic, qos=self.cfg.get("qos", 1))
        logging.info(f"Prenumererar på: {topic}")

    def close(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("MQTT ansluten.")
            self._connected_evt.set()
        else:
            logging.error(f"MQTT anslutningsfel: rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        logging.warning(f"MQTT frånkopplad: rc={rc}")
        self._connected_evt.clear()

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="ignore")
            data = json.loads(payload)
        except Exception:
            logging.exception("Kunde inte avkoda inkommande MQTT‑meddelande")
            return

        corr_id = data.get("corr_id") or data.get("correlation_id")
        if not corr_id:
            logging.warning("MQTT‑svar saknar corr_id")
            return

        q = self.pending.get(corr_id)
        if q:
            q.put(data)

    def request_reply(self, text: str, lang: str, qos: int = 1, timeout: int = 15):
        corr_id = str(uuid.uuid4())
        base = self.cfg["base_response_topic"].rstrip("/")
        reply_topic = f"{base}/{corr_id}"

        q = queue.Queue()
        self.pending[corr_id] = q

        payload = {
            "text": text,
            "lang": lang,
            "timestamp": utc_iso(),
            "corr_id": corr_id,
            "reply_topic": reply_topic,
            "source": "genio-ai-rpi5"
        }
        req_topic = self.cfg["request_topic"]
        result = self.client.publish(req_topic, json.dumps(payload), qos=qos, retain=False)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logging.error(f"MQTT publish misslyckades: rc={result.rc}")
        else:
            logging.info(f"Skickade MQTT‑request -> {req_topic} (corr_id={corr_id})")

        try:
            response = q.get(timeout=timeout)
            logging.info("MQTT‑svar mottaget från n8n")
            return response
        except queue.Empty:
            logging.error("Timeout: inget svar från n8n")
            return None
        finally:
            self.pending.pop(corr_id, None)

class Recorder:
    def __init__(self, audio_cfg, wake_cfg):
        self.audio_cfg = audio_cfg
        self.wake_cfg = wake_cfg

        access_key = os.environ.get(wake_cfg["access_key_env"])
        if not access_key:
            raise RuntimeError("PORCUPINE_ACCESS_KEY saknas i miljön")

        keyword_path = wake_cfg["keyword_path"]
        model_path = wake_cfg.get("model_path", None)
        sensitivity = float(wake_cfg.get("sensitivity", 0.5))

        if not Path(keyword_path).exists():
            raise FileNotFoundError(f"Saknar wakeword‑fil: {keyword_path}")
        if model_path is not None and not Path(model_path).exists():
            raise FileNotFoundError(f"Saknar Porcupine språkmodell (.pv): {model_path}")

        kwargs = dict(
            access_key=access_key,
            keyword_paths=[keyword_path],
            sensitivities=[sensitivity],
        )
        if model_path:
            kwargs["model_path"] = model_path

        self.porcupine = pvporcupine.create(**kwargs)

        self.sample_rate = int(audio_cfg.get("sample_rate", 16000))
        self.input_device = audio_cfg.get("input_device", None)

        self.vad = webrtcvad.Vad(int(audio_cfg.get("vad_aggressiveness", 2)))
        self.frame_ms = 30
        self.silence_end_ms = int(audio_cfg.get("silence_end_ms", 800))
        self.max_utt_sec = int(audio_cfg.get("max_utterance_sec", 12))

        self.pv_frame_len = self.porcupine.frame_length
        self.pv_sample_rate = self.porcupine.sample_rate

    def listen_for_wakeword(self, stop_evt: threading.Event):
        logging.info("Lyssnar efter väckningsfras...")
        with sd.RawInputStream(samplerate=self.pv_sample_rate,
                               blocksize=self.pv_frame_len,
                               dtype="int16",
                               channels=1,
                               device=self.input_device) as stream:
            while not stop_evt.is_set():
                audio = stream.read(self.pv_frame_len)[0]
                if not audio:
                    continue
                pcm = np.frombuffer(audio, dtype=np.int16)
                result = self.porcupine.process(pcm)
                if result >= 0:
                    logging.info("Väckningsfras detekterad.")
                    return

    def record_utterance(self) -> bytes:
        logging.info("Börjar inspelning...")
        frame_size = int(self.sample_rate * self.frame_ms / 1000)
        blocksize = frame_size

        def is_speech(frame_bytes):
            return self.vad.is_speech(frame_bytes, self.sample_rate)

        stream = sd.RawInputStream(samplerate=self.sample_rate,
                                   blocksize=blocksize,
                                   dtype="int16",
                                   channels=1,
                                   device=self.input_device)
        stream.start()

        frames = []
        start_time = time.time()
        last_voice_time = None
        try:
            while True:
                block, _ = stream.read(blocksize)
                if not block:
                    continue
                frames.append(block)
                if is_speech(block):
                    last_voice_time = time.time()

                elapsed = time.time() - start_time
                if elapsed > self.max_utt_sec:
                    logging.info("Max längd uppnådd, stoppar inspelning.")
                    break

                if last_voice_time is not None:
                    silence_ms = (time.time() - last_voice_time) * 1000.0
                    if silence_ms >= self.silence_end_ms:
                        logging.info("Tystnad detekterad, stoppar inspelning.")
                        break
        finally:
            stream.stop()
            stream.close()

        pcm = b"".join(frames)
        return pcm

class LocalSTT:
    def __init__(self, stt_cfg, sample_rate: int):
        model_dir = stt_cfg["model_dir"]
        compute_type = stt_cfg.get("compute_type", "int8")
        self.language = stt_cfg.get("language", "sv")
        self.beam_size = int(stt_cfg.get("beam_size", 5))
        self.sample_rate = sample_rate

        logging.info(f"Laddar Faster‑Whisper från: {model_dir} (compute_type={compute_type})")
        self.model = WhisperModel(model_dir, device="cpu", compute_type=compute_type)

    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        # Konvertera PCM int16 -> float32 [-1, 1] @ 16 kHz
        pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, info = self.model.transcribe(
            pcm,
            beam_size=self.beam_size,
            language=self.language,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = "".join([seg.text for seg in segments]).strip()
        logging.info(f"STT: '{text}'")
        return text

class PiperTTS:
    def __init__(self, tts_cfg):
        self.piper_bin = tts_cfg["piper_bin"]
        self.model_path = tts_cfg["model_path"]
        self.keep_wav = bool(tts_cfg.get("keep_wav", False))

        if not Path(self.piper_bin).exists():
            raise FileNotFoundError(f"Hittar inte piper-binär: {self.piper_bin}")
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"Hittar inte piper‑modellen: {self.model_path}")

    def speak(self, text: str):
        if not text:
            return
        wav_path = f"/tmp/genio_tts_{uuid.uuid4().hex}.wav"
        try:
            p = Popen([self.piper_bin, "-m", self.model_path, "-f", wav_path], stdin=PIPE)
            p.communicate(input=text.encode("utf-8"))
            run(["aplay", wav_path], check=True)
        except CalledProcessError:
            logging.exception("Fel vid uppspelning med aplay")
        finally:
            if not self.keep_wav:
                try:
                    Path(wav_path).unlink(missing_ok=True)
                except Exception:
                    pass

class GenioAIApp:
    def __init__(self, cfg):
        self.cfg = cfg
        self.lang = cfg.get("stt", {}).get("language", "sv")

        self.rec = Recorder(cfg["audio"], cfg["wakeword"])
        self.stt = LocalSTT(cfg["stt"], self.rec.sample_rate)
        self.tts = PiperTTS(cfg["tts"])
        self.mqtt = MqttClient(cfg["mqtt"])

        self.stop_evt = threading.Event()
        signal.signal(signal.SIGINT, self._sig_handler)
        signal.signal(signal.SIGTERM, self._sig_handler)

    def _sig_handler(self, signum, frame):
        logging.info("Avslutar...")
        self.stop_evt.set()

    def run(self):
        self.mqtt.connect()
        while not self.stop_evt.is_set():
            try:
                self.rec.listen_for_wakeword(self.stop_evt)
                if self.stop_evt.is_set():
                    break

                pcm = self.rec.record_utterance()
                if not pcm or len(pcm) < self.rec.sample_rate * 2 * 0.2:
                    logging.info("Tomt/kort yttrande. Återgår till lyssning.")
                    continue

                # Transkribera direkt från PCM-array (ingen fil-avkodning; undviker PyAV-behov)
                text = self.stt.transcribe_pcm(pcm)

                if not text:
                    self.tts.speak("Jag hörde inget. Försök igen.")
                    continue

                resp = self.mqtt.request_reply(
                    text=text,
                    lang=self.lang,
                    qos=self.cfg["mqtt"].get("qos", 1),
                    timeout=int(self.cfg["mqtt"].get("timeout_sec", 15))
                )

                if resp is None:
                    self.tts.speak("Inget svar från arbetsflödet. Försök igen senare.")
                else:
                    reply_text = resp.get("reply") or resp.get("text") or ""
                    if not reply_text:
                        reply_text = "Jag fick ett tomt svar."
                    self.tts.speak(reply_text)

                logging.info("Redo för ny väckningsfras.")
            except Exception:
                logging.exception("Oväntat fel i huvudloopen")
                time.sleep(1)

        self.mqtt.close()

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg_path = os.environ.get("GENIO_CONFIG", "config.yaml")
    if not Path(cfg_path).exists():
        print(f"Saknar konfig: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(cfg_path)
    app = GenioAIApp(cfg)
    app.run()

if __name__ == "__main__":
    main()
