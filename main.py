#!/usr/bin/env python3
"""
Main entry point for the Voice Assistant.

This routes user input to the appropriate controller based on configuration.
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from controller.wrapper import Wrapper
import config as app_config

# Load environment variables from .env file
load_dotenv()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the voice assistant."
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["llama", "claude", "gemini", "simulation"],
        default="llama",
        help="LLM model to use (default: llama)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually execute commands (simulate only)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds before auto-executing actions (default: 0.5)"
    )
    parser.add_argument(
        "--manual-confirm",
        action="store_true",
        help="Require manual confirmation for actions (default: auto-confirm)"
    )
    parser.add_argument(
        "--scene",
        type=str,
        help="Scene file to use (optional)"
    )
    parser.add_argument(
        "--list-scenes",
        action="store_true",
        help="List available scenes and exit"
    )
    parser.add_argument(
        "--max-history",
        type=int,
        default=5,
        help="Maximum number of conversation turns to remember (default: 5)"
    )
    parser.add_argument(
        "--unsafe",
        action="store_true",
        help="Disable safety checks for OS commands (use with caution!)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Directory containing data files (default: data)"
    )
    
    # Audio-related arguments
    audio_group = parser.add_argument_group('Audio Options')
    audio_group.add_argument(
        "--audio",
        action="store_true",
        help="Enable audio input/output mode"
    )
    audio_group.add_argument(
        "--list-audio-devices",
        action="store_true",
        help="List available audio input/output devices and exit"
    )
    audio_group.add_argument(
        "--input-device",
        type=int,
        help="Specify audio input device ID"
    )
    audio_group.add_argument(
        "--output-device",
        type=int,
        help="Specify audio output device ID"
    )
    audio_group.add_argument(
        "--whisper-model",
        type=str,
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Specify Whisper model size (default: base)"
    )
    audio_group.add_argument(
        "--tts-engine",
        type=str,
        choices=["pyttsx3", "edge_tts"],
        default="pyttsx3",
        help="Text-to-speech engine to use (default: pyttsx3)"
    )
    audio_group.add_argument(
        "--no-continuous",
        action="store_true",
        help="Disable continuous listening (use push-to-talk mode)"
    )
    audio_group.add_argument(
        "--no-log-audio",
        action="store_true",
        help="Disable audio conversation logging"
    )
    
    return parser.parse_args()

def list_available_scenes():
    """List all available scene files in the scenes directory."""
    if not os.path.exists(app_config.SCENES_DIR) or not os.path.isdir(app_config.SCENES_DIR):
        print("Scenes directory not found.")
        return []
        
    scenes = []
    for file in os.listdir(app_config.SCENES_DIR):
        if file.endswith(('.yaml', '.yml', '.json')):
            scenes.append(file)
            
    return scenes

def list_audio_devices():
    """List available audio input and output devices."""
    try:
        # First try to import needed modules
        import sounddevice as sd
        
        # Get device info
        devices = sd.query_devices()
        
        # Separate into input and output devices
        input_devices = []
        output_devices = []
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append((i, device['name'], device['max_input_channels']))
            if device['max_output_channels'] > 0:
                output_devices.append((i, device['name'], device['max_output_channels']))
        
        # Print input devices
        print("\n===== Audio Input Devices =====")
        if not input_devices:
            print("No input devices found.")
        else:
            for id, name, channels in input_devices:
                print(f"ID: {id} - {name} ({channels} channels)")
        
        # Print output devices
        print("\n===== Audio Output Devices =====")
        if not output_devices:
            print("No output devices found.")
        else:
            for id, name, channels in output_devices:
                print(f"ID: {id} - {name} ({channels} channels)")
                
        print("\nTo use a specific device, run with --input-device ID and/or --output-device ID")
        
    except ImportError:
        print("\nAudio device listing requires sounddevice module.")
        print("Install required packages with: pip install sounddevice")
    except Exception as e:
        print(f"\nError listing audio devices: {e}")

def main():
    """Run the voice assistant."""
    args = parse_args()
    
    # Check if we should just list scenes and exit
    if args.list_scenes:
        print("\n===== Available Scenes =====")
        scenes = list_available_scenes()
        if not scenes:
            print("No scene files found.")
        else:
            for i, scene in enumerate(scenes, 1):
                scene_path = os.path.join(app_config.SCENES_DIR, scene)
                # Try to extract the name from the file
                try:
                    with open(scene_path, 'r') as f:
                        first_line = f.readline().strip()
                        name = first_line.split("name:", 1)[1].strip().strip('"\'') if "name:" in first_line else scene
                except:
                    name = scene
                    
                print(f"{i}. {scene} - {name}")
        return
    
    # Check if we should list audio devices and exit
    if args.list_audio_devices:
        list_audio_devices()
        return
    
    # Configure the assistant
    # Use the model specified in args, or fall back to default config
    model_type = args.model if args.model != "llama" else app_config.DEFAULT_CONFIG["llm_model"]
    
    # Basic configuration
    user_config = {
        "llm_model": model_type,
        "dry_run": args.dry_run,
        "safe_mode": not args.unsafe,
        "auto_confirm": not args.manual_confirm,
        "delay": args.delay,
        "scene_path": args.scene,
        "max_history": args.max_history,
        "data_dir": args.data_dir
    }
    
    # Audio configuration if enabled
    if args.audio:
        # Check if audio modules are available
        try:
            import sounddevice
            import whisper
            import pyttsx3
            
            # Add audio configuration
            user_config.update({
                "audio_mode": True,
                "audio_input_device": args.input_device,
                "audio_output_device": args.output_device,
                "audio_model_size": args.whisper_model,
                "tts_engine": args.tts_engine,
                "log_audio": not args.no_log_audio,
                "continuous_listening": not args.no_continuous
            })
        except ImportError as e:
            print(f"\nError: Audio mode requires additional modules. {e}")
            print("Install required packages with: pip install sounddevice scipy openai-whisper pyttsx3 pygame edge-tts")
            return
    
    # Print configuration
    print("\n===== Voice Assistant =====")
    print("Configuration:")
    print(f"- Model: {model_type}")
    if args.scene:
        print(f"- Scene: {args.scene}")
    print(f"- Data directory: {args.data_dir}")
    print(f"- Execution mode: {'Dry run' if args.dry_run else 'Live (will execute commands)'}")
    print(f"- Safety checks: {'Disabled (UNSAFE)' if args.unsafe else 'Enabled'}")
    print(f"- Confirmation: {'Manual' if args.manual_confirm else 'Automatic'}")
    print(f"- Auto-confirmation delay: {args.delay} seconds")
    print(f"- History size: {args.max_history} turns")
    
    # Print audio configuration if enabled
    if args.audio:
        print("\nAudio Configuration:")
        print(f"- Audio mode: Enabled")
        print(f"- Input device: {args.input_device if args.input_device is not None else 'Default'}")
        print(f"- Output device: {args.output_device if args.output_device is not None else 'Default'}")
        print(f"- Whisper model: {args.whisper_model}")
        print(f"- TTS engine: {args.tts_engine}")
        print(f"- Listening mode: {'Push-to-talk' if args.no_continuous else 'Continuous'}")
        print(f"- Audio logging: {'Disabled' if args.no_log_audio else 'Enabled'}")
    
    print()
    
    try:
        # Initialize and run the assistant
        assistant = Wrapper(config=user_config)
        assistant.run_interactive_session()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Use --list-scenes to see available scenes.")
    except Exception as e:
        print(f"Error initializing assistant: {e}")

if __name__ == "__main__":
    main()