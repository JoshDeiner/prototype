#!/usr/bin/env python3
"""
streamer.py - Audio router/broadcaster for logging or streaming audio
"""
import os
import time
import logging
import tempfile
import threading
import wave
import pyaudio
import numpy as np
from scipy.io import wavfile

logger = logging.getLogger(__name__)

class AudioStreamer:
    """
    Records, saves, and optionally broadcasts audio streams.
    Useful for logging conversations or sending audio to external services.
    """
    
    def __init__(self, 
                 sample_rate=16000, 
                 channels=1,
                 chunk_size=1024,
                 output_dir=None):
        """
        Initialize the audio streamer.
        
        Args:
            sample_rate: Audio sample rate
            channels: Number of audio channels (1=mono, 2=stereo)
            chunk_size: Size of audio chunks to process
            output_dir: Directory to save recordings (None = use temp dir)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.output_dir = output_dir or tempfile.gettempdir()
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # PyAudio setup
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording = False
        self.recording_data = []
        
        # Callbacks
        self.broadcast_callbacks = []
    
    def start_recording(self, session_id=None):
        """
        Start recording an audio session.
        
        Args:
            session_id: Optional ID for the session (defaults to timestamp)
            
        Returns:
            session_id of the recording
        """
        if self.recording:
            logger.warning("Recording already in progress, stopping current session")
            self.stop_recording()
        
        # Generate session ID if not provided
        self.session_id = session_id or f"session_{int(time.time())}"
        logger.info(f"Starting recording session: {self.session_id}")
        
        # Reset recording buffer
        self.recording_data = []
        self.recording = True
        
        # Start recording stream
        self.stream = self.audio.open(
            format=pyaudio.paFloat32,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            output=False,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback
        )
        
        return self.session_id
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Handle incoming audio data"""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        # Store the audio data
        if self.recording:
            self.recording_data.append(in_data)
            
            # Broadcast to any registered callbacks
            data_np = np.frombuffer(in_data, dtype=np.float32)
            for callback_fn in self.broadcast_callbacks:
                try:
                    callback_fn(data_np, self.session_id)
                except Exception as e:
                    logger.error(f"Error in broadcast callback: {e}")
        
        # Continue recording
        return (in_data, pyaudio.paContinue)
    
    def stop_recording(self):
        """
        Stop the current recording session and save the file.
        
        Returns:
            Path to the saved WAV file
        """
        if not self.recording:
            logger.warning("No recording in progress")
            return None
        
        # Stop recording
        self.recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        # Save the recorded data
        if self.recording_data:
            # Generate output path
            output_path = os.path.join(
                self.output_dir, 
                f"{self.session_id}.wav"
            )
            
            # Convert data to numpy array
            audio_data = np.frombuffer(b''.join(self.recording_data), dtype=np.float32)
            
            # Save as WAV file
            wavfile.write(output_path, self.sample_rate, audio_data)
            logger.info(f"Saved recording to: {output_path}")
            
            return output_path
        
        return None
    
    def register_broadcast_callback(self, callback_fn):
        """
        Register a callback function to receive audio chunks in real-time.
        
        Args:
            callback_fn: Function that takes (audio_chunk, session_id) as arguments
        """
        self.broadcast_callbacks.append(callback_fn)
        logger.info(f"Registered broadcast callback: {callback_fn.__name__}")
    
    def unregister_broadcast_callback(self, callback_fn):
        """Remove a registered callback function"""
        if callback_fn in self.broadcast_callbacks:
            self.broadcast_callbacks.remove(callback_fn)
            logger.info(f"Unregistered broadcast callback: {callback_fn.__name__}")
    
    def cleanup(self):
        """Clean up resources"""
        if self.stream:
            self.stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        logger.info("Audio streamer resources cleaned up")

class ConversationLogger:
    """
    Logger for audio conversations that tracks both audio and transcriptions.
    """
    
    def __init__(self, log_dir=None):
        """
        Initialize the conversation logger.
        
        Args:
            log_dir: Directory to save logs (None = use temp dir)
        """
        self.log_dir = log_dir or os.path.join(tempfile.gettempdir(), "conversation_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.current_session = None
        self.transcript = []
    
    def start_session(self, session_id=None):
        """Start a new conversation session"""
        # Generate session ID if not provided
        self.current_session = session_id or f"conversation_{int(time.time())}"
        self.transcript = []
        
        # Create session directory
        session_dir = os.path.join(self.log_dir, self.current_session)
        os.makedirs(session_dir, exist_ok=True)
        
        logger.info(f"Started conversation session: {self.current_session}")
        return self.current_session
    
    def log_interaction(self, speaker, text, audio_path=None):
        """
        Log an interaction in the conversation.
        
        Args:
            speaker: Who is speaking ("user" or "assistant")
            text: Transcribed or generated text
            audio_path: Optional path to audio file
        """
        if not self.current_session:
            logger.warning("No active session, starting a new one")
            self.start_session()
        
        # Add to transcript
        timestamp = time.time()
        entry = {
            "timestamp": timestamp,
            "speaker": speaker,
            "text": text,
            "audio_path": audio_path
        }
        self.transcript.append(entry)
        
        # Write to log file
        self._append_to_log(entry)
        
        logger.debug(f"Logged {speaker} interaction: {text[:50]}{'...' if len(text) > 50 else ''}")
    
    def _append_to_log(self, entry):
        """Append an entry to the log file"""
        session_dir = os.path.join(self.log_dir, self.current_session)
        log_path = os.path.join(session_dir, "transcript.txt")
        
        # Format the entry
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["timestamp"]))
        log_line = f"[{timestamp_str}] {entry['speaker']}: {entry['text']}"
        if entry['audio_path']:
            log_line += f" [Audio: {os.path.basename(entry['audio_path'])}]"
        
        # Write to file
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    
    def end_session(self):
        """End the current session and return the transcript"""
        if not self.current_session:
            logger.warning("No active session to end")
            return None
        
        logger.info(f"Ended conversation session: {self.current_session}")
        
        # Return a copy of the transcript
        transcript = self.transcript.copy()
        self.current_session = None
        self.transcript = []
        
        return transcript
    
    def get_transcript(self):
        """Get the current transcript"""
        return self.transcript.copy() if self.transcript else []