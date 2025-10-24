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
from typing import Optional, Dict, Any

import sounddevice as sd
import webrtcvad
import pvporcupine
from paho.mqtt import client as mqtt
from faster_whisper import WhisperModel
from datetime import datetime, timezone
from pathlib import Path
from subprocess import Popen, PIPE, CalledProcessError, run

def load_config(path: str) -> dict:
    """Load and validate configuration from YAML file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        
        # Validate required sections
        required_sections = ["audio", "wakeword", "stt", "tts", "mqtt"]
        for section in required_sections:
            if section not in cfg:
                raise ValueError(f"Missing required config section: {section}")
        
        # Validate MQTT configuration
        mqtt_cfg = cfg["mqtt"]
        if not mqtt_cfg.get("host"):
            raise ValueError("MQTT host is required")
        if not mqtt_cfg.get("request_topic"):
            raise ValueError("MQTT request_topic is required")
        if not mqtt_cfg.get("base_response_topic"):
            raise ValueError("MQTT base_response_topic is required")
        
        return cfg
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML configuration: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {path}")

def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class MqttClient:
    def __init__(self, cfg):
        self.cfg = cfg
        
        # Get clean_session parameter from config (default to True for MQTTv311)
        clean_session = bool(cfg.get("clean_session", True))
        
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=cfg["client_id"],
            clean_session=clean_session,
            protocol=mqtt.MQTTv311,
        )
        self.client.enable_logger(logging.getLogger("paho-mqtt"))

        # Get credentials from environment variables
        username = os.environ.get(cfg["username_env"], "").strip()
        password = os.environ.get(cfg["password_env"], "").strip()
        
        # Only set credentials if both username and password are provided
        if username and password:
            self.client.username_pw_set(username, password)
            logging.debug(f"MQTT credentials set for user: {username}")
        elif username or password:
            # Warn if only one credential is provided
            logging.warning(f"MQTT credentials incomplete: username={'set' if username else 'missing'}, password={'set' if password else 'missing'}")
        else:
            logging.info("MQTT ansluter utan autentisering")

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
        self._reconnect_lock = threading.Lock()
        self._connection_attempts = 0
        self._max_reconnect_attempts = 5

    def connect(self):
        """Connect to MQTT broker with retry logic."""
        host = self.cfg["host"]
        port = int(self.cfg.get("port", 8883))
        keepalive = int(self.cfg.get("keepalive", 60))
        
        logging.info(f"Ansluter till MQTT {host}:{port} (TLS)")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.client.connect(host, port, keepalive=keepalive)
                self.client.loop_start()
                if not self._connected_evt.wait(timeout=10):
                    if attempt < max_attempts - 1:
                        logging.warning(f"MQTT: anslutning timeout, försöker igen ({attempt + 1}/{max_attempts})...")
                        time.sleep(2)
                        continue
                    raise RuntimeError("MQTT: anslutning misslyckades (timeout)")
                
                base = self.cfg["base_response_topic"].rstrip("/")
                topic = f"{base}/#"
                self.client.subscribe(topic, qos=self.cfg.get("qos", 1))
                logging.info(f"Prenumererar på: {topic}")
                self._connection_attempts = 0
                return
            except Exception as e:
                if attempt < max_attempts - 1:
                    logging.warning(f"MQTT anslutningsfel: {e}, försöker igen ({attempt + 1}/{max_attempts})...")
                    time.sleep(2)
                else:
                    raise RuntimeError(f"MQTT: anslutning misslyckades efter {max_attempts} försök: {e}")

    def close(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logging.info("MQTT-anslutning stängd.")
        except Exception as e:
            logging.warning(f"Fel vid stängning av MQTT: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logging.info("MQTT ansluten.")
            self._connected_evt.set()
            self._connection_attempts = 0
        else:
            # Provide more helpful error messages based on reason code
            error_messages = {
                1: "Protocol version not supported",
                2: "Client identifier rejected",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized - check credentials",
            }
            error_msg = error_messages.get(reason_code, f"Unknown error (code {reason_code})")
            logging.error(f"MQTT anslutningsfel: reason_code={reason_code} ({error_msg})")
            
            # Additional troubleshooting hints for common errors
            if reason_code == 4 or reason_code == 5:
                logging.error(f"Kontrollera att miljövariabler {self.cfg['username_env']} och {self.cfg['password_env']} är korrekt satta")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        logging.warning(f"MQTT frånkopplad: reason_code={reason_code}")
        self._connected_evt.clear()
        
        # Automatic reconnection for unexpected disconnects
        if reason_code != 0:
            with self._reconnect_lock:
                self._connection_attempts += 1
                if self._connection_attempts <= self._max_reconnect_attempts:
                    logging.info(f"Försöker återansluta till MQTT (försök {self._connection_attempts}/{self._max_reconnect_attempts})...")
                    time.sleep(2 ** self._connection_attempts)  # Exponential backoff
                else:
                    logging.error("Max antal återanslutningsförsök nått. Ger upp.")

    def _on_message(self, client, userdata, message):
        try:
            payload = message.payload.decode("utf-8", errors="ignore")
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            logging.error(f"Kunde inte avkoda JSON från MQTT-meddelande: {e}")
            return
        except Exception as e:
            logging.exception(f"Oväntat fel vid avkodning av MQTT-meddelande: {e}")
            return

        corr_id = data.get("corr_id") or data.get("correlation_id")
        if not corr_id:
            logging.warning("MQTT-svar saknar corr_id")
            return

        q = self.pending.get(corr_id)
        if q:
            q.put(data)

    def request_reply(self, text: str, lang: str, qos: int = 1, timeout: int = 15) -> Optional[Dict[str, Any]]:
        """Send request to n8n workflow and wait for response."""
        if not self._connected_evt.is_set():
            logging.error("MQTT inte ansluten, kan inte skicka request")
            return None
        
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
        
        try:
            req_topic = self.cfg["request_topic"]
            result = self.client.publish(req_topic, json.dumps(payload), qos=qos, retain=False)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logging.error(f"MQTT publish misslyckades: rc={result.rc}")
                return None
            
            logging.info(f"Skickade MQTT-request -> {req_topic} (corr_id={corr_id})")

            response = q.get(timeout=timeout)
            logging.info("MQTT-svar mottaget från n8n")
            return response
        except queue.Empty:
            logging.error("Timeout: inget svar från n8n")
            return None
        except Exception as e:
            logging.error(f"Fel vid MQTT request: {e}")
            return None
        finally:
            self.pending.pop(corr_id, None)

class Recorder:
    def __init__(self, audio_cfg, wake_cfg):
        self.audio_cfg = audio_cfg
        self.wake_cfg = wake_cfg

        access_key = os.environ.get(wake_cfg["access_key_env"])
        if not access_key:
            raise RuntimeError(f"{wake_cfg['access_key_env']} saknas i miljön")

        keyword_path = wake_cfg["keyword_path"]
        model_path = wake_cfg.get("model_path", None)
        sensitivity = float(wake_cfg.get("sensitivity", 0.5))

        if not Path(keyword_path).exists():
            raise FileNotFoundError(f"Saknar wakeword-fil: {keyword_path}")
        
        # Make model_path optional: skip if None, empty, or file doesn't exist
        # Porcupine will use its built-in default model when model_path is not provided
        use_model_path = False
        if model_path:
            model_path = model_path.strip()
            if model_path and Path(model_path).exists():
                use_model_path = True
                logging.info(f"Använder Porcupine språkmodell: {model_path}")
            else:
                if model_path:
                    logging.warning(f"Porcupine språkmodell saknas ({model_path}), använder inbyggd standardmodell")
                else:
                    logging.info("Använder inbyggd Porcupine standardmodell")
        else:
            logging.info("Använder inbyggd Porcupine standardmodell")

        try:
            kwargs = dict(
                access_key=access_key,
                keyword_paths=[keyword_path],
                sensitivities=[sensitivity],
            )
            if use_model_path:
                kwargs["model_path"] = model_path

            self.porcupine = pvporcupine.create(**kwargs)
            logging.info("Porcupine wakeword-detektor initierad")
        except Exception as e:
            raise RuntimeError(f"Kunde inte initiera Porcupine: {e}")

        self.sample_rate = int(audio_cfg.get("sample_rate", 16000))
        self.input_device = audio_cfg.get("input_device", None)

        try:
            self.vad = webrtcvad.Vad(int(audio_cfg.get("vad_aggressiveness", 2)))
        except Exception as e:
            raise RuntimeError(f"Kunde inte initiera WebRTC VAD: {e}")
        
        self.frame_ms = 30
        self.silence_end_ms = int(audio_cfg.get("silence_end_ms", 800))
        self.max_utt_sec = int(audio_cfg.get("max_utterance_sec", 12))

        self.pv_frame_len = self.porcupine.frame_length
        self.pv_sample_rate = self.porcupine.sample_rate

    def listen_for_wakeword(self, stop_evt: threading.Event):
        """Listen for wakeword using Porcupine."""
        logging.info("Lyssnar efter väckningsfras...")
        try:
            with sd.RawInputStream(samplerate=self.pv_sample_rate,
                                   blocksize=self.pv_frame_len,
                                   dtype="int16",
                                   channels=1,
                                   device=self.input_device) as stream:
                while not stop_evt.is_set():
                    try:
                        audio = stream.read(self.pv_frame_len)[0]
                        if not audio:
                            continue
                        pcm = np.frombuffer(audio, dtype=np.int16)
                        result = self.porcupine.process(pcm)
                        if result >= 0:
                            logging.info("Väckningsfras detekterad.")
                            return
                    except Exception as e:
                        logging.error(f"Fel vid läsning av ljudström för wakeword: {e}")
                        time.sleep(0.1)
        except Exception as e:
            logging.error(f"Kunde inte öppna ljudinmatning för wakeword: {e}")
            raise

    def record_utterance(self) -> bytes:
        """Record user utterance after wakeword detection."""
        logging.info("Börjar inspelning...")
        frame_size = int(self.sample_rate * self.frame_ms / 1000)
        blocksize = frame_size

        def is_speech(frame_bytes):
            try:
                return self.vad.is_speech(frame_bytes, self.sample_rate)
            except Exception as e:
                logging.debug(f"VAD-fel: {e}")
                return False

        try:
            stream = sd.RawInputStream(samplerate=self.sample_rate,
                                       blocksize=blocksize,
                                       dtype="int16",
                                       channels=1,
                                       device=self.input_device)
            stream.start()
        except Exception as e:
            logging.error(f"Kunde inte öppna ljudinmatning för inspelning: {e}")
            raise

        frames = []
        start_time = time.time()
        last_voice_time = None
        try:
            while True:
                try:
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
                except Exception as e:
                    logging.error(f"Fel vid läsning av ljuddata: {e}")
                    break
        finally:
            stream.stop()
            stream.close()

        pcm = b"".join(frames)
        logging.info(f"Inspelning klar: {len(pcm)} bytes, {len(pcm) / (self.sample_rate * 2):.2f} sekunder")
        return pcm

class LocalSTT:
    def __init__(self, stt_cfg, sample_rate: int):
        model_dir = stt_cfg["model_dir"]
        compute_type = stt_cfg.get("compute_type", "int8")
        self.language = stt_cfg.get("language", "sv")
        self.beam_size = int(stt_cfg.get("beam_size", 5))
        self.sample_rate = sample_rate

        if not Path(model_dir).exists():
            raise FileNotFoundError(f"Whisper-modell saknas: {model_dir}")

        logging.info(f"Laddar Faster-Whisper från: {model_dir} (compute_type={compute_type})")
        try:
            self.model = WhisperModel(model_dir, device="cpu", compute_type=compute_type)
            logging.info("Faster-Whisper modell laddad")
        except Exception as e:
            raise RuntimeError(f"Kunde inte ladda Whisper-modell: {e}")

    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        """Transcribe PCM audio data to text."""
        try:
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
            logging.info(f"STT: '{text}' (språk: {info.language}, sannolikhet: {info.language_probability:.2f})")
            return text
        except Exception as e:
            logging.error(f"Fel vid transkribering: {e}")
            return ""

class PiperTTS:
    def __init__(self, tts_cfg):
        self.piper_bin = tts_cfg["piper_bin"]
        self.model_path = tts_cfg["model_path"]
        self.keep_wav = bool(tts_cfg.get("keep_wav", False))

        if not Path(self.piper_bin).exists():
            raise FileNotFoundError(f"Hittar inte piper-binär: {self.piper_bin}")
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"Hittar inte piper-modellen: {self.model_path}")
        
        logging.info("Piper TTS initierad")

    def speak(self, text: str):
        """Convert text to speech and play it."""
        if not text:
            logging.warning("Tom text skickad till TTS, hoppar över")
            return
        
        # Sanitize text to prevent command injection
        text = text.strip()
        if not text:
            return
            
        wav_path = f"/tmp/genio_tts_{uuid.uuid4().hex}.wav"
        try:
            logging.info(f"TTS: Genererar tal för '{text[:50]}...'")
            p = Popen([self.piper_bin, "-m", self.model_path, "-f", wav_path], stdin=PIPE)
            p.communicate(input=text.encode("utf-8"), timeout=30)
            
            if p.returncode != 0:
                logging.error(f"Piper avslutades med felkod {p.returncode}")
                return
            
            if not Path(wav_path).exists():
                logging.error("Piper genererade ingen WAV-fil")
                return
                
            logging.info("Spelar upp tal...")
            result = run(["aplay", "-q", wav_path], capture_output=True, timeout=30)
            if result.returncode != 0:
                logging.error(f"aplay fel: {result.stderr.decode('utf-8', errors='ignore')}")
        except CalledProcessError as e:
            logging.error(f"Fel vid uppspelning med aplay: {e}")
        except TimeoutError:
            logging.error("TTS timeout")
        except Exception as e:
            logging.error(f"Oväntat TTS-fel: {e}")
        finally:
            if not self.keep_wav:
                try:
                    Path(wav_path).unlink(missing_ok=True)
                except Exception as e:
                    logging.debug(f"Kunde inte ta bort temporär WAV-fil: {e}")

class GenioAIApp:
    def __init__(self, cfg):
        self.cfg = cfg
        self.lang = cfg.get("stt", {}).get("language", "sv")

        try:
            self.rec = Recorder(cfg["audio"], cfg["wakeword"])
            self.stt = LocalSTT(cfg["stt"], self.rec.sample_rate)
            self.tts = PiperTTS(cfg["tts"])
            self.mqtt = MqttClient(cfg["mqtt"])
        except Exception as e:
            logging.error(f"Fel vid initialisering av komponenter: {e}")
            raise

        self.stop_evt = threading.Event()
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._sig_handler)
        signal.signal(signal.SIGTERM, self._sig_handler)

    def _sig_handler(self, signum, frame):
        if not self._shutdown_requested:
            self._shutdown_requested = True
            sig_name = signal.Signals(signum).name
            logging.info(f"Mottog signal {sig_name}, avslutar graciöst...")
            self.stop_evt.set()

    def run(self):
        """Main application loop."""
        logging.info("Genio AI startar...")
        
        try:
            self.mqtt.connect()
        except Exception as e:
            logging.error(f"Kunde inte ansluta till MQTT: {e}")
            return
        
        logging.info("Genio AI redo. Lyssnar efter väckningsfras.")
        
        while not self.stop_evt.is_set():
            try:
                # Step 1: Listen for wakeword
                self.rec.listen_for_wakeword(self.stop_evt)
                if self.stop_evt.is_set():
                    break

                # Step 2: Record utterance and convert to text
                pcm = self.rec.record_utterance()
                if not pcm or len(pcm) < self.rec.sample_rate * 2 * 0.2:
                    logging.info("Tomt/kort yttrande. Återgår till lyssning.")
                    continue

                # Transkribera direkt från PCM-array (ingen fil-avkodning; undviker PyAV-behov)
                text = self.stt.transcribe_pcm(pcm)

                if not text:
                    self.tts.speak("Jag hörde inget. Försök igen.")
                    continue

                # Step 3: Send to n8n via MQTT and wait for response
                resp = self.mqtt.request_reply(
                    text=text,
                    lang=self.lang,
                    qos=self.cfg["mqtt"].get("qos", 1),
                    timeout=int(self.cfg["mqtt"].get("timeout_sec", 15))
                )

                # Step 4: Speak the response
                if resp is None:
                    self.tts.speak("Inget svar från arbetsflödet. Försök igen senare.")
                else:
                    reply_text = resp.get("reply") or resp.get("text") or ""
                    if not reply_text:
                        reply_text = "Jag fick ett tomt svar."
                    self.tts.speak(reply_text)

                # Step 5: Ready for next wakeword
                logging.info("Redo för ny väckningsfras.")
                
            except KeyboardInterrupt:
                logging.info("Avbruten av användaren")
                break
            except Exception as e:
                logging.exception(f"Oväntat fel i huvudloopen: {e}")
                # Wait before retrying to avoid rapid error loops
                time.sleep(2)

        logging.info("Stänger ner...")
        self.mqtt.close()
        logging.info("Genio AI avslutad.")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    cfg_path = os.environ.get("GENIO_CONFIG", "config.yaml")
    
    try:
        if not Path(cfg_path).exists():
            logging.error(f"Saknar konfig: {cfg_path}")
            print(f"Konfig-fil saknas: {cfg_path}", file=sys.stderr)
            print(f"Kopiera config.example.yaml till {cfg_path} och redigera den.", file=sys.stderr)
            sys.exit(1)

        cfg = load_config(cfg_path)
        
        # Validate environment variables (only check names, never log values)
        # Note: We only log environment variable NAMES (e.g., "MQTT_PASSWORD"),
        # never the actual sensitive values
        required_env_vars = [
            cfg["wakeword"]["access_key_env"],
            cfg["mqtt"]["username_env"],
            cfg["mqtt"]["password_env"]
        ]
        
        missing_vars = []
        empty_vars = []
        for env_var_name in required_env_vars:
            value = os.environ.get(env_var_name)
            if value is None:
                missing_vars.append(env_var_name)
            elif not value.strip():
                empty_vars.append(env_var_name)
        
        if missing_vars or empty_vars:
            all_invalid = missing_vars + empty_vars
            # Safe: Log only variable names, not values
            logging.error(f"Saknade eller tomma miljövariabler: {', '.join(all_invalid)}")
            print(f"\n❌ Följande miljövariabler måste sättas korrekt:", file=sys.stderr)
            for env_var_name in all_invalid:
                # Safe: Only printing variable name, no sensitive data
                if env_var_name in missing_vars:
                    print(f"  - {env_var_name} (inte satt i miljön)", file=sys.stderr)
                else:
                    print(f"  - {env_var_name} (tom eller endast whitespace)", file=sys.stderr)
            
            print(f"\n💡 Felsökning:", file=sys.stderr)
            print(f"  1. Kontrollera att du stavat variabelnamnen rätt", file=sys.stderr)
            # Safe: At least one list is non-empty due to condition on line 570
            first_var = missing_vars[0] if missing_vars else empty_vars[0]
            print(f"  2. Kör 'echo ${first_var}' för att verifiera värdet", file=sys.stderr)
            print(f"  3. Exportera variabler i SAMMA terminal där du kör scriptet", file=sys.stderr)
            
            print(f"\n📝 Exempel på korrekt användning:", file=sys.stderr)
            print(f"  export PORCUPINE_ACCESS_KEY=\"your_key_here\"", file=sys.stderr)
            print(f"  export MQTT_USERNAME=\"your_username\"", file=sys.stderr)
            print(f"  export MQTT_PASSWORD=\"your_password\"", file=sys.stderr)
            print(f"  python3 genio_ai.py", file=sys.stderr)
            
            print(f"\n⚙️  Din konfigurationsfil ({cfg_path}) förväntar sig:", file=sys.stderr)
            for env_var_name in required_env_vars:
                print(f"  - {env_var_name}", file=sys.stderr)
            
            sys.exit(1)
        
        app = GenioAIApp(cfg)
        app.run()
        
    except FileNotFoundError as e:
        logging.error(f"Fil saknas: {e}")
        sys.exit(1)
    except ValueError as e:
        logging.error(f"Konfigurationsfel: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logging.error(f"Runtime-fel: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Avbruten av användaren")
        sys.exit(0)
    except Exception as e:
        logging.exception(f"Kritiskt fel: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
