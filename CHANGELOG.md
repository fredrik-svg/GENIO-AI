# CHANGELOG

## [Unreleased]

### Added
- Comprehensive error handling throughout all components
- Configuration validation at startup with detailed error messages
- Health check script (`scripts/health_check.py`) for system validation
- MQTT automatic reconnection with exponential backoff
- Better logging with timestamps and formatted output
- Graceful shutdown handling for SIGINT/SIGTERM signals
- Input validation and sanitization for TTS
- Timeout handling for external processes (Piper TTS)
- `.gitignore` file for better version control
- Type hints for better code clarity
- Detailed README with comprehensive documentation
- Environment variable validation at startup

### Changed
- Improved MQTT client with retry logic and connection state management
- Enhanced Recorder class with better error handling for audio streams
- Better STT transcription with language probability logging
- Enhanced TTS with timeout protection and error recovery
- Main application loop with structured error handling
- Log format now includes date, time, level, and component name

### Fixed
- MQTT connection timeout issues with retry mechanism
- Missing error handling in audio stream operations
- Potential command injection in TTS text processing
- Silent failures in component initialization
- Missing validation for required configuration sections

### Security
- Added input sanitization for text-to-speech to prevent command injection
- Environment variable validation before runtime
- Better error messages without exposing sensitive information
- Timeouts on external process calls to prevent hanging

## Previous Versions

See git history for previous changes.
