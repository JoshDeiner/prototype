#!/usr/bin/env python3
"""
controller.py - Main audio controller that integrates with the wrapper
"""
import logging
import threading
import time
from .audio_input import AudioInputProcessor
from .audio_output import AudioOutputProcessor
from .streamer import ConversationLogger

logger = logging.getLogger(__name__)

class AudioController:
    """
    Manages audio I/O and integrates with the main wrapper controller.
    Acts as the bridge between audio subsystems and the LLM/OS modes.
    """
    
    def __init__(self, 
                 input_processor=None, 
                 output_processor=None,
                 log_conversations=True,
                 log_dir=None):
        """
        Initialize the audio controller.
        
        Args:
            input_processor: AudioInputProcessor instance (created if None)
            output_processor: AudioOutputProcessor instance (created if None)
            log_conversations: Whether to log conversations
            log_dir: Directory to save conversation logs
        """
        # Initialize processors if not provided
        self.input_processor = input_processor or AudioInputProcessor()
        self.output_processor = output_processor or AudioOutputProcessor()
        
        # Initialize conversation logger if enabled
        self.log_conversations = log_conversations
        if log_conversations:
            self.conversation_logger = ConversationLogger(log_dir)
            self.current_session = None
        
        # Control flags
        self.active = False
        self.listen_mode = 'continuous'  # 'continuous', 'push_to_talk', or 'command'
        
        # Callbacks
        self.on_transcription_callback = None
    
    def start(self, session_id=None):
        """
        Start the audio controller.
        
        Args:
            session_id: Optional session ID for logging
        """
        if self.active:
            logger.warning("Audio controller already active")
            return
        
        self.active = True
        
        # Start input processor
        self.input_processor.start_listening()
        
        # Start conversation logger if enabled
        if self.log_conversations:
            self.current_session = self.conversation_logger.start_session(session_id)
        
        logger.info("Audio controller started")
    
    def stop(self):
        """Stop the audio controller"""
        if not self.active:
            logger.warning("Audio controller not active")
            return
        
        self.active = False
        
        # Stop input processor
        self.input_processor.stop_listening()
        
        # End conversation logger session if enabled
        if self.log_conversations and self.current_session:
            transcript = self.conversation_logger.end_session()
            self.current_session = None
        
        logger.info("Audio controller stopped")
    
    def set_transcription_callback(self, callback_fn):
        """
        Set callback function to be called when new transcription is available.
        
        Args:
            callback_fn: Function that takes the transcribed text as argument
        """
        self.on_transcription_callback = callback_fn
        logger.info("Set transcription callback")
    
    def set_listen_mode(self, mode):
        """
        Set the listening mode.
        
        Args:
            mode: 'continuous', 'push_to_talk', or 'command'
        """
        if mode not in ['continuous', 'push_to_talk', 'command']:
            raise ValueError(f"Invalid listen mode: {mode}")
        
        self.listen_mode = mode
        logger.info(f"Set listen mode to: {mode}")
    
    def listen_for_command(self, timeout=5.0):
        """
        Listen for a single command.
        
        Args:
            timeout: Maximum duration to listen for
            
        Returns:
            Transcribed command text
        """
        # For push-to-talk or command mode
        if self.listen_mode == 'push_to_talk' or self.listen_mode == 'command':
            # Use fixed duration recording
            text = self.input_processor.record_and_transcribe(timeout)
        else:
            # Use phrase detection
            text = self.input_processor.transcribe_next_phrase(timeout)
        
        # Log the user input if enabled
        if self.log_conversations and self.current_session:
            self.conversation_logger.log_interaction("user", text)
        
        # Call the callback if set
        if self.on_transcription_callback:
            self.on_transcription_callback(text)
        
        return text
    
    def start_continuous_listening(self):
        """
        Start continuous listening in a background thread.
        Will call the transcription callback whenever a new phrase is detected.
        """
        if self.listen_mode != 'continuous':
            logger.warning(f"Changing listen mode from {self.listen_mode} to continuous")
            self.listen_mode = 'continuous'
        
        if not self.active:
            self.start()
        
        # Start background thread for continuous listening
        self.listen_thread = threading.Thread(target=self._continuous_listen_thread)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        logger.info("Started continuous listening")
    
    def _continuous_listen_thread(self):
        """Background thread for continuous listening"""
        while self.active and self.listen_mode == 'continuous':
            try:
                # Transcribe next complete phrase
                text = self.input_processor.transcribe_next_phrase()
                
                if text:
                    # Log the user input if enabled
                    if self.log_conversations and self.current_session:
                        self.conversation_logger.log_interaction("user", text)
                    
                    # Call the callback if set
                    if self.on_transcription_callback:
                        self.on_transcription_callback(text)
            
            except Exception as e:
                logger.error(f"Error in continuous listening thread: {e}")
                time.sleep(1)  # Avoid tight loop on error
    
    def speak_response(self, text, block=False):
        """
        Speak a response using the output processor.
        
        Args:
            text: Text to speak
            block: Whether to block until speech is complete
        """
        # Log the assistant response if enabled
        if self.log_conversations and self.current_session:
            self.conversation_logger.log_interaction("assistant", text)
        
        # Speak the response
        self.output_processor.speak(text, block=block)
    
    def get_conversation_transcript(self):
        """Get the current conversation transcript if logging is enabled"""
        if self.log_conversations:
            return self.conversation_logger.get_transcript()
        return []