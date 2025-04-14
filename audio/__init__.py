"""
Audio package for speech-to-text and text-to-speech capabilities.

Contains modules for audio input (microphone capture and STT),
audio output (TTS and speaker playback), and audio streaming/logging.
"""

from .audio_input import AudioInputProcessor, get_available_devices
from .audio_output import AudioOutputProcessor, get_default_voice
from .streamer import AudioStreamer, ConversationLogger

__all__ = [
    'AudioInputProcessor',
    'AudioOutputProcessor',
    'AudioStreamer',
    'ConversationLogger',
    'get_available_devices',
    'get_default_voice'
]