#!/usr/bin/env python3
"""
audio_output.py - Text to speech wrapper module
"""
import os
import tempfile
import logging
import threading
import pygame
import pyttsx3
import edge_tts

logger = logging.getLogger(__name__)

class AudioOutputProcessor:
    """
    Converts text to speech and plays it through speakers.
    Supports multiple TTS engines.
    """
    
    # Available TTS engines
    ENGINE_PYTTSX3 = "pyttsx3"
    ENGINE_EDGE_TTS = "edge_tts"
    
    def __init__(self, engine=ENGINE_PYTTSX3, voice=None, rate=175, volume=1.0):
        """
        Initialize the audio output processor.
        
        Args:
            engine: TTS engine to use ("pyttsx3" or "edge_tts")
            voice: Voice to use (depends on engine)
            rate: Speech rate (words per minute)
            volume: Volume (0.0 to 1.0)
        """
        self.engine_type = engine
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self._setup_engine()
        
        # Initialize pygame for audio playback
        pygame.mixer.init()
    
    def _setup_engine(self):
        """Set up the TTS engine"""
        if self.engine_type == self.ENGINE_PYTTSX3:
            self.engine = pyttsx3.init()
            
            # Set voice if specified
            if self.voice:
                self.engine.setProperty('voice', self.voice)
            
            # Set rate and volume
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
        
        elif self.engine_type == self.ENGINE_EDGE_TTS:
            # Edge TTS only creates the engine at synthesis time
            pass
        
        else:
            raise ValueError(f"Unsupported TTS engine: {self.engine_type}")
    
    def get_available_voices(self):
        """Get available voices for the current engine"""
        if self.engine_type == self.ENGINE_PYTTSX3:
            voices = self.engine.getProperty('voices')
            return [(voice.id, voice.name) for voice in voices]
        
        elif self.engine_type == self.ENGINE_EDGE_TTS:
            # Edge TTS would need to fetch voices via API
            # For simplicity, return a list of common voices
            return [
                ("en-US-AriaNeural", "English US - Aria (Female)"),
                ("en-US-GuyNeural", "English US - Guy (Male)"),
                ("en-GB-SoniaNeural", "English UK - Sonia (Female)"),
                ("en-GB-RyanNeural", "English UK - Ryan (Male)")
            ]
    
    async def _edge_tts_communicate(self, text, output_file):
        """Helper for Edge TTS communication"""
        voice = self.voice or "en-US-AriaNeural"
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
    
    def speak(self, text, block=False):
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to speak
            block: Whether to block until speech is complete
        """
        if not text:
            return
        
        logger.info(f"Speaking: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        if self.engine_type == self.ENGINE_PYTTSX3:
            if block:
                self.engine.say(text)
                self.engine.runAndWait()
            else:
                # Run in separate thread to avoid blocking
                speech_thread = threading.Thread(
                    target=self._threaded_speak_pyttsx3,
                    args=(text,)
                )
                speech_thread.daemon = True
                speech_thread.start()
        
        elif self.engine_type == self.ENGINE_EDGE_TTS:
            # Create temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate speech in a separate thread
            speech_thread = threading.Thread(
                target=self._threaded_speak_edge_tts,
                args=(text, temp_path)
            )
            speech_thread.daemon = True
            speech_thread.start()
            
            if block:
                speech_thread.join()
    
    def _threaded_speak_pyttsx3(self, text):
        """Helper for threaded pyttsx3 speech"""
        self.engine.say(text)
        self.engine.runAndWait()
    
    def _threaded_speak_edge_tts(self, text, output_file):
        """Helper for threaded Edge TTS speech"""
        import asyncio
        
        # Run the async function
        asyncio.run(self._edge_tts_communicate(text, output_file))
        
        # Play the audio
        pygame.mixer.music.load(output_file)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Clean up the temporary file
        try:
            os.unlink(output_file)
        except Exception as e:
            logger.error(f"Error removing temporary file: {e}")
    
    def stop(self):
        """Stop current speech"""
        if self.engine_type == self.ENGINE_PYTTSX3:
            self.engine.stop()
        elif self.engine_type == self.ENGINE_EDGE_TTS:
            pygame.mixer.music.stop()

def get_default_voice():
    """Get the default system voice"""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    return voices[0].id if voices else None