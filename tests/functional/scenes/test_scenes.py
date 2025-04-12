#!/usr/bin/env python3
"""
Tests for the scene simulator functionality.
"""
import os
import unittest
import tempfile
import json
import yaml
from scene_simulator import SceneSimulator
from utils import ensure_directory

class TestSceneSimulator(unittest.TestCase):
    """Tests for the SceneSimulator class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for test scenes and output
        self.temp_dir = tempfile.mkdtemp()
        self.scene_dir = os.path.join(self.temp_dir, "scenes")
        self.output_dir = os.path.join(self.temp_dir, "output")
        ensure_directory(self.scene_dir)
        ensure_directory(self.output_dir)
        
        # Create simulator with test configuration
        self.config = {
            "llm_model": "simulation",  # Use simulation mode for testing
            "scene_dir": self.scene_dir,
            "output_dir": self.output_dir,
            "max_steps": 5  # Use smaller max steps for testing
        }
        self.simulator = SceneSimulator(config=self.config)
        
        # Create a test scene
        self.test_scene = {
            "name": "Test Scene",
            "roles": {
                "user": "Test User Role",
                "client": "Test Client Role"
            },
            "scene": "This is a test scene description",
            "constraints": {
                "max_steps": 3
            }
        }
        
        # Save the test scene
        self.test_scene_path = os.path.join(self.scene_dir, "test_scene.yaml")
        with open(self.test_scene_path, 'w') as f:
            yaml.dump(self.test_scene, f, default_flow_style=False)
    
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_scene(self):
        """Test loading a scene from a file."""
        # Test loading YAML scene
        result = self.simulator.load_scene(self.test_scene_path)
        self.assertTrue(result)
        self.assertEqual(self.simulator.current_scene["name"], "Test Scene")
        
        # Create and test loading JSON scene
        json_scene_path = os.path.join(self.scene_dir, "test_scene.json")
        with open(json_scene_path, 'w') as f:
            json.dump(self.test_scene, f)
        
        # Reset simulator
        self.simulator.current_scene = None
        
        # Test loading JSON scene
        result = self.simulator.load_scene(json_scene_path)
        self.assertTrue(result)
        self.assertEqual(self.simulator.current_scene["name"], "Test Scene")
        
        # Test loading non-existent scene
        result = self.simulator.load_scene("non_existent_scene.yaml")
        self.assertFalse(result)
    
    def test_validate_scene_config(self):
        """Test scene configuration validation."""
        # Valid configuration should pass
        valid = self.simulator._validate_scene_config(self.test_scene)
        self.assertTrue(valid)
        
        # Missing required fields should fail
        invalid_scene = self.test_scene.copy()
        del invalid_scene["name"]
        valid = self.simulator._validate_scene_config(invalid_scene)
        self.assertFalse(valid)
        
        # Missing role should fail
        invalid_scene = self.test_scene.copy()
        invalid_scene["roles"] = {"user": "Test User Role"}  # Missing client
        valid = self.simulator._validate_scene_config(invalid_scene)
        self.assertFalse(valid)
    
    def test_generate_client_prompt(self):
        """Test generating client prompts."""
        # Load the scene
        self.simulator.load_scene(self.test_scene_path)
        
        # Generate a prompt
        prompt = self.simulator.generate_client_prompt("Test user input")
        
        # Check that the prompt contains all necessary components
        self.assertIn("Test User Role", prompt)
        self.assertIn("Test Client Role", prompt)
        self.assertIn("This is a test scene description", prompt)
        self.assertIn("Test user input", prompt)
    
    def test_process_user_input(self):
        """Test processing user input in simulation mode."""
        # Load the scene
        self.simulator.load_scene(self.test_scene_path)
        
        # Process some inputs
        result1 = self.simulator.process_user_input("Test input 1")
        self.assertTrue(result1["success"])
        self.assertEqual(result1["step_count"], 1)
        
        result2 = self.simulator.process_user_input("Test input 2")
        self.assertTrue(result2["success"])
        self.assertEqual(result2["step_count"], 2)
        
        result3 = self.simulator.process_user_input("Test input 3")
        self.assertTrue(result3["success"])
        self.assertEqual(result3["step_count"], 3)
        self.assertTrue(result3["scene_ended"])
        
        # Should fail after max steps
        result4 = self.simulator.process_user_input("Test input 4")
        self.assertFalse(result4["success"])
        self.assertTrue(result4["scene_ended"])
    
    def test_save_conversation(self):
        """Test saving conversation to a file."""
        # Load the scene
        self.simulator.load_scene(self.test_scene_path)
        
        # Process some inputs
        self.simulator.process_user_input("Test input 1")
        self.simulator.process_user_input("Test input 2")
        
        # Save the conversation
        saved_path = self.simulator.save_conversation("test_conversation.json")
        self.assertIsNotNone(saved_path)
        self.assertTrue(os.path.exists(saved_path))
        
        # Check the contents
        with open(saved_path, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["scene_name"], "Test Scene")
        self.assertEqual(data["steps"], 2)
        self.assertEqual(len(data["conversation"]), 2)


if __name__ == "__main__":
    unittest.main()