"""Main voice assistant module integrating all services."""
import os
import json
import logging
from voice_utils import logger, ensure_directory, load_scenario
from transcription import TranscriptionService
from llm_service import LLMService
from os_exec import OSExecutionService
from tts_service import TTSService

class VoiceAssistant:
    def __init__(self, config=None):
        """Initialize the voice assistant.
        
        Args:
            config: Configuration dictionary
        """
        # Set default configuration
        self.config = {
            "transcription_model": None,
            "llm_model": "llama",
            "tts_engine": "pyttsx3",
            "dry_run": True,
            "output_dir": "output"
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
            
        # Ensure output directory exists
        ensure_directory(self.config["output_dir"])
        
        # Initialize services
        self.transcription_service = TranscriptionService(
            whisper_model_path=self.config["transcription_model"]
        )
        
        self.llm_service = LLMService(
            model_type=self.config["llm_model"]
        )
        
        self.os_exec_service = OSExecutionService(
            dry_run=self.config["dry_run"]
        )
        
        self.tts_service = TTSService(
            engine=self.config["tts_engine"],
            output_dir=os.path.join(self.config["output_dir"], "audio")
        )
        
        logger.info("Voice assistant initialized")
        
    def process_audio_file(self, audio_file, expected_transcript=None, expected_action=None):
        """Process an audio file through the full pipeline.
        
        Args:
            audio_file: Path to the audio file
            expected_transcript: Expected transcription for validation
            expected_action: Expected action for validation
            
        Returns:
            dict: Results from the processing pipeline
        """
        results = {
            "audio_file": audio_file,
            "success": False,
            "transcript": None,
            "transcript_valid": None,
            "llm_response": None,
            "action_valid": None,
            "action_result": None,
            "tts_output": None
        }
        
        # Step 1: Transcribe audio
        logger.info(f"Processing audio file: {audio_file}")
        transcript = self.transcription_service.transcribe_audio(audio_file)
        results["transcript"] = transcript
        
        if not transcript:
            logger.error("Transcription failed")
            return results
            
        # Validate transcript if expected transcript is provided
        if expected_transcript:
            transcript_valid = self.transcription_service.validate_transcription(
                transcript, expected_transcript
            )
            results["transcript_valid"] = transcript_valid
            
        # Step 2: Process through LLM
        llm_response = self.llm_service.process_input(transcript)
        results["llm_response"] = llm_response
        
        if not llm_response:
            logger.error("LLM processing failed")
            return results
        
        # Validate action if expected action is provided
        if expected_action:
            action_valid = self.llm_service.validate_response(
                llm_response, expected_action
            )
            results["action_valid"] = action_valid
        
        # Step 3: Execute action
        action_result = self.os_exec_service.execute_action(llm_response["action"])
        results["action_result"] = action_result
        
        # Step 4: Convert response to speech
        tts_output = self.tts_service.speak(llm_response["response"])
        results["tts_output"] = tts_output
        
        results["success"] = True
        logger.info("Audio processing completed successfully")
        return results
    
    def process_scenario(self, scenario_path):
        """Process a scenario defined in a JSON file.
        
        Args:
            scenario_path: Path to the scenario JSON file
            
        Returns:
            dict: Results from processing the scenario
        """
        scenario = load_scenario(scenario_path)
        if not scenario:
            logger.error(f"Failed to load scenario: {scenario_path}")
            return {"success": False, "error": "Failed to load scenario"}
            
        logger.info(f"Processing scenario: {scenario_path}")
        
        results = {
            "scenario": scenario_path,
            "success": True,
            "steps": []
        }
        
        audio_file = scenario.get("audio_file")
        expected_transcript = scenario.get("expected_transcript")
        expected_action = scenario.get("expected_action")
        
        step_result = self.process_audio_file(
            audio_file,
            expected_transcript,
            expected_action
        )
        
        results["steps"].append(step_result)
        
        # Check if all steps were successful
        if not all(step["success"] for step in results["steps"]):
            results["success"] = False
            
        return results


def main():
    """Main function to run a test scenario."""
    # Create test scenario directory
    test_dir = "test_scenarios"
    ensure_directory(test_dir)
    
    # Create a sample scenario file
    scenario = {
        "audio_file": "test_scenarios/open_browser.mp4",
        "expected_transcript": "How do I open up my browser?",
        "expected_action": {
            "type": "launch_app",
            "app_name": "firefox"
        }
    }
    
    scenario_path = os.path.join(test_dir, "browser_scenario.json")
    with open(scenario_path, 'w') as f:
        json.dump(scenario, f, indent=2)
    
    # Create a dummy audio file for testing
    dummy_audio_path = "test_scenarios/open_browser.mp4"
    with open(dummy_audio_path, 'w') as f:
        f.write("# Dummy audio file")
    
    # Initialize and run the voice assistant
    assistant = VoiceAssistant()
    results = assistant.process_scenario(scenario_path)
    
    # Print results
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()