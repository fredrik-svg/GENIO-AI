#!/usr/bin/env bash
set -Eeuo pipefail

# Install Piper TTS binary for Raspberry Pi / ARM64 Linux
# Downloads the pre-built binary from the official Piper releases

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect architecture
ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|arm64)
    PLATFORM="arm64"
    ;;
  x86_64|amd64)
    PLATFORM="amd64"
    ;;
  armv7l)
    PLATFORM="armv7"
    ;;
  *)
    echo "❌ Unsupported architecture: $ARCH"
    echo "   Piper supports: arm64 (Raspberry Pi 5), amd64, armv7"
    exit 1
    ;;
esac

# Piper release information
PIPER_VERSION="2023.11.14-2"
PIPER_RELEASE="${PIPER_VERSION}"
PIPER_ARCHIVE="piper_linux_${ARCH}.tar.gz"
PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_RELEASE}/${PIPER_ARCHIVE}"

echo ">>> Installing Piper TTS binary"
echo "    Version: ${PIPER_VERSION}"
echo "    Platform: ${PLATFORM} (${ARCH})"
echo "    URL: ${PIPER_URL}"
echo ""

# Create temporary directory
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

cd "$TMP_DIR"

# Download Piper
echo ">>> Downloading Piper binary..."
if ! curl -L -o "$PIPER_ARCHIVE" "$PIPER_URL"; then
    echo "❌ Failed to download Piper binary from ${PIPER_URL}"
    echo "   Please check your internet connection and try again."
    exit 1
fi

# Extract archive
echo ">>> Extracting archive..."
tar -xzf "$PIPER_ARCHIVE"

# Find the piper binary (it's in a subdirectory called 'piper')
PIPER_BIN=$(find . -name "piper" -type f -executable 2>/dev/null | head -1)
if [[ -z "$PIPER_BIN" ]]; then
    echo "❌ Could not find piper binary in archive"
    exit 1
fi

# Make it executable
chmod +x "$PIPER_BIN"

# Test that it works
echo ">>> Testing Piper binary..."
PIPER_VERSION_OUTPUT=$("$PIPER_BIN" --version 2>&1 || echo "unknown")
echo "    Version: $PIPER_VERSION_OUTPUT"

# Install to /usr/local/bin (requires sudo)
echo ">>> Installing to /usr/local/bin/piper (requires sudo)..."
if [[ -f /usr/local/bin/piper ]]; then
    echo "    Piper already exists at /usr/local/bin/piper"
    echo -n "    Replace it? [y/N] "
    read -r REPLY
    if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
        echo "    Skipping installation."
        exit 0
    fi
fi

if ! sudo cp "$PIPER_BIN" /usr/local/bin/piper; then
    echo "❌ Failed to install Piper to /usr/local/bin/piper"
    echo "   You may need to run this script with sudo privileges."
    exit 1
fi

# Verify installation
if [[ -f /usr/local/bin/piper ]]; then
    echo "✅ Piper installed successfully to /usr/local/bin/piper"
    echo ""
    echo "Test it with:"
    echo "  echo 'Hej, jag är Piper' | piper -m resources/piper/sv_SE-lisa-medium.onnx -f test.wav"
    echo ""
else
    echo "❌ Installation verification failed"
    exit 1
fi
