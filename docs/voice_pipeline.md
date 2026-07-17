# Voice pipeline

XenoBuddy-Pi.AI keeps speech tools as adapters rather than bundled dependencies.

## Speech-to-text

Use `whisper.cpp` or another local STT tool to transcribe microphone audio to text. The framework is designed so recognised text is passed into the same safe planner used by typed commands.

## Text-to-speech

Use Piper or another local TTS tool for local spoken replies. Large model files do not belong in the repository; keep them in `voices/` or another ignored local directory.

## Why this architecture

The robot should not require cloud AI to move. A reliable offline intent router is included for demos. Future LLM integrations should return constrained JSON and choose only named gestures from the local library.
