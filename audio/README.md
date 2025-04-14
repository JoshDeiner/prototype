# 🎤 Audio Support for Voice Assistant

This module adds audio input/output capabilities to the Voice Assistant prototype, enabling speech-to-text and text-to-speech functionality.

## Features

- **Speech-to-Text:** Capture audio from microphone and transcribe using Whisper
- **Text-to-Speech:** Convert responses to speech using either pyttsx3 or Edge TTS
- **Audio Streaming:** Record, save and process audio streams
- **Conversation Logging:** Log conversations with both text and audio

## Requirements

To use the audio features, you need to install the required dependencies. Uncomment and install the audio-related packages in `requirements.txt`:

```bash
# Audio-related packages
sounddevice>=0.4.6
scipy>=1.10.0
openai-whisper>=20230314
pyttsx3>=2.90
pygame>=2.5.0
edge-tts>=6.1.5
numpy>=1.23.0
pyaudio>=0.2.13
```

Install with:

```bash
pip install -r requirements.txt
```

## Usage

Enable audio mode when starting the assistant:

```bash
python main.py --audio
```

### Additional Options

- `--list-audio-devices`: List available audio input/output devices
- `--input-device ID`: Specify audio input device ID
- `--output-device ID`: Specify audio output device ID
- `--whisper-model [tiny|base|small|medium|large]`: Specify Whisper model size
- `--tts-engine [pyttsx3|edge_tts]`: Select text-to-speech engine
- `--no-continuous`: Disable continuous listening (use push-to-talk mode)
- `--no-log-audio`: Disable audio conversation logging

Example:

```bash
python main.py --audio --whisper-model tiny --tts-engine edge_tts
```

## Runtime Commands

When the assistant is running in audio mode, you can use these text commands:

- `start listening`: Start continuous listening
- `stop listening`: Stop continuous listening
- `exit`, `quit`, `bye`: End the session

## Architecture

The audio system consists of several components:

1. **AudioInputProcessor**: Handles microphone recording and transcription
2. **AudioOutputProcessor**: Manages text-to-speech synthesis and playback
3. **AudioStreamer**: Routes and logs audio streams
4. **ConversationLogger**: Tracks both audio and text parts of the conversation
5. **AudioController**: Coordinates the above components and integrates with the main wrapper

## Implementation Details

- Uses OpenAI's Whisper for offline speech recognition
- Supports multiple TTS engines (pyttsx3 for offline use, Edge TTS for better quality)
- Audio logs are saved to `/logs/audio/` by default
- Continuous listening detects phrases based on silence periods