#!/usr/bin/env python3
"""
Health check script for Genio AI.
Validates configuration, dependencies, and system requirements.
"""
import os
import sys
from pathlib import Path
import yaml
import importlib

def check_file(path: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description} saknas: {path}")
        return False

def check_env_var(var_name: str, required: bool = True) -> bool:
    """Check if an environment variable is set.
    
    Note: This function only logs the environment variable NAME (e.g., "MQTT_PASSWORD"),
    never the actual value. The actual value is masked when present.
    """
    # Validate that var_name looks like an environment variable name, not a value
    # Environment variable names typically:
    # - Are uppercase or mixed case with underscores
    # - Contain underscores, letters, and numbers
    # - Do NOT contain spaces, special characters (except _), or look like base64/passwords
    if var_name:
        has_lowercase = any(c.islower() for c in var_name)
        has_uppercase = any(c.isupper() for c in var_name)
        has_underscore = '_' in var_name
        has_suspicious_chars = any(char in var_name for char in [' ', '=', '+', '/', '{', '}', '[', ']'])
        
        is_suspicious = (
            len(var_name) > 50 or  # Suspiciously long
            has_suspicious_chars or  # Contains base64 or other suspicious chars
            (has_lowercase and has_uppercase and not has_underscore)  # Mixed case without underscores (like "Genio2025")
        )
        
        if is_suspicious:
            print(f"⚠️  VARNING: '{var_name[:20]}...' ser inte ut som ett miljövariabelnamn!")
            print(f"    Miljövariabler ska vara namn som 'PORCUPINE_ACCESS_KEY', inte faktiska lösenord.")
            print(f"    Kontrollera din config.yaml - använd miljövariabelnamn, inte värden.")
            return False
    
    value = os.environ.get(var_name)
    if value:
        # Only show that variable is set, never log actual value
        masked_value = '*' * min(len(value), 8)
        # Safe: Only printing the variable name and masked value, not actual sensitive data
        print(f"✅ Miljövariabel {var_name}: {masked_value}")
        return True
    else:
        if required:
            # Safe: Only printing the variable name when missing, no sensitive data
            print(f"❌ Miljövariabel {var_name} saknas")
        else:
            # Safe: Only printing the variable name, no sensitive data
            print(f"⚠️  Miljövariabel {var_name} inte satt (valfri)")
        return not required

def check_config(cfg_path: str) -> dict:
    """Load and validate configuration."""
    print(f"\n📋 Kontrollerar konfiguration: {cfg_path}")
    
    if not Path(cfg_path).exists():
        print(f"❌ Konfigurationsfil saknas: {cfg_path}")
        return None
    
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        print(f"✅ Konfigurationsfil laddad")
    except Exception as e:
        print(f"❌ Kunde inte läsa konfiguration: {e}")
        return None
    
    # Check required sections
    required_sections = ["audio", "wakeword", "stt", "tts", "mqtt"]
    all_ok = True
    for section in required_sections:
        if section in cfg:
            print(f"✅ Sektion '{section}' finns")
        else:
            print(f"❌ Sektion '{section}' saknas")
            all_ok = False
    
    return cfg if all_ok else None

def check_dependencies():
    """Check Python dependencies."""
    print("\n📦 Kontrollerar Python-beroenden:")
    
    required_modules = [
        "numpy",
        "yaml",
        "sounddevice",
        "webrtcvad",
        "pvporcupine",
        "paho.mqtt.client",
        "faster_whisper",
    ]
    
    all_ok = True
    for module_name in required_modules:
        try:
            importlib.import_module(module_name)
            print(f"✅ {module_name}")
        except ImportError:
            print(f"❌ {module_name} saknas")
            all_ok = False
    
    return all_ok

def main():
    print("=" * 60)
    print("Genio AI - Hälsokontroll")
    print("=" * 60)
    
    all_checks_ok = True
    
    # Check configuration file
    cfg_path = os.environ.get("GENIO_CONFIG", "config.yaml")
    cfg = check_config(cfg_path)
    if not cfg:
        all_checks_ok = False
    
    # Check Python dependencies
    if not check_dependencies():
        all_checks_ok = False
    
    # Check environment variables
    if cfg:
        print("\n🔑 Kontrollerar miljövariabler:")
        wakeword_cfg = cfg.get("wakeword", {})
        mqtt_cfg = cfg.get("mqtt", {})
        
        if not check_env_var(wakeword_cfg.get("access_key_env", "PORCUPINE_ACCESS_KEY")):
            all_checks_ok = False
        if not check_env_var(mqtt_cfg.get("username_env", "MQTT_USERNAME")):
            all_checks_ok = False
        if not check_env_var(mqtt_cfg.get("password_env", "MQTT_PASSWORD")):
            all_checks_ok = False
    
    # Check model files
    if cfg:
        print("\n📁 Kontrollerar modellfiler:")
        
        # Wakeword
        wakeword_cfg = cfg.get("wakeword", {})
        if not check_file(wakeword_cfg.get("keyword_path", ""), "Wakeword (.ppn)"):
            all_checks_ok = False
        
        model_path = wakeword_cfg.get("model_path")
        if model_path:
            if Path(model_path).exists():
                print(f"✅ Porcupine språkmodell (.pv): {model_path}")
            else:
                print(f"⚠️  Porcupine språkmodell (.pv) saknas: {model_path}")
                print(f"    Inbyggd standardmodell kommer användas istället")
        else:
            print(f"ℹ️  Porcupine språkmodell inte konfigurerad, använder inbyggd standardmodell")
        
        # STT
        stt_cfg = cfg.get("stt", {})
        model_dir = stt_cfg.get("model_dir", "")
        if not check_file(model_dir, "Whisper-modell (katalog)"):
            all_checks_ok = False
        
        # TTS
        tts_cfg = cfg.get("tts", {})
        if not check_file(tts_cfg.get("piper_bin", ""), "Piper-binär"):
            all_checks_ok = False
        if not check_file(tts_cfg.get("model_path", ""), "Piper-modell (.onnx)"):
            all_checks_ok = False
    
    # Print summary
    print("\n" + "=" * 60)
    if all_checks_ok:
        print("✅ Alla kontroller godkända! Genio AI är redo att köras.")
        print("=" * 60)
        return 0
    else:
        print("❌ Vissa kontroller misslyckades. Se ovan för detaljer.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
