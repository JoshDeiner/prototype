#!/usr/bin/env python3
"""
audio_input.py - Speech to text module using Whisper
"""
import os
import tempfile
import logging
import queue
import threading
import sounddevice as sd
import numpy as np
import whisper
from scipy.io import wavfile

logger = logging.getLogger(__name__)

class AudioInputProcessor:
    """
    Records audio from microphone and transcribes it using Whisper.
    """
    def __init__(self, 
                 model_size="base", 
                 sample_rate=16000, 
                 device=None,
                 energy_threshold=0.01,
                 phrase_timeout=1.0):
        """
        Initialize the audio input processor.
        
        Args:
            model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
            sample_rate: Audio sample rate
            device: Sound input device
            energy_threshold: Minimum energy level to consider as speaking
            phrase_timeout: Time of silence to consider end of phrase
        """
        # Whisper setup
        self.model = whisper.load_model(model_size)
        self.sample_rate = sample_rate
        
        # Audio recording parameters
        self.device = device
        self.energy_threshold = energy_threshold
        self.phrase_timeout = phrase_timeout
        self.recording = False
        self.audio_queue = queue.Queue()
        
    def start_listening(self):
        """Start background listening for audio input"""
        self.recording = True
        self.listen_thread = threading.Thread(target=self._background_listen)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        logger.info("Started background listening")
        
    def stop_listening(self):
        """Stop background listening"""
        self.recording = False
        if hasattr(self, 'listen_thread'):
            self.listen_thread.join(timeout=2.0)
        logger.info("Stopped background listening")
    
    def _background_listen(self):
        """Background thread that continuously records audio"""
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio callback status: {status}")
            # Queue the audio data for processing
            self.audio_queue.put(indata.copy())
            
        # Audio stream for continuous recording
        with sd.InputStream(samplerate=self.sample_rate, 
                          channels=1, 
                          callback=audio_callback,
                          device=self.device):
            while self.recording:
                # Keep the thread alive
                import time
                time.sleep(0.1)
    
    def transcribe_next_phrase(self, timeout=None):
        """
        Records until a phrase is complete, then transcribes it.
        
        Args:
            timeout: Maximum time to wait for a phrase
            
        Returns:
            Transcribed text
        """
        # Initialize buffer for recording
        audio_data = []
        phrase_complete = False
        silence_start = None
        
        # Record until phrase is complete
        while not phrase_complete and self.recording:
            try:
                # Get chunk from queue
                chunk = self.audio_queue.get(timeout=timeout)
                audio_data.append(chunk)
                
                # Check if speaking
                energy = np.sqrt(np.mean(chunk**2))
                
                # Detect if speaking or silence
                if energy > self.energy_threshold:
                    # Reset silence counter when speech detected
                    silence_start = None
                elif silence_start is None:
                    # Start silence counter
                    silence_start = threading.Event()
                    silence_start.wait(self.phrase_timeout)
                    
                    # If silence lasted long enough, consider phrase complete
                    if silence_start and not silence_start.is_set():
                        phrase_complete = True
            
            except queue.Empty:
                if timeout:
                    # If queue timeout occurred and we're using a timeout, break
                    break
        
        # If we collected audio data, transcribe it
        if audio_data:
            # Concatenate all audio chunks
            audio_array = np.concatenate(audio_data, axis=0)
            
            # Save to temporary WAV file (Whisper expects a file)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                wavfile.write(temp_file.name, self.sample_rate, audio_array)
                temp_path = temp_file.name
            
            try:
                # Transcribe with Whisper
                result = self.model.transcribe(temp_path)
                transcribed_text = result["text"].strip()
                logger.info(f"Transcribed: {transcribed_text}")
                return transcribed_text
            finally:
                # Clean up temp file
                os.unlink(temp_path)
        
        return ""
    
    def record_and_transcribe(self, duration=5.0):
        """
        Record for a fixed duration and transcribe.
        
        Args:
            duration: How long to record in seconds
            
        Returns:
            Transcribed text
        """
        logger.info(f"Recording for {duration} seconds...")
        
        # Initialize recording
        audio_data = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()  # Wait until recording is finished
        
        # Save to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            wavfile.write(temp_file.name, self.sample_rate, audio_data)
            temp_path = temp_file.name
        
        try:
            # Transcribe with Whisper
            result = self.model.transcribe(temp_path)
            transcribed_text = result["text"].strip()
            logger.info(f"Transcribed: {transcribed_text}")
            return transcribed_text
        finally:
            # Clean up temp file
            os.unlink(temp_path)

def get_available_devices():
    """List all available audio input devices"""
    devices = sd.query_devices()
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    return input_devices